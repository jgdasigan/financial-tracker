"""Single-user password gate.

Not a real multi-user auth system — this app has exactly one intended user,
so a shared password compared with a constant-time check is enough. The
password lives in st.secrets, same place as the DB connection string, so it
never ends up in the repo.
"""
from __future__ import annotations

import hmac

import streamlit as st

SESSION_KEY = "authenticated"


def _check_password(entered: str) -> bool:
    try:
        expected = st.secrets["APP_PASSWORD"]
    except Exception:
        return False
    return hmac.compare_digest(entered, expected)


def require_login() -> None:
    """Call at the very top of the app, before any page content renders.
    Stops the script here until the correct password has been entered."""
    if st.session_state.get(SESSION_KEY):
        return

    try:
        st.secrets["APP_PASSWORD"]
    except Exception:
        st.error(
            "No APP_PASSWORD set in `.streamlit/secrets.toml` — add one "
            "(see `secrets.toml.example`) before running the app."
        )
        st.stop()

    _, center, _ = st.columns([1, 1.2, 1])
    with center:
        st.write("")
        st.write("")
        with st.container(border=True):
            st.markdown("### 💸 Bill & Savings Tracker")
            st.caption("Enter the app password to continue.")
            with st.form("login_form"):
                entered = st.text_input("Password", type="password")
                submitted = st.form_submit_button("Log in", type="primary")
                if submitted:
                    if _check_password(entered):
                        st.session_state[SESSION_KEY] = True
                        st.rerun()
                    else:
                        st.error("Wrong password.")
    st.stop()


def logout_button() -> None:
    """Call this *after* the page's own content has rendered (in particular,
    after st.navigation(...).run()) so it ends up last in the sidebar's DOM
    order — combined with the margin-top:auto rule in lib/style.py, that's
    what pins it to the bottom of the sidebar instead of sitting wherever it
    was called from."""
    if st.sidebar.button("Log out", key="logout_btn"):
        st.session_state.pop(SESSION_KEY, None)
        st.rerun()
