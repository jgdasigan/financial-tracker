"""Add, edit, and delete bills: recurring subscriptions, credit-card
installments (with a first-month conversion fee), and one-time expenses."""
from datetime import date

import streamlit as st

from lib import bill_edits
from lib import calculations as calc
from lib import db
from lib import style

st.title("📋 Manage bills")
st.caption(
    "Create, update, organize, and review every recurring payment and "
    "scheduled expense."
)

try:
    bills_df = db.list_bills()
except Exception as e:
    st.error(f"Couldn't reach the database: {e}")
    st.stop()

TYPE_HELP = {
    "recurring": "A fixed amount every month (subscription, rent). Leave duration blank to run indefinitely.",
    "installment": "A credit-card installment plan. The first month adds the conversion fee on top of the monthly amount.",
    "onetime": "A single charge in one specific month.",
    "pakaskas": "Lending to someone else, or fronting a payment that gets reimbursed. Tracked like an installment, "
                "but you can opt it out of the leftover/savings math below if the money was never really yours to begin with.",
}


def _card_options() -> list[str]:
    """Every tag a user could pick — built-ins, anything registered via the
    "Register a new tag" control below, and anything already used on a
    bill — so past entries are pickable again instead of having to be
    retyped."""
    return ["None"] + db.list_all_tags() + ["Other (type below)"]


def _pick_card(current: str | None, key_prefix: str) -> str | None:
    """Card selectbox + free-text fallback for a custom tag. Rendered
    *outside* any st.form — a field that only appears after a conditional
    pick needs an immediate rerun to show up in time, which forms don't give
    until submit."""
    options = _card_options()
    index = options.index(current) if current in options else 0
    choice = st.selectbox(
        "Card / tag",
        options,
        index=index,
        key=f"{key_prefix}_card_choice",
        width=220,
    )
    if choice == "Other (type below)":
        typed = st.text_input("Custom tag name", key=f"{key_prefix}_card_custom").strip()
        if typed:
            db.add_tag(typed)  # remembered immediately, not just once a bill is saved
        return typed or None
    return None if choice == "None" else choice


def _pick_month(label: str) -> date:
    current_month = calc.month_start(date.today())
    first_option = calc.add_months(current_month, -60)
    month_options = calc.month_range(first_option, 121)
    return st.selectbox(
        label,
        month_options,
        index=60,
        format_func=lambda month: month.strftime("%B %Y"),
        key="add_start_month",
        width=200,
    )


# ------------------------------------------------------------------ add form --
style.section_header(
    "Add a bill",
    "Set the schedule, amount, due date, and card or tag.",
)
with st.container(
    horizontal=True,
    horizontal_alignment="left",
    vertical_alignment="bottom",
    gap="small",
):
    bill_type = st.selectbox(
        "Type",
        ["recurring", "installment", "onetime", "pakaskas"],
        format_func=str.title,
        key="add_bill_type",
        width=180,
    )
    card = _pick_card(None, "add")

st.caption(TYPE_HELP[bill_type])

with st.form("add_bill_form", clear_on_submit=True):
    name = st.text_input("Name", placeholder="e.g. Clothes, Shoes, Groceries")
    col1, col2 = st.columns(2)

    if bill_type == "installment":
        with col1:
            monthly_amount = st.number_input("Monthly installment amount (excl. fee)", min_value=0.0, step=50.0)
            duration_months = st.number_input("Number of months", min_value=1, step=1, value=3)
        with col2:
            fee_mode = st.radio("Conversion fee (first month only)", ["Fixed amount", "% of monthly amount"], horizontal=True)
            fee_value = st.number_input("Fee value", min_value=0.0, step=10.0)
            start_month = _pick_month("Start month")
        conversion_fee = round(monthly_amount * fee_value / 100, 2) if fee_mode.startswith("%") else round(fee_value, 2)

    elif bill_type == "recurring":
        with col1:
            monthly_amount = st.number_input("Monthly amount", min_value=0.0, step=50.0)
            ongoing = st.checkbox("Ongoing (no end date)", value=True)
        with col2:
            start_month = _pick_month("Start month")
            duration_months = None if ongoing else st.number_input("Runs for how many months", min_value=1, step=1, value=6)
        conversion_fee = 0.0

    elif bill_type == "pakaskas":
        with col1:
            monthly_amount = st.number_input("Monthly amount", min_value=0.0, step=50.0)
            duration_months = st.number_input("Number of months", min_value=1, step=1, value=1)
        with col2:
            start_month = _pick_month("Start month")
        conversion_fee = 0.0

    else:  # onetime
        with col1:
            monthly_amount = st.number_input("Amount", min_value=0.0, step=50.0)
        with col2:
            start_month = _pick_month("Month it's due")
        duration_months = 1
        conversion_fee = 0.0

    include_in_projection = True
    if bill_type == "pakaskas":
        include_in_projection = st.checkbox(
            "Count against my leftover/savings projection", value=True,
            help="Uncheck if this money was never really yours to begin with — it'll still show up in the Pakaskas "
                 "table and upcoming payments, just won't reduce your projected leftover or savings balance.",
        )

    due_day = st.number_input(
        "Due day of month", min_value=1, max_value=31, value=1, step=1,
        help="Which day of the month this is due — used by the Weekly income check to know which week it falls in.",
    )
    notes = st.text_input("Notes (optional)")
    submitted = st.form_submit_button("Add bill", type="primary")

    if submitted:
        if not name.strip():
            st.error("Give the bill a name.")
        elif monthly_amount <= 0:
            st.error("Amount must be greater than 0.")
        else:
            db.add_bill(
                name=name.strip(),
                bill_type=bill_type,
                base_amount=monthly_amount,
                conversion_fee=conversion_fee,
                start_month=date(start_month.year, start_month.month, 1),
                duration_months=int(duration_months) if duration_months is not None else None,
                card=card,
                due_day=int(due_day),
                include_in_projection=include_in_projection,
                notes=notes.strip(),
            )
            st.success(f"Added “{name.strip()}”.")
            st.rerun()

