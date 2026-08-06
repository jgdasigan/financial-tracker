"""Entry point / navigation router. Actual page content lives in views/."""
import streamlit as st

from lib import auth
from lib import style

st.set_page_config(page_title="Bill & Savings Tracker", page_icon="💸", layout="wide")
style.inject_css()
auth.require_login()

pg = st.navigation([
    st.Page("views/dashboard.py", title="Dashboard", icon="🏠", default=True),
    st.Page("views/manage_bills.py", title="Manage bills", icon="📋"),
    st.Page("views/affordability_checker.py", title="Affordability", icon="🛒"),
    st.Page("views/weekly_income.py", title="Weekly income", icon="🗓️"),
    st.Page("views/settings.py", title="Settings", icon="⚙️"),
])
pg.run()

# Rendered last so it lands at the bottom of the sidebar's DOM order, below
# whatever page-specific sidebar controls the current page just added.
auth.logout_button()
