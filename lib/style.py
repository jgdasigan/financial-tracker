"""Small CSS/HTML helpers for the dark, card-based look.

Streamlit's `st.container(border=True)` already gives theme-aware rounded
cards for free, so most of the app leans on that rather than raw CSS. The
handful of things Streamlit has no built-in primitive for — the credit-card
visual, status pills — live here as plain HTML snippets.
"""
from __future__ import annotations

import streamlit as st

from lib import theme

_CSS = f"""
<style>
/* Trim the default top padding so the dashboard sits higher on the page. */
.block-container {{ padding-top: 2rem; }}

/* Sidebar as a flex column so the logout button (rendered last, see
   lib/auth.py) can be pinned to the bottom edge via margin-top:auto instead
   of sitting wherever it happens to fall in the nav + page-controls flow. */
div[data-testid="stSidebarContent"] {{
    display: flex !important;
    flex-direction: column !important;
}}
.st-key-logout_btn {{
    margin-top: auto;
    padding-top: 1rem;
}}

/* Bordered containers (our "cards") get a touch more rounding + a subtle
   surface tint so they read as distinct tiles against the page background. */
div[data-testid="stVerticalBlockBorderWrapper"] {{
    border-radius: 14px !important;
}}

.ft-pill {{
    display: inline-flex;
    align-items: center;
    gap: 4px;
    padding: 2px 10px;
    border-radius: 999px;
    font-size: 0.75rem;
    font-weight: 600;
    white-space: nowrap;
}}
.ft-pill-good {{ background: rgba(12,163,12,0.16); color: {theme.STATUS_GOOD}; }}
.ft-pill-warning {{ background: rgba(250,178,25,0.16); color: {theme.STATUS_WARNING}; }}
.ft-pill-critical {{ background: rgba(208,59,59,0.18); color: {theme.STATUS_CRITICAL}; }}
.ft-pill-muted {{ background: rgba(137,135,129,0.16); color: {theme.MUTED_INK}; }}

.ft-card {{
    border-radius: 16px;
    padding: 18px 20px;
    color: #ffffff;
    display: flex;
    flex-direction: column;
    justify-content: space-between;
    min-height: 148px;
    box-shadow: 0 6px 20px rgba(0,0,0,0.35);
}}
.ft-card-top {{ display: flex; justify-content: space-between; align-items: flex-start; }}
.ft-card-brand {{ font-weight: 700; font-size: 0.95rem; letter-spacing: 0.02em; }}
.ft-card-number {{ font-size: 1.05rem; letter-spacing: 0.18em; opacity: 0.85; margin: 14px 0; }}
.ft-card-bottom {{ display: flex; justify-content: space-between; align-items: baseline; }}
.ft-card-label {{ font-size: 0.7rem; opacity: 0.75; text-transform: uppercase; letter-spacing: 0.04em; }}
.ft-card-amount {{ font-size: 1.35rem; font-weight: 700; margin-top: 2px; }}
.ft-card-sub {{ font-size: 0.75rem; opacity: 0.8; }}

.ft-row {{
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 10px 4px;
}}
.ft-row + .ft-row {{ border-top: 1px solid {theme.BORDER}; }}
.ft-row-left {{ display: flex; align-items: center; gap: 10px; }}
.ft-row-icon {{
    width: 34px; height: 34px; border-radius: 10px;
    background: {theme.CARD_SURFACE};
    display: flex; align-items: center; justify-content: center;
    font-size: 1rem;
}}
.ft-row-name {{ font-weight: 600; font-size: 0.92rem; }}
.ft-row-sub {{ font-size: 0.78rem; color: {theme.MUTED_INK}; }}
.ft-row-amount {{ font-weight: 700; font-size: 0.95rem; }}

/* -------------------------------------------------------------- buttons -- */
.stButton > button, .stFormSubmitButton > button, .stDownloadButton > button {{
    border-radius: 10px !important;
    border: 1px solid {theme.BORDER} !important;
    font-weight: 600;
    padding: 0.5rem 1.1rem;
    transition: transform 0.06s ease, box-shadow 0.15s ease, border-color 0.15s ease;
}}
.stButton > button:hover, .stFormSubmitButton > button:hover, .stDownloadButton > button:hover {{
    transform: translateY(-1px);
    box-shadow: 0 6px 16px rgba(0,0,0,0.35);
    border-color: {theme.SERIES_BLUE} !important;
}}
.stButton > button:active, .stFormSubmitButton > button:active {{
    transform: translateY(0);
}}
.stButton > button[kind="primary"], .stFormSubmitButton > button[kind="primary"] {{
    background: linear-gradient(135deg, {theme.SERIES_BLUE}, #1c5cab) !important;
    border: none !important;
}}
.stButton > button[kind="primary"]:hover, .stFormSubmitButton > button[kind="primary"]:hover {{
    box-shadow: 0 6px 18px rgba(57,135,229,0.45);
}}

/* --------------------------------------------------- dropdowns / inputs -- */
div[data-baseweb="select"] > div,
.stTextInput input, .stNumberInput input, .stDateInput input, .stTextArea textarea {{
    border-radius: 10px !important;
    border-color: {theme.BORDER} !important;
    transition: border-color 0.15s ease, box-shadow 0.15s ease;
}}
div[data-baseweb="select"]:focus-within > div,
.stTextInput input:focus, .stNumberInput input:focus, .stDateInput input:focus {{
    border-color: {theme.SERIES_BLUE} !important;
    box-shadow: 0 0 0 1px {theme.SERIES_BLUE} !important;
}}
/* Selected chips inside a multiselect */
span[data-baseweb="tag"] {{
    border-radius: 999px !important;
    background: rgba(57,135,229,0.22) !important;
}}
/* Dropdown menu panel */
ul[data-testid="stSelectboxVirtualDropdown"], div[data-baseweb="popover"] div[role="listbox"] {{
    border-radius: 12px !important;
    border: 1px solid {theme.BORDER} !important;
}}

/* -------------------------------------------------------- radio as pills -- */
div[role="radiogroup"] {{
    gap: 6px;
    flex-wrap: wrap;
}}
div[role="radiogroup"] label {{
    border: 1px solid {theme.BORDER};
    border-radius: 999px;
    padding: 5px 14px 5px 10px;
    margin: 0 !important;
    transition: background 0.15s ease, border-color 0.15s ease;
}}
div[role="radiogroup"] label:hover {{
    border-color: {theme.SERIES_BLUE};
    background: rgba(57,135,229,0.10);
}}

/* ---------------------------------------------------------- expanders -- */
div[data-testid="stExpander"] {{
    border-radius: 12px !important;
    border-color: {theme.BORDER} !important;
}}

/* ------------------------------------------------------------- loading -- */
/* Streamlit dims stale content (opacity fade) while a rerun is in flight —
   that's the "breathing" look. Killing the fade and replacing it with an
   explicit top progress bar + a restyled status pill instead, so there's
   one unambiguous loading signal rather than the whole page dimming. */
[data-stale="true"] {{
    opacity: 1 !important;
    transition: none !important;
}}

.ft-loading-bar {{
    position: fixed;
    top: 0;
    left: 0;
    width: 100%;
    height: 3px;
    z-index: 10000;
    background: linear-gradient(90deg, transparent, {theme.SERIES_BLUE}, {theme.SERIES_AQUA}, transparent);
    background-size: 60% 100%;
    opacity: 0;
    pointer-events: none;
}}
body:has([data-testid="stStatusWidget"]) .ft-loading-bar {{
    opacity: 1;
    animation: ft-loading-sweep 1.1s ease-in-out infinite;
}}
@keyframes ft-loading-sweep {{
    0%   {{ background-position: -60% 0; }}
    100% {{ background-position: 160% 0; }}
}}

/* The little "Running..." indicator itself, restyled as a clear pill with
   a spinner instead of the default faint icon. */
div[data-testid="stStatusWidget"] {{
    background: {theme.CARD_SURFACE};
    border: 1px solid {theme.BORDER};
    border-radius: 999px;
    padding: 4px 12px 4px 8px !important;
}}
div[data-testid="stStatusWidget"] svg {{
    animation: ft-spin 0.8s linear infinite;
}}
@keyframes ft-spin {{
    from {{ transform: rotate(0deg); }}
    to {{ transform: rotate(360deg); }}
}}
</style>
"""


