"""Dashboard — projected bills, income, and savings for the months ahead."""
from datetime import date, timedelta

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from lib import calculations as calc
from lib import bill_edits
from lib import db
from lib import style
from lib import theme

st.title("💸 Bill & Savings Tracker")
st.caption("Projected monthly payments and savings, computed from your income, current savings, and active bills.")

try:
    settings = db.get_settings()
    bills_df = db.list_bills()
    bonuses_df = db.list_income_bonuses()
except Exception as e:
    st.error(
        "Couldn't reach the database. Check that DB_URL is set in "
        ".streamlit/secrets.toml — see secrets.toml.example.\n\n"
        f"Details: {e}"
    )
    st.stop()

all_bills = bills_df.to_dict("records") if not bills_df.empty else []
bills = [
    bill
    for bill in all_bills
    if not bill_edits.is_completed_bill(bill)
]
extra_income = calc.sum_bonuses_by_month(bonuses_df.to_dict("records")) if not bonuses_df.empty else {}
# Pakaskas can opt out of the leftover/savings math (it's sometimes not
# really your money) while still showing up in its own table and in
# "Upcoming payments" — so the projection uses a filtered list, everything
# display-only uses the full `bills` list.
projection_bills = [b for b in bills if b.get("include_in_projection", True)]

with st.sidebar:
    st.header("Projection window")
    today = date.today()
    horizon_start = st.date_input("Start month", value=date(today.year, today.month, 1))
    n_months = st.slider("Months to project", min_value=3, max_value=24, value=3)


def _amounts_hidden(section_key: str) -> bool:
    state_key = f"dashboard_hide_{section_key}"
    if state_key not in st.session_state:
        st.session_state[state_key] = True
    help_text = (
        "Show amounts"
        if st.session_state[state_key]
        else "Hide amounts"
    )
    if st.button(
        "👁" if st.session_state[state_key] else "🙈",
        key=f"{state_key}_button",
        help=help_text,
        type="tertiary",
    ):
        st.session_state[state_key] = not st.session_state[state_key]
    return st.session_state[state_key]


def _currency(value: float, hidden: bool) -> str:
    return "••••••" if hidden else f"₱{value:,.2f}"

if not bills:
    st.info("No bills yet. Add your recurring bills and installments on **Manage bills** to see a projection.")

schedule_df, months = calc.build_schedule(projection_bills, calc.month_start(horizon_start), n_months)
totals = calc.monthly_totals(schedule_df)
projection = calc.project_savings(totals, months, settings["monthly_income"], settings["current_savings"], extra_income)

this_month_bills = float(totals.iloc[0]) if len(totals) else 0.0
this_month_income = float(projection["income"].iloc[0]) if len(projection) else settings["monthly_income"]
this_month_leftover = float(projection["leftover"].iloc[0]) if len(projection) else this_month_income - this_month_bills
this_month_bonus = extra_income.get(calc.month_start(horizon_start), 0.0)

income_label = "💰 Monthly income" + (" (incl. bonus)" if this_month_bonus else "")

# --------------------------------------------------------------------- KPIs --
_, overview_eye = st.columns([20, 1])
with overview_eye:
    overview_hidden = _amounts_hidden("overview")

k1, k2, k3, k4 = st.columns(4)
kpi_specs = [
    (
        k1,
        "🏦 Current savings",
        _currency(settings["current_savings"], overview_hidden),
    ),
    (k2, income_label, _currency(this_month_income, overview_hidden)),
    (
        k3,
        "🧾 This month's bills",
        _currency(this_month_bills, overview_hidden),
    ),
    (
        k4,
        "✅ This month's leftover",
        _currency(this_month_leftover, overview_hidden),
    ),
]
for col, label, value in kpi_specs:
    with col:
        with st.container(border=True):
            st.markdown(
                f'<div class="ft-kpi">'
                f'<div class="ft-kpi-label">{label}</div>'
                f'<div class="ft-kpi-value">{value}</div>'
                f'</div>',
                unsafe_allow_html=True,
            )

st.write("")


def _full_height_table(
    df: pd.DataFrame,
    hidden: bool,
    bold_last_row: bool = False,
):
    """st.dataframe defaults to a fixed height that scrolls internally once a
    table has more than a handful of rows — size it to the row count instead
    so the whole schedule is visible with no inner scrollbar.

    Pre-formats to plain strings rather than handing st.dataframe a Styler
    with .format(na_rep=""): st.dataframe doesn't render the Styler's HTML
    directly, and blank cells came back through as the literal text "None"
    instead of empty — stringifying ourselves leaves no NaN for it to guess
    about."""
    str_df = df.map(
        lambda value: _currency(value, hidden) if pd.notna(value) else ""
    )
    styled = str_df.style
    if bold_last_row:
        styled = styled.set_properties(subset=pd.IndexSlice[[str_df.index[-1]], :], **{"font-weight": "bold"})
    height = (len(df) + 1) * 35 + 3
    st.dataframe(styled, width="stretch", height=height)


