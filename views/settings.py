"""Income sources, current savings, and the minimum monthly buffer used everywhere else."""
from datetime import date

import streamlit as st

from lib import calculations as calc
from lib import db
from lib import style

st.title("⚙️ Settings")
st.caption(
    "Manage the income, savings, and safety assumptions used throughout "
    "the tracker."
)

try:
    settings = db.get_settings()
    income_sources = db.list_income_sources()
    income_bonuses = db.list_income_bonuses()
except Exception as e:
    st.error(f"Couldn't reach the database: {e}")
    st.stop()


def _pick_bonus_month() -> date:
    current_month = calc.month_start(date.today())
    first_option = calc.add_months(current_month, -60)
    month_options = calc.month_range(first_option, 181)
    default_month = date(current_month.year, 12, 1)
    default_index = (
        month_options.index(default_month)
        if default_month in month_options
        else 60
    )
    return st.selectbox(
        "Month",
        month_options,
        index=default_index,
        format_func=lambda month: month.strftime("%B %Y"),
        width=200,
    )


# Global layout is "wide" (set once in app.py for the dashboard), so center
# this form in a narrower column rather than letting it stretch edge to edge.
_, center, _ = st.columns([1, 2, 1])
with center:
    style.section_header(
        "Monthly income",
        "Add one row per income stream. Their total feeds every projection "
        "and affordability check.",
    )
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
    style.section_header(
        "One-time income",
        "Add bonuses, refunds, and other income that applies to one month.",
    )
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
            bonus_month = _pick_bonus_month()
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
    style.section_header(
        "Savings, onhand, and safety buffer",
        "Set today's balances and the minimum monthly room you want to "
        "preserve.",
    )
    with st.form("settings_form"):
        current_savings = st.number_input(
            "Current savings", min_value=0.0, step=500.0, value=settings["current_savings"],
            help="Your savings balance as of today. The dashboard projects forward from here.",
        )
        onhand = st.number_input(
            "Onhand",
            min_value=0.0,
            step=500.0,
            value=settings["onhand"],
            help="Cash currently available for weekly expenses.",
        )
        safety_buffer = st.number_input(
            "Minimum leftover to keep each month", min_value=0.0, step=100.0, value=settings["safety_buffer"],
            help="A month is flagged as tight if leftover would dip below this amount, not just below zero.",
        )
        submitted = st.form_submit_button("Save", type="primary")
        if submitted:
            db.save_settings(current_savings, onhand, safety_buffer)
            st.success("Saved.")
            st.rerun()

    st.write("")
    style.section_header(
        "Database connection",
        "Confirm that the selected data backend is reachable.",
    )
    with st.container(border=True):
        try:
            db.get_engine()
            st.success("Connected.")
        except Exception as e:
            st.error(f"Not connected: {e}")
