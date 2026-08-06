"""Weekly income check — for the variable, weekly-paid income stream: log
what a given week's paycheck was, and check it against whatever bills have
their deadline inside that same week, before the next paycheck lands."""
from datetime import date

import streamlit as st

from lib import calculations as calc
from lib import db
from lib import style
from lib import theme

st.title("🗓️ Weekly income check")
st.caption("For the weekly/variable income stream — log a week's pay and check it against bills due that week.")

try:
    settings = db.get_settings()
    bills_df = db.list_bills()
    income_df = db.list_income_entries()
except Exception as e:
    st.error(f"Couldn't reach the database: {e}")
    st.stop()

bills = bills_df.to_dict("records") if not bills_df.empty else []
_ORDINALS = {1: "1st", 2: "2nd", 3: "3rd", 4: "4th"}
WEEK_LABELS = {w: f"{_ORDINALS[w]} week (days {lo}–{hi})" for w, (lo, hi) in calc.WEEK_DAY_RANGES.items()}

st.subheader("Pick a week")
with st.container(border=True):
    c1, c2 = st.columns(2)
    with c1:
        picked_day = st.date_input("Any date in the month", value=date.today())
    with c2:
        week_number = st.radio(
            "Week", list(WEEK_LABELS.keys()), format_func=lambda w: WEEK_LABELS[w], horizontal=True,
        )
    month = calc.month_start(picked_day)

    existing = income_df[(income_df["month"] == month) & (income_df["week_number"] == week_number)]
    default_amount = float(existing.iloc[0]["amount"]) if not existing.empty else 0.0
    default_notes = (existing.iloc[0]["notes"] or "") if not existing.empty else ""

    amount = st.number_input("Income for this week", min_value=0.0, step=500.0, value=default_amount)
    notes = st.text_input("Notes (optional)", value=default_notes, placeholder="e.g. sweldo from last week")
    if st.button("Save this week's income", type="primary"):
        db.upsert_income_entry(month, week_number, amount, notes.strip())
        st.success(f"Saved ₱{amount:,.2f} for {calc.week_label(month, week_number)}.")
        st.rerun()

week_lbl = calc.week_label(month, week_number)
due = calc.bills_due_in_week(bills, month, week_number)
total_due = sum(amt for _, amt in due)
leftover = amount - total_due

st.write("")
k1, k2, k3 = st.columns(3)
for col, label, value in [
    (k1, "Income this week", f"₱{amount:,.2f}"),
    (k2, "Bills due this week", f"₱{total_due:,.2f}"),
    (k3, "Leftover", f"₱{leftover:,.2f}"),
]:
    with col:
        with st.container(border=True):
            st.markdown(f"<div style='color:{theme.MUTED_INK}; font-size:0.8rem;'>{label}</div>", unsafe_allow_html=True)
            st.markdown(f"<div style='font-size:1.4rem; font-weight:700;'>{value}</div>", unsafe_allow_html=True)

buffer = settings["safety_buffer"]
if leftover >= buffer:
    st.success(f"**Enough for {week_lbl}** — ₱{leftover:,.2f} left over, at or above your ₱{buffer:,.2f} buffer.")
else:
    st.error(f"**Short for {week_lbl}** — short by ₱{buffer - leftover:,.2f} against your ₱{buffer:,.2f} buffer.")

st.subheader(f"Bills due — {week_lbl}")
with st.container(border=True):
    if not due:
        st.caption("No bills have a due day falling in this week. Set a bill's \"Due day of month\" on Manage bills.")
    else:
        icon_by_type = {"installment": "💳", "recurring": "🔁", "onetime": "🧾", "pakaskas": "🤝"}
        for bill, amt in sorted(due, key=lambda row: -row[1]):
            tag = calc.card_tag(bill)
            subtitle = f"Due day {int(bill.get('due_day') or 1)}" + (f" · {tag}" if tag else "")
            st.markdown(
                style.payment_row_html(icon_by_type.get(bill["bill_type"], "🧾"), bill["name"], subtitle, amt),
                unsafe_allow_html=True,
            )

with st.expander("All logged weeks"):
    if income_df.empty:
        st.caption("Nothing logged yet.")
    else:
        view = income_df.copy()
        view["Week"] = view.apply(lambda r: calc.week_label(r["month"], int(r["week_number"])), axis=1)
        view["Amount"] = view["amount"].map(lambda v: f"₱{v:,.2f}")
        st.dataframe(
            view[["Week", "Amount", "notes"]].rename(columns={"notes": "Notes"}),
            width="stretch", hide_index=True,
        )