def _apply_chart_privacy(fig: go.Figure, hidden: bool) -> None:
    if not hidden:
        return
    fig.update_yaxes(showticklabels=False, title=None)
    fig.update_traces(
        hovertemplate="%{x}<extra>%{fullData.name}</extra>",
    )


# ------------------------------------------------------------- credit cards --
# Pakaskas counts here regardless of include_in_projection: the card bill is
# still due either way, whether or not the money is projected as "yours".
card_bills = [b for b in bills if b["bill_type"] in ("installment", "pakaskas") and calc.card_tag(b)]
cards_seen = {
    card_name: {"due": 0.0, "count": 0}
    for card_name in db.KNOWN_CARDS
}
for b in card_bills:
    due_this_month = calc.bill_amount_for_month(b, calc.month_start(today)) or 0.0
    if due_this_month <= 0:
        continue  # nothing charged to this card this month
    card_name = calc.card_tag(b)
    entry = cards_seen.setdefault(card_name, {"due": 0.0, "count": 0})
    entry["due"] += due_this_month
    entry["count"] += 1

if cards_seen:
    cards_title, cards_eye = st.columns([20, 1])
    with cards_title:
        st.subheader("Cards")
    with cards_eye:
        cards_hidden = _amounts_hidden("cards")

    card_cols = st.columns(len(cards_seen))
    for i, (card_name, info) in enumerate(cards_seen.items()):
        with card_cols[i]:
            st.markdown(
                style.credit_card_html(
                    card_name,
                    info["due"],
                    info["count"],
                    hide_amount=cards_hidden,
                ),
                unsafe_allow_html=True,
            )
    st.write("")

    # ------------------------------------------------------ card due by month --
    card_trends_title, card_trends_eye = st.columns([20, 1])
    with card_trends_title:
        st.markdown("##### Card payments due by month")
    with card_trends_eye:
        card_trends_hidden = _amounts_hidden("card_trends")
    st.caption("What's actually charged to each card that month, alongside your projected savings balance.")
    with st.container(border=True):
        fig = go.Figure()
        for i, card_name in enumerate(cards_seen):
            due = calc.card_due_by_month(bills, card_name, months)
            fig.add_trace(go.Scatter(
                x=projection["month"], y=due, name=f"{card_name} due",
                mode="lines+markers", line=dict(color=theme.CARD_LINE_COLORS[i % len(theme.CARD_LINE_COLORS)], width=2),
                marker=dict(size=6),
            ))
        fig.add_trace(go.Scatter(
            x=projection["month"], y=projection["savings_balance"], name="Savings balance",
            mode="lines+markers", line=dict(color=theme.SERIES_AQUA, width=2), marker=dict(size=6),
        ))
        fig.update_layout(
            plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
            font=dict(family=theme.FONT_FAMILY, color=theme.PRIMARY_INK),
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0),
            margin=dict(t=10, l=10, r=10, b=10),
            yaxis=dict(title="₱", gridcolor=theme.GRIDLINE, zerolinecolor=theme.BASELINE),
            xaxis=dict(gridcolor=theme.GRIDLINE),
            hovermode="x unified",
        )
        _apply_chart_privacy(fig, card_trends_hidden)
        st.plotly_chart(fig, width="stretch")

        due_rows = {
            f"{card_name} due": calc.card_due_by_month(bills, card_name, months)
            for card_name in cards_seen
        }
        due_rows["Savings balance"] = projection["savings_balance"].tolist()
        due_df = pd.DataFrame(due_rows, index=[calc.month_label(m) for m in months]).T
        _full_height_table(due_df, hidden=card_trends_hidden)
    st.write("")

# ------------------------------------------------------ main layout: chart + upcoming --
main_col, side_col = st.columns([2, 1])

with main_col:
    with st.container(border=True):
        projection_title, projection_eye = st.columns([12, 1])
        with projection_title:
            st.markdown(f"<div style='color:{theme.MUTED_INK}; font-size:0.8rem;'>Projected balance, {n_months} months out</div>", unsafe_allow_html=True)
        with projection_eye:
            projection_hidden = _amounts_hidden("projection")
        end_balance = projection["savings_balance"].iloc[-1] if len(projection) else settings["current_savings"]
        st.markdown(f"<div style='font-size:1.8rem; font-weight:700; margin-bottom:6px;'>{_currency(end_balance, projection_hidden)}</div>", unsafe_allow_html=True)

        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=projection["month"], y=projection["income"], name="Income",
            mode="lines", line=dict(color=theme.SERIES_BLUE, width=2),
        ))
        fig.add_trace(go.Scatter(
            x=projection["month"], y=projection["total_bills"], name="Total bills",
            mode="lines", line=dict(color=theme.SERIES_ORANGE, width=2),
        ))
        fig.add_trace(go.Scatter(
            x=projection["month"], y=projection["savings_balance"], name="Savings balance",
            mode="lines+markers", line=dict(color=theme.SERIES_AQUA, width=2), marker=dict(size=7),
        ))
        fig.update_layout(
            plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
            font=dict(family=theme.FONT_FAMILY, color=theme.PRIMARY_INK),
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0),
            margin=dict(t=10, l=10, r=10, b=10),
            yaxis=dict(title="₱", gridcolor=theme.GRIDLINE, zerolinecolor=theme.BASELINE),
            xaxis=dict(gridcolor=theme.GRIDLINE),
            hovermode="x unified",
        )
        _apply_chart_privacy(fig, projection_hidden)
        st.plotly_chart(fig, width="stretch")

    negative_months = projection[projection["leftover"] < 0]
    if not negative_months.empty:
        st.warning(
            f"⚠️ Bills exceed income in **{len(negative_months)}** month(s): "
            + ", ".join(negative_months["month"].tolist())
            + ". Your savings balance absorbs the gap above."
        )

