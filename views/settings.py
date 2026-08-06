"""Income sources, current savings, and the minimum monthly buffer used everywhere else."""
from datetime import date

import streamlit as st

from lib import db

st.title("⚙️ Settings")

try:
    settings = db.get_settings()
    income_sources = db.list_income_sources()
    income_bonuses = db.list_income_bonuses()
except Exception as e:
    st.error(f"Couldn't reach the database: {e}")
    st.stop()

st.caption("These values feed the Dashboard projection and the Affordability checker's defaults.")

# Global layout is "wide" (set once in app.py for the dashboard), so center
# this form in a narrower column rather than letting it stretch edge to edge.
_, center, _ = st.columns([1, 2, 1])
with center:
    st.subheader("Monthly income")
    st.caption("Add one row per income stream (day job, side gig, …) — the total below feeds everything else.")
    with st.container(border=True):
        if income_sources.empty:
            st.caption("No income sources yet — add one below.")
        else:
            for _, row in income_sources.iterrows():
                r1, r2, r3 = st.columns([3, 2, 1])
                r1.write(row["name"])
                r2.write(f"₱{row['amount']:,.2f}")
                if r3.button("Delete", key=f"del_income_{row['id']}"):
                    db.delete_income_source(int(row["id"]))
                    st.rerun()
            st.divider()
        st.markdown(f"**Total: ₱{settings['monthly_income']:,.2f}**")

    with st.form("add_income_source_form", clear_on_submit=True):
        c1, c2, c3 = st.columns([3, 2, 1])
        with c1:
            source_name = st.text_input("Source name", placeholder="e.g. Day job, Freelance")
        with c2:
            source_amount = st.number_input("Monthly amount", min_value=0.0, step=500.0)
        with c3:
            st.write("")
            add_source = st.form_submit_button("Add")
        if add_source:
            if not source_name.strip():
                st.error("Give the income source a name.")
            elif source_amount <= 0:
                st.error("Amount must be greater than 0.")
            else:
                db.add_income_source(source_name.strip(), source_amount)
                st.rerun()

    st.write("")
    st.subheader("One-time income")
    st.caption("A bonus, 13th month pay, tax refund, … added on top of the recurring total for just that month.")
    with st.container(border=True):
        if income_bonuses.empty:
            st.caption("None logged yet — add one below.")
        else:
            for _, row in income_bonuses.iterrows():
                b1, b2, b3, b4 = st.columns([3, 2, 2, 1])
                b1.write(row["name"])
                b2.write(row["month"].strftime("%b %Y"))
                b3.write(f"₱{row['amount']:,.2f}")
                if b4.button("Delete", key=f"del_bonus_{row['id']}"):
                    db.delete_income_bonus(int(row["id"]))
                    st.rerun()

    with st.form("add_income_bonus_form", clear_on_submit=True):
        c1, c2, c3, c4 = st.columns([3, 2, 2, 1])
        with c1:
            bonus_name = st.text_input("Name", placeholder="e.g. December bonus")
        with c2:
            bonus_month = st.date_input("Month", value=date(date.today().year, 12, 1))
        with c3:
            bonus_amount = st.number_input("Amount", min_value=0.0, step=500.0)
        with c4:
            st.write("")
            add_bonus = st.form_submit_button("Add")
        if add_bonus:
            if not bonus_name.strip():
                st.error("Give it a name.")
            elif bonus_amount <= 0:
                st.error("Amount must be greater than 0.")
            else:
                db.add_income_bonus(bonus_name.strip(), date(bonus_month.year, bonus_month.month, 1), bonus_amount)
                st.rerun()

    st.write("")
    with st.form("settings_form"), st.container(border=True):
        current_savings = st.number_input(
            "Current savings", min_value=0.0, step=500.0, value=settings["current_savings"],
            help="Your savings balance as of today. The dashboard projects forward from here.",
        )
        safety_buffer = st.number_input(
            "Minimum leftover to keep each month", min_value=0.0, step=100.0, value=settings["safety_buffer"],
            help="A month is flagged as tight if leftover would dip below this amount, not just below zero.",
        )
        submitted = st.form_submit_button("Save", type="primary")
        if submitted:
            db.save_settings(current_savings, safety_buffer)
            st.success("Saved.")
            st.rerun()

    st.write("")
    with st.container(border=True):
        st.markdown("**Database connection**")
        try:
            db.get_engine()
            st.success("Connected.")
        except Exception as e:
            st.error(f"Not connected: {e}")
