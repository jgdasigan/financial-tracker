"""Check whether a new purchase fits your budget before you commit to it —
either as a credit-card installment (first-month conversion fee included) or
as a straight cash payment deducted from savings right now."""
from datetime import date

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from lib import calculations as calc
from lib import db
from lib import theme

st.title("🛒 Affordability checker")
st.caption("Model a purchase — on installment or in cash — and see if it still leaves you with leeway.")

try:
    settings = db.get_settings()
    bills_df = db.list_bills()
    bonuses_df = db.list_income_bonuses()
except Exception as e:
    st.error(f"Couldn't reach the database: {e}")
    st.stop()

existing_bills = bills_df.to_dict("records") if not bills_df.empty else []
extra_income = calc.sum_bonuses_by_month(bonuses_df.to_dict("records")) if not bonuses_df.empty else {}
CARD_CHOICES = db.KNOWN_CARDS + ["Other"]

st.subheader("The item")
with st.container(border=True):
    payment_mode = st.radio("Payment mode", ["Card (installment)", "Cash (pay from savings now)"], horizontal=True)
    is_card = payment_mode.startswith("Card")

    c1, c2, c3 = st.columns(3)
    with c1:
        item_name = st.text_input("Item name", placeholder="e.g. New phone")
        price = st.number_input("Total price", min_value=0.0, step=100.0)

    if is_card:
        with c2:
            down_payment = st.number_input("Down payment (optional)", min_value=0.0, step=100.0)
            duration_months = st.number_input("Installment term (months)", min_value=1, step=1, value=6)
        with c3:
            fee_mode = st.radio("Conversion fee (first month only)", ["Fixed amount", "% of price"], horizontal=True)
            fee_value = st.number_input("Fee value", min_value=0.0, step=10.0)
            start_month = st.date_input("First payment month", value=date(date.today().year, date.today().month, 1))
        card_choice = st.selectbox("Card", CARD_CHOICES)
        card = st.text_input("Card name", key="custom_card").strip() or "Other" if card_choice == "Other" else card_choice
    else:
        with c2:
            start_month = st.date_input("Purchase month", value=date(date.today().year, date.today().month, 1))
        down_payment, duration_months, fee_value, fee_mode = 0.0, 1, 0.0, "Fixed amount"
        card = "Cash"

st.subheader("Budget assumptions")
with st.container(border=True):
    b1, b2, b3 = st.columns(3)
    with b1:
        monthly_income = st.number_input("Monthly income", min_value=0.0, step=500.0, value=settings["monthly_income"])
    with b2:
        starting_savings = st.number_input("Current savings", min_value=0.0, step=500.0, value=settings["current_savings"])
    with b3:
        safety_buffer = st.number_input(
            "Minimum leftover/savings to keep", min_value=0.0, step=100.0, value=settings["safety_buffer"],
            help="Card: flag a month as tight if leftover dips below this. Cash: flag the purchase if it would leave less than this in savings.",
        )

if price <= 0 or not item_name.strip():
    st.info("Enter an item name and price to run the check.")
    st.stop()

start = date(start_month.year, start_month.month, 1)

if is_card:
    monthly_amount = calc.installment_amount(price, down_payment, int(duration_months))
    conversion_fee = calc.fee_amount(monthly_amount, fee_value, fee_mode.startswith("%"))
    proposed_bill = {
        "name": item_name.strip(), "bill_type": "installment", "base_amount": monthly_amount,
        "conversion_fee": conversion_fee, "start_month": start, "duration_months": int(duration_months),
    }
else:
    monthly_amount, conversion_fee = price, 0.0
    proposed_bill = {
        "name": item_name.strip(), "bill_type": "onetime", "base_amount": price,
        "conversion_fee": 0.0, "start_month": start, "duration_months": 1,
    }

st.divider()
m1, m2 = st.columns(2)
if is_card:
    m1.metric("Monthly installment", f"₱{monthly_amount:,.2f}")
    m2.metric("First-month payment (with fee)", f"₱{monthly_amount + conversion_fee:,.2f}", delta=f"+₱{conversion_fee:,.2f} fee")
else:
    m1.metric("Price (paid now)", f"₱{price:,.2f}")
    m2.metric("Savings after purchase", f"₱{starting_savings - price:,.2f}", delta=f"-₱{price:,.2f}")