with side_col:
    with st.container(border=True):
        upcoming_title, upcoming_eye = st.columns([8, 1])
        with upcoming_title:
            st.markdown("**Upcoming payments**")
        with upcoming_eye:
            upcoming_hidden = _amounts_hidden("upcoming")
        payment_window = st.segmented_control(
            "Payment window",
            ["Week", "Month"],
            default="Week",
            label_visibility="collapsed",
            width="stretch",
        )

        if payment_window == "Month":
            period_start = calc.month_start(today)
            period_end = calc.add_months(period_start, 1) - timedelta(days=1)
            empty_message = "Nothing due this month."
        else:
            period_start = today - timedelta(days=today.weekday())
            period_end = period_start + timedelta(days=6)
            empty_message = "Nothing due this week."

        icon_by_type = {"installment": "💳", "recurring": "🔁", "onetime": "🧾", "pakaskas": "🤝"}
        upcoming = calc.bills_due_between(
            bills,
            period_start,
            period_end,
        )
        if not upcoming:
            st.caption(empty_message)
        payment_rows = []
        for due_date, b, amt in upcoming:
            when = (
                "Today"
                if due_date == today
                else f"{due_date.strftime('%b')} {due_date.day}"
            )
            pill_kind = "warning" if due_date <= today else "muted"
            tag = calc.card_tag(b)
            subtitle = (
                f"Due {due_date.strftime('%A')}"
                + (f" · {tag}" if tag else "")
            )
            payment_rows.append(
                style.payment_row_html(
                    icon_by_type.get(b["bill_type"], "🧾"), b["name"], subtitle, amt,
                    pill_html=style.pill(when, pill_kind),
                    hide_amount=upcoming_hidden,
                )
            )
        if payment_rows:
            st.markdown(
                '<div class="ft-upcoming-scroll">'
                + "".join(payment_rows)
                + "</div>",
                unsafe_allow_html=True,
            )

st.write("")
schedule_title, schedule_eye = st.columns([20, 1])
with schedule_title:
    st.subheader("Full payments schedule")
with schedule_eye:
    schedule_hidden = _amounts_hidden("schedule")

all_tags = sorted({calc.card_tag(b) for b in bills if calc.card_tag(b)})
selected_tags = st.multiselect(
    "Filter by tag", all_tags, help="Leave empty to show every bill regardless of tag.",
) if all_tags else []
filtered_bills = [b for b in bills if not selected_tags or calc.card_tag(b) in selected_tags]

TABLE_SPECS = [
    ("Installments", "installment"),
    ("Recurring", "recurring"),
    ("One-time", "onetime"),
    ("Pakaskas", "pakaskas"),
]
table_groups = [
    (
        label,
        btype,
        [bill for bill in filtered_bills if bill["bill_type"] == btype],
    )
    for label, btype in TABLE_SPECS
]
table_groups = [group for group in table_groups if group[2]]

if table_groups:
    table_tabs = st.tabs(
        [
            f"{label} ({len(group)})"
            for label, _, group in table_groups
        ]
    )
    for tab, (label, btype, group) in zip(table_tabs, table_groups):
        with tab:
            if btype == "pakaskas":
                excluded = sum(
                    1
                    for bill in group
                    if not bill.get("include_in_projection", True)
                )
                if excluded:
                    st.caption(
                        f"{excluded} of {len(group)} excluded from the "
                        "leftover/savings math above — see Manage bills "
                        "to change."
                    )
            group_schedule, _ = calc.build_schedule(
                group,
                calc.month_start(horizon_start),
                n_months,
            )
            group_schedule.index.name = "Bill"
            group_schedule.loc["Total"] = group_schedule.sum(
                numeric_only=True,
                skipna=True,
            )
            _full_height_table(
                group_schedule,
                hidden=schedule_hidden,
                bold_last_row=True,
            )
elif not filtered_bills:
    st.caption("No bills match this filter.")

with st.expander("Monthly income / bills / savings detail"):
    detail = projection.copy()
    for col in ["income", "total_bills", "leftover", "savings_balance"]:
        detail[col] = detail[col].map(
            lambda value: _currency(value, schedule_hidden)
        )
    st.dataframe(detail, width="stretch", hide_index=True, height=(len(detail) + 1) * 35 + 3)