st.divider()

# -------------------------------------------------------------------- listing --
EDITOR_KEY = "bills_editor"
UNDO_KEY = "bills_last_undo"
EDITABLE_COLUMNS = [
    "id", "name", "bill_type", "base_amount", "conversion_fee",
    "start_month", "duration_months", "card", "due_day", "include_in_projection", "notes",
]


def _filter_months():
    if bills_df.empty:
        return []

    today_month = calc.month_start(date.today())
    earliest_month = min(
        calc.month_start(month)
        for month in bills_df["start_month"]
    )
    latest_month = calc.add_months(today_month, 23)

    for record in bills_df.to_dict("records"):
        start_month = calc.month_start(record["start_month"])
        latest_month = max(latest_month, start_month)
        duration = record.get("duration_months")
        try:
            duration_months = int(duration)
        except (TypeError, ValueError):
            duration_months = None

        if record["bill_type"] == "onetime":
            duration_months = 1
        if duration_months:
            final_month = calc.add_months(
                start_month,
                duration_months - 1,
            )
            latest_month = max(latest_month, final_month)

    month_count = (
        (latest_month.year - earliest_month.year) * 12
        + latest_month.month
        - earliest_month.month
        + 1
    )
    return calc.month_range(earliest_month, month_count)


FILTER_MONTHS = _filter_months()


def _table_filters(key_prefix: str):
    with st.container(
        horizontal=True,
        horizontal_alignment="left",
        gap="small",
    ):
        selected_month = st.selectbox(
            "Month",
            [None, *FILTER_MONTHS],
            format_func=lambda month: (
                "All months"
                if month is None
                else calc.month_label(month)
            ),
            key=f"{key_prefix}_month",
            width=190,
        )
        selected_type = st.selectbox(
            "Type",
            [None, "recurring", "installment", "onetime", "pakaskas"],
            format_func=lambda bill_type: (
                "All types"
                if bill_type is None
                else bill_type.title()
            ),
            key=f"{key_prefix}_type",
            width=170,
        )
    alphabetical = st.toggle(
        "A–Z",
        key=f"{key_prefix}_alphabetical",
    )
    return selected_month, selected_type, alphabetical

if bills_df.empty:
    current_bills_df = bills_df.copy()
    archived_bills_df = bills_df.copy()
else:
    archive_mask = bills_df.apply(
        bill_edits.is_completed_bill,
        axis=1,
    )
    current_bills_df = bills_df.loc[~archive_mask].copy()
    archived_bills_df = bills_df.loc[archive_mask].copy()

style.section_header(
    "Current bills",
    "Changes save automatically. Use the row menu to remove a bill or the "
    "blank bottom row to add one.",
)

current_month, current_type, current_alphabetical = _table_filters(
    "current_bills",
)
visible_current_bills_df = bill_edits.filter_bills(
    current_bills_df,
    selected_month=current_month,
    selected_type=current_type,
    alphabetical=current_alphabetical,
)

autosave_status, undo_col = st.columns([8, 2])
autosave_status.caption("Autosave on")
undo_action = st.session_state.get(UNDO_KEY)
if undo_col.button(
    "Undo last change",
    disabled=undo_action is None,
    width="stretch",
):
    if undo_action["kind"] == "delete":
        db.delete_bill(undo_action["bill_id"])
    elif undo_action["kind"] == "restore":
        db.add_bill(**undo_action["bill"])
    elif undo_action["kind"] == "update":
        db.update_bill(
            undo_action["bill_id"],
            **undo_action["fields"],
        )
    st.session_state.pop(UNDO_KEY, None)
    st.session_state.pop(EDITOR_KEY, None)
    st.rerun()

if visible_current_bills_df.empty:
    if current_bills_df.empty:
        st.info("No current bills — add one above.")
    else:
        st.info("No current bills match these filters.")