# --------------------------------------------------------------- verdict --
st.divider()
if is_card:
    horizon_months = int(duration_months) + 2  # runway past the last installment
    result = calc.check_affordability(
        existing_bills=existing_bills, proposed_bill=proposed_bill, horizon_start=start,
        n_months=horizon_months, monthly_income=monthly_income, starting_savings=starting_savings,
        safety_buffer=safety_buffer, extra_income=extra_income,
    )
    if result.affordable:
        st.success(f"✅ **Affordable** — leftover stays at or above ₱{safety_buffer:,.2f} every month through {result.comparison['month'].iloc[-1]}.")
    else:
        st.error(
            f"❌ **Not affordable as planned** — leftover dips below your ₱{safety_buffer:,.2f} buffer starting "
            f"**{result.first_shortfall_month}**, short by ₱{result.worst_shortfall:,.2f} at the worst point."
        )
    comparison = result.comparison
else:
    horizon_months = 4  # just enough runway to visualize recovery after the hit
    cash_result = calc.check_cash_affordability(starting_savings, price, safety_buffer)
    if cash_result.affordable:
        st.success(f"✅ **Affordable in cash** — savings would drop to ₱{cash_result.savings_after:,.2f}, still at or above your ₱{safety_buffer:,.2f} buffer.")
    else:
        st.error(
            f"❌ **Not affordable in cash right now** — savings would drop to ₱{cash_result.savings_after:,.2f}, "
            f"short of your ₱{safety_buffer:,.2f} buffer by ₱{cash_result.shortfall:,.2f}."
        )
    before_schedule, months = calc.build_schedule(existing_bills, start, horizon_months)
    before = calc.project_savings(calc.monthly_totals(before_schedule), months, monthly_income, starting_savings, extra_income)
    after_schedule, _ = calc.build_schedule(existing_bills + [proposed_bill], start, horizon_months)
    after = calc.project_savings(calc.monthly_totals(after_schedule), months, monthly_income, starting_savings, extra_income)
    comparison = pd.DataFrame({
        "month": before["month"], "leftover_before": before["leftover"], "leftover_after": after["leftover"],
        "savings_balance_after": after["savings_balance"],
    })
    comparison["affordable"] = True
    comparison.loc[0, "affordable"] = cash_result.affordable  # only the purchase month carries the verdict

st.subheader("Leftover per month: before vs. after this purchase")
colors = [theme.STATUS_GOOD if ok else theme.STATUS_CRITICAL for ok in comparison["affordable"]]
labels = ["OK" if ok else "Short" for ok in comparison["affordable"]]

fig = go.Figure()
fig.add_trace(go.Bar(x=comparison["month"], y=comparison["leftover_before"], name="Leftover today", marker_color=theme.MUTED_INK, opacity=0.5))
fig.add_trace(go.Bar(x=comparison["month"], y=comparison["leftover_after"], name="Leftover with this purchase", marker_color=colors, text=labels, textposition="outside"))
if safety_buffer > 0:
    fig.add_hline(y=safety_buffer, line_dash="dot", line_color=theme.BASELINE, annotation_text="buffer")
fig.add_hline(y=0, line_color=theme.BASELINE)
fig.update_layout(
    barmode="group", plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
    font=dict(family=theme.FONT_FAMILY, color=theme.PRIMARY_INK),
    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0),
    margin=dict(t=40, l=10, r=10, b=10),
    yaxis=dict(title="₱", gridcolor=theme.GRIDLINE, zerolinecolor=theme.BASELINE),
    xaxis=dict(gridcolor=theme.GRIDLINE),
)
with st.container(border=True):
    st.plotly_chart(fig, width="stretch")

with st.expander("Monthly detail"):
    detail = comparison.copy()
    for col in ["leftover_before", "leftover_after", "savings_balance_after"]:
        detail[col] = detail[col].map(lambda v: f"₱{v:,.2f}")
    detail["affordable"] = detail["affordable"].map(lambda ok: "✅ OK" if ok else "❌ Short")
    st.dataframe(
        detail.rename(columns={
            "leftover_before": "Leftover (today)", "leftover_after": "Leftover (with purchase)",
            "savings_balance_after": "Savings balance", "affordable": "Status",
        }),
        width="stretch", hide_index=True,
    )

st.divider()
if st.button("Commit this purchase to my bills", type="primary"):
    db.add_bill(
        name=proposed_bill["name"], bill_type=proposed_bill["bill_type"],
        base_amount=proposed_bill["base_amount"], conversion_fee=proposed_bill["conversion_fee"],
        start_month=proposed_bill["start_month"], duration_months=proposed_bill["duration_months"],
        card=card, notes=f"Price ₱{price:,.2f}" + (f", down payment ₱{down_payment:,.2f}" if is_card else ", paid in cash"),
    )
    st.success(f"Added “{proposed_bill['name']}” to your bills. See it on the Dashboard.")
