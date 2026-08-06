"""Add, edit, and delete bills: recurring subscriptions, credit-card
installments (with a first-month conversion fee), and one-time expenses."""
from datetime import date

import streamlit as st

from lib import bill_edits
from lib import db

st.title("📋 Manage bills")

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
    choice = st.selectbox("Card / tag", options, index=index, key=f"{key_prefix}_card_choice")
    if choice == "Other (type below)":
        typed = st.text_input("Custom tag name", key=f"{key_prefix}_card_custom").strip()
        if typed:
            db.add_tag(typed)  # remembered immediately, not just once a bill is saved
        return typed or None
    return None if choice == "None" else choice


# ------------------------------------------------------------------ add form --
st.subheader("Add a bill")
bill_type = st.selectbox(
    "Type", ["recurring", "installment", "onetime", "pakaskas"], format_func=str.title,
    help=TYPE_HELP["recurring"], key="add_bill_type",
)
st.caption(TYPE_HELP[bill_type])

card = _pick_card(None, "add")  # optional for every type — "None" is always the first choice

with st.form("add_bill_form", clear_on_submit=True), st.container(border=True):
    name = st.text_input("Name", placeholder="e.g. Clothes, Shoes, Groceries")
    col1, col2 = st.columns(2)

    if bill_type == "installment":
        with col1:
            monthly_amount = st.number_input("Monthly installment amount (excl. fee)", min_value=0.0, step=50.0)
            duration_months = st.number_input("Number of months", min_value=1, step=1, value=3)
        with col2:
            fee_mode = st.radio("Conversion fee (first month only)", ["Fixed amount", "% of monthly amount"], horizontal=True)
            fee_value = st.number_input("Fee value", min_value=0.0, step=10.0)
            start_month = st.date_input("Start month", value=date(date.today().year, date.today().month, 1))
        conversion_fee = round(monthly_amount * fee_value / 100, 2) if fee_mode.startswith("%") else round(fee_value, 2)

    elif bill_type == "recurring":
        with col1:
            monthly_amount = st.number_input("Monthly amount", min_value=0.0, step=50.0)
            ongoing = st.checkbox("Ongoing (no end date)", value=True)
        with col2:
            start_month = st.date_input("Start month", value=date(date.today().year, date.today().month, 1))
            duration_months = None if ongoing else st.number_input("Runs for how many months", min_value=1, step=1, value=6)
        conversion_fee = 0.0

    elif bill_type == "pakaskas":
        with col1:
            monthly_amount = st.number_input("Monthly amount", min_value=0.0, step=50.0)
            duration_months = st.number_input("Number of months", min_value=1, step=1, value=1)
        with col2:
            start_month = st.date_input("Start month", value=date(date.today().year, date.today().month, 1))
        conversion_fee = 0.0

    else:  # onetime
        with col1:
            monthly_amount = st.number_input("Amount", min_value=0.0, step=50.0)
        with col2:
            start_month = st.date_input("Month it's due", value=date(date.today().year, date.today().month, 1))
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
EDITABLE_COLUMNS = [
    "id", "name", "bill_type", "base_amount", "conversion_fee",
    "start_month", "duration_months", "card", "due_day", "include_in_projection", "notes",
]

st.subheader("Current bills")
st.caption("Edit any cell directly. Use the row's ⋮ menu (or select + Delete key) to remove a row, or the blank bottom row to add one.")

# with st.form("register_tag_form", clear_on_submit=True):
#     t1, t2 = st.columns([4, 1])
#     with t1:
#         new_tag = st.text_input("Register a new card/tag", placeholder="e.g. Metrobank — makes it pickable in the Card/tag column below")
#     with t2:
#         st.write("")
#         register = st.form_submit_button("Add tag")
#     if register and new_tag.strip():
#         db.add_tag(new_tag.strip())
#         st.rerun()

if bills_df.empty:
    st.info("No bills yet — add one above.")
else:
    editable = bills_df[EDITABLE_COLUMNS].copy()
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

    save_col, undo_col, _spacer = st.columns([2, 2, 19])
    if save_col.button("Save changes", type="primary"):
        diff = bill_edits.diff_bills_edit(bills_df, edited)
        for bill_id in diff.deletes:
            db.delete_bill(bill_id)
        for kwargs in diff.adds:
            db.add_bill(**kwargs)
        for bill_id, fields in diff.updates:
            db.update_bill(bill_id, **fields)

        msg = []
        if diff.updates: msg.append(f"{len(diff.updates)} updated")
        if diff.adds: msg.append(f"{len(diff.adds)} added")
        if diff.deletes: msg.append(f"{len(diff.deletes)} deleted")
        if diff.skipped: msg.append(f"{diff.skipped} incomplete new row(s) skipped")
        st.success(", ".join(msg) if msg else "No changes.")
        st.session_state.pop(EDITOR_KEY, None)
        st.rerun()

    if undo_col.button("Undo changes"):
        st.session_state.pop(EDITOR_KEY, None)
        st.rerun()