else:
    editable = visible_current_bills_df[EDITABLE_COLUMNS].copy()
    # st.data_editor renders a blank text cell as the literal word "None"
    # rather than empty — fill those with "" so it reads as blank. Numeric
    # blanks (duration_months, for "ongoing") don't have that same fix
    # available, since NumberColumn only accepts a number or NaN.
    editable["card"] = editable["card"].fillna("")
    editable["notes"] = editable["notes"].fillna("")
    tag_options = [""] + db.list_all_tags()
    # A card/tag the data already has but that isn't in the picklist yet
    # (shouldn't normally happen, but keeps an old value from vanishing).
    for used in editable["card"].unique():
        if used and used not in tag_options:
            tag_options.append(used)

    edited = st.data_editor(
        editable,
        key=EDITOR_KEY,
        hide_index=True,
        num_rows="dynamic",
        width="stretch",
        column_order=["name", "bill_type", "base_amount", "conversion_fee", "start_month", "duration_months", "card", "due_day", "include_in_projection", "notes"],
        column_config={
            # "id": st.column_config.NumberColumn("ID", disabled=True, help="Assigned automatically — leave blank on a new row."),
            "name": st.column_config.TextColumn("Name", required=True),
            "bill_type": st.column_config.SelectboxColumn("Type", options=["recurring", "installment", "onetime", "pakaskas"], required=True),
            "base_amount": st.column_config.NumberColumn("Monthly amount", format="₱%.2f", min_value=0.0, required=True),
            "conversion_fee": st.column_config.NumberColumn("First-month fee", format="₱%.2f", min_value=0.0),
            "start_month": st.column_config.DateColumn("Start month", format="YYYY-MM-DD", required=True),
            "duration_months": st.column_config.NumberColumn("Duration (mo.)", min_value=1, step=1, help="Blank = ongoing (recurring only)."),
            "include_in_projection": st.column_config.CheckboxColumn(
                "In projection?", help="Uncheck for a Pakaskas entry that isn't really your money — it stays visible but won't affect leftover/savings.",
            ),
            "card": st.column_config.SelectboxColumn("Card / tag", options=tag_options, help="Blank = no tag. Add a new choice above."),
            "due_day": st.column_config.NumberColumn("Due day", min_value=1, max_value=31, step=1),
            "notes": st.column_config.TextColumn("Notes"),
        },
    )

    diff = bill_edits.diff_bills_edit(visible_current_bills_df, edited)
    change_applied = False

    for bill_id in diff.deletes:
        original = visible_current_bills_df.loc[
            visible_current_bills_df["id"] == bill_id
        ].iloc[0]
        st.session_state[UNDO_KEY] = {
            "kind": "restore",
            "bill": bill_edits.bill_kwargs_from_record(original),
        }
        db.delete_bill(bill_id)
        change_applied = True

    for kwargs in diff.adds:
        new_bill_id = db.add_bill(**kwargs)
        st.session_state[UNDO_KEY] = {
            "kind": "delete",
            "bill_id": new_bill_id,
        }
        change_applied = True

    for bill_id, fields in diff.updates:
        original = visible_current_bills_df.loc[
            visible_current_bills_df["id"] == bill_id
        ].iloc[0]
        st.session_state[UNDO_KEY] = {
            "kind": "update",
            "bill_id": bill_id,
            "fields": bill_edits.original_update_fields(
                original,
                fields,
            ),
        }
        db.update_bill(bill_id, **fields)
        change_applied = True

    if change_applied:
        st.session_state.pop(EDITOR_KEY, None)
        st.rerun()

st.divider()
style.section_header(
    "Archived bills",
    "Finite bills move here automatically after their final scheduled payment "
    "month and remain available for reference.",
)

archive_month, archive_type, archive_alphabetical = _table_filters(
    "archived_bills",
)
visible_archived_bills_df = bill_edits.filter_bills(
    archived_bills_df,
    selected_month=archive_month,
    selected_type=archive_type,
    alphabetical=archive_alphabetical,
)

if visible_archived_bills_df.empty:
    if archived_bills_df.empty:
        st.info("No completed bills yet.")
    else:
        st.info("No archived bills match these filters.")
else:
    archived = visible_archived_bills_df[EDITABLE_COLUMNS].copy()
    archived["card"] = archived["card"].fillna("")
    archived["notes"] = archived["notes"].fillna("")
    st.dataframe(
        archived,
        hide_index=True,
        width="stretch",
        column_order=[
            "name", "bill_type", "base_amount", "start_month", "duration_months",
            "card", "due_day", "notes",
        ],
        column_config={
            "name": st.column_config.TextColumn("Name"),
            "bill_type": st.column_config.TextColumn("Type"),
            "base_amount": st.column_config.NumberColumn(
                "Monthly amount",
                format="₱%.2f",
            ),
            "start_month": st.column_config.DateColumn(
                "Start month",
                format="YYYY-MM-DD",
            ),
            "duration_months": st.column_config.NumberColumn("Duration (mo.)"),
            "card": st.column_config.TextColumn("Card / tag"),
            "due_day": st.column_config.NumberColumn("Due day"),
            "notes": st.column_config.TextColumn("Notes"),
        },
    )