def inject_css() -> None:
    st.markdown(_CSS, unsafe_allow_html=True)
    # Always present in the DOM; the CSS above only shows it (and animates
    # it) while Streamlit's own status widget is mounted, i.e. mid-rerun.
    st.markdown('<div class="ft-loading-bar"></div>', unsafe_allow_html=True)


def pill(label: str, kind: str = "muted") -> str:
    return f'<span class="ft-pill ft-pill-{kind}">{label}</span>'


def credit_card_html(card_name: str, due_this_month: float, active_count: int) -> str:
    # Deliberately zero-indented / single-line: st.markdown still runs its
    # content through a markdown pass even in unsafe_allow_html mode, and
    # any line indented 4+ spaces reads as a fenced code block — which is
    # exactly what nested, pretty-printed HTML looks like. Multi-line HTML
    # with real indentation rendered as literal escaped text instead of
    # markup for anything past the first couple of nesting levels.
    start, end = theme.CARD_GRADIENTS.get(card_name, theme.CARD_GRADIENT_DEFAULT)
    plural = "installment" if active_count == 1 else "installments"
    return (
        f'<div class="ft-card" style="background: linear-gradient(135deg, {start}, {end});">'
        f'<div class="ft-card-top">'
        f'<div class="ft-card-brand">💳 {card_name}</div>'
        f'<div style="font-size:0.75rem; opacity:0.8;">{active_count} active {plural}</div>'
        f'</div>'
        f'<div class="ft-card-number">•••• •••• •••• ••••</div>'
        f'<div class="ft-card-bottom"><div>'
        f'<div class="ft-card-label">Due this month</div>'
        f'<div class="ft-card-amount">₱{due_this_month:,.2f}</div>'
        f'</div></div>'
        f'</div>'
    )


def payment_row_html(icon: str, name: str, subtitle: str, amount: float, pill_html: str = "") -> str:
    return (
        f'<div class="ft-row">'
        f'<div class="ft-row-left">'
        f'<div class="ft-row-icon">{icon}</div>'
        f'<div>'
        f'<div class="ft-row-name">{name}</div>'
        f'<div class="ft-row-sub">{subtitle}</div>'
        f'</div></div>'
        f'<div style="display:flex; align-items:center; gap:10px;">'
        f'{pill_html}'
        f'<div class="ft-row-amount">₱{amount:,.2f}</div>'
        f'</div>'
        f'</div>'
    )
