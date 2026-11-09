"""Small CSS/HTML helpers for the dark, card-based look.

Streamlit's `st.container(border=True)` already gives theme-aware rounded
cards for free, so most of the app leans on that rather than raw CSS. The
handful of things Streamlit has no built-in primitive for — the credit-card
visual, status pills — live here as plain HTML snippets.
"""
from __future__ import annotations

from html import escape

import streamlit as st

from lib import theme

_CSS = f"""
<style>
.stApp {{
    background:
        radial-gradient(circle at 12% -10%, rgba(108,140,255,0.16), transparent 32rem),
        radial-gradient(circle at 92% 4%, rgba(53,214,180,0.09), transparent 28rem),
        {theme.PAGE_PLANE};
}}

header[data-testid="stHeader"] {{
    background: rgba(6,16,31,0.72);
    border-bottom: 1px solid {theme.BORDER};
    backdrop-filter: blur(18px);
}}

.block-container {{
    max-width: 1440px;
    padding-top: 2.6rem;
    padding-bottom: 4rem;
}}

h1, h2, h3 {{
    letter-spacing: -0.035em;
}}
h1 {{
    font-weight: 800 !important;
    color: {theme.PRIMARY_INK};
    text-shadow: 0 8px 30px rgba(108,140,255,0.15);
}}
h2, h3 {{
    font-weight: 700 !important;
}}
p, label {{
    color: {theme.SECONDARY_INK};
}}

section[data-testid="stSidebar"] {{
    background:
        linear-gradient(180deg, rgba(17,36,58,0.96), rgba(7,21,38,0.98));
    border-right: 1px solid {theme.BORDER};
}}
section[data-testid="stSidebar"] [data-testid="stSidebarNav"] a {{
    border: 1px solid transparent;
    border-radius: 12px;
    margin: 3px 10px;
    transition: background 0.16s ease, border-color 0.16s ease, transform 0.16s ease;
}}
section[data-testid="stSidebar"] [data-testid="stSidebarNav"] a:hover {{
    background: rgba(108,140,255,0.10);
    border-color: {theme.BORDER};
    transform: translateX(2px);
}}
section[data-testid="stSidebar"] [data-testid="stSidebarNav"] a[aria-current="page"] {{
    background: linear-gradient(135deg, rgba(108,140,255,0.22), rgba(53,214,180,0.08));
    border-color: rgba(108,140,255,0.35);
    box-shadow: inset 3px 0 0 {theme.SERIES_BLUE};
}}

.ft-sidebar-brand {{
    position: fixed;
    left: 1rem;
    bottom: 4.25rem;
    z-index: 100;
    display: flex;
    width: 17rem;
    box-sizing: border-box;
    align-items: center;
    gap: 10px;
    margin: 0;
    padding: 0.75rem;
    border: 1px solid {theme.BORDER};
    border-radius: 14px;
    background: rgba(108,140,255,0.08);
}}
.ft-sidebar-mark {{
    display: flex;
    width: 34px;
    height: 34px;
    align-items: center;
    justify-content: center;
    border-radius: 10px;
    background: linear-gradient(145deg, {theme.SERIES_BLUE}, #4f6fe5);
    color: #ffffff;
    font-weight: 800;
}}
.ft-sidebar-name {{
    color: {theme.PRIMARY_INK};
    font-size: 0.86rem;
    font-weight: 750;
    line-height: 1.2;
}}
.ft-sidebar-sub {{
    margin-top: 2px;
    color: {theme.MUTED_INK};
    font-size: 0.65rem;
}}

/* Sidebar as a flex column so the logout button (rendered last, see
   lib/auth.py) can be pinned to the bottom edge via margin-top:auto instead
   of sitting wherever it happens to fall in the nav + page-controls flow. */
div[data-testid="stSidebarContent"] {{
    display: flex !important;
    flex-direction: column !important;
    min-height: 100dvh;
    padding-bottom: 10rem;
}}
.st-key-logout_btn {{
    position: fixed;
    left: 1rem;
    bottom: 1rem;
    z-index: 100;
    width: 17rem;
    margin: 0 !important;
    border: 1px solid {theme.BORDER};
    border-radius: 14px;
    padding: 0;
    background: transparent;
}}

/* Bordered containers (our "cards") get a touch more rounding + a subtle
   surface tint so they read as distinct tiles against the page background. */
div[data-testid="stVerticalBlockBorderWrapper"] {{
    background: linear-gradient(
        145deg,
        rgba(17,36,58,0.88),
        rgba(10,27,47,0.78)
    );
    border: 1px solid {theme.BORDER} !important;
    border-radius: 18px !important;
    box-shadow:
        0 18px 45px rgba(0,0,0,0.20),
        inset 0 1px 0 rgba(255,255,255,0.025);
    backdrop-filter: blur(16px);
}}

.st-key-login_card {{
    margin-top: clamp(2rem, 10vh, 7rem);
}}
.st-key-login_card div[data-testid="stVerticalBlockBorderWrapper"] {{
    padding: 0.8rem;
    border-color: rgba(108,140,255,0.28) !important;
    border-radius: 24px !important;
    box-shadow:
        0 30px 80px rgba(0,0,0,0.34),
        0 0 0 1px rgba(255,255,255,0.02);
}}
.ft-login-brand {{
    padding: 0.5rem 0 1.1rem;
    text-align: center;
}}
.ft-login-mark {{
    display: inline-flex;
    width: 54px;
    height: 54px;
    align-items: center;
    justify-content: center;
    margin-bottom: 1rem;
    border: 1px solid rgba(108,140,255,0.34);
    border-radius: 17px;
    background: linear-gradient(145deg, rgba(108,140,255,0.24), rgba(53,214,180,0.10));
    color: #dfe7ff;
    font-size: 1.5rem;
    font-weight: 800;
    box-shadow: 0 12px 30px rgba(25,49,105,0.30);
}}
.ft-login-eyebrow {{
    color: {theme.SERIES_AQUA};
    font-size: 0.68rem;
    font-weight: 800;
    letter-spacing: 0.16em;
}}
.ft-login-title {{
    margin-top: 0.35rem;
    color: {theme.PRIMARY_INK};
    font-size: 1.45rem;
    font-weight: 800;
    letter-spacing: -0.035em;
}}
.ft-login-subtitle {{
    max-width: 300px;
    margin: 0.45rem auto 0;
    color: {theme.MUTED_INK};
    font-size: 0.84rem;
    line-height: 1.55;
}}
.st-key-login_card [data-testid="stForm"] {{
    border-top: 1px solid {theme.BORDER};
    padding-top: 1.15rem;
}}

.ft-section-heading {{
    display: flex;
    align-items: flex-start;
    gap: 11px;
    margin: 1.4rem 0 0.75rem;
}}
.ft-section-marker {{
    width: 4px;
    height: 34px;
    flex: 0 0 4px;
    margin-top: 2px;
    border-radius: 999px;
    background: linear-gradient({theme.SERIES_BLUE}, {theme.SERIES_AQUA});
}}
.ft-section-title {{
    color: {theme.PRIMARY_INK};
    font-size: 1.12rem;
    font-weight: 750;
    letter-spacing: -0.02em;
}}
.ft-section-description {{
    margin-top: 0.2rem;
    color: {theme.MUTED_INK};
    font-size: 0.79rem;
    line-height: 1.5;
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
    position: relative;
    overflow: hidden;
    border: 1px solid rgba(255,255,255,0.16);
    border-radius: 16px;
    padding: 14px 15px;
    color: #ffffff;
    display: flex;
    flex-direction: column;
    justify-content: space-between;
    min-height: 116px;
    box-shadow: 0 14px 30px rgba(0,0,0,0.24);
}}
.ft-card-top {{ display: flex; flex-direction: column; gap: 8px; align-items: flex-start; position: relative; z-index: 1; }}
.ft-card-brand {{
    display: flex;
    align-items: center;
    gap: 8px;
    min-width: 0;
    font-weight: 700;
    font-size: 0.82rem;
    line-height: 1.2;
}}
.ft-card-logo {{
    display: inline-flex;
    width: 28px;
    height: 28px;
    flex: 0 0 28px;
    align-items: center;
    justify-content: center;
    border: 1px solid rgba(255,255,255,0.24);
    border-radius: 9px;
    background: rgba(255,255,255,0.14);
    font-size: 0.68rem;
    font-weight: 800;
}}
.ft-card-active {{ font-size: 0.67rem; opacity: 0.76; }}
.ft-card-bottom {{ display: flex; justify-content: space-between; align-items: baseline; position: relative; z-index: 1; }}
.ft-card-label {{ font-size: 0.62rem; opacity: 0.75; text-transform: uppercase; letter-spacing: 0.04em; }}
.ft-card-amount {{ font-size: 1.02rem; font-weight: 700; margin-top: 2px; }}
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

.ft-kpi {{
    display: flex;
    min-height: 66px;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    padding: 0.15rem 0;
    box-sizing: border-box;
    text-align: center;
    transform: translateY(-4px);
}}
div[data-testid="stVerticalBlockBorderWrapper"]:has(.ft-kpi) {{
    display: flex;
    min-height: 66px;
    align-items: center;
    padding: 0 !important;
}}
div[data-testid="stVerticalBlockBorderWrapper"]:has(.ft-kpi)
div[data-testid="stVerticalBlock"] {{
    width: 100%;
    gap: 0 !important;
}}
.ft-kpi-label {{
    color: {theme.MUTED_INK};
    font-size: 0.76rem;
}}
.ft-kpi-value {{
    margin-top: 0.18rem;
    color: {theme.PRIMARY_INK};
    font-size: 1.35rem;
    font-weight: 750;
    letter-spacing: -0.02em;
}}

.ft-upcoming-scroll {{
    height: 370px;
    max-height: 370px;
    overflow-y: auto;
    overscroll-behavior: contain;
    padding-right: 8px;
}}

.st-key-projection_panel div[data-testid="stVerticalBlockBorderWrapper"],
.st-key-upcoming_panel div[data-testid="stVerticalBlockBorderWrapper"] {{
    height: 455px;
    min-height: 455px;
}}

/* -------------------------------------------------------------- buttons -- */
.stButton > button, .stFormSubmitButton > button, .stDownloadButton > button {{
    min-height: 2.25rem;
    border-radius: 999px !important;
    border: 1px solid {theme.BORDER} !important;
    font-weight: 600;
    font-size: 0.78rem;
    padding: 0.36rem 0.9rem;
    background: rgba(17,36,58,0.42);
    box-shadow: none;
    transition: background 0.14s ease, box-shadow 0.14s ease, border-color 0.14s ease;
}}
.stButton > button:hover, .stFormSubmitButton > button:hover, .stDownloadButton > button:hover {{
    background: rgba(108,140,255,0.10);
    box-shadow: 0 0 0 3px rgba(108,140,255,0.10);
    border-color: {theme.SERIES_BLUE} !important;
}}
.stButton > button:active, .stFormSubmitButton > button:active {{
    background: rgba(108,140,255,0.16);
}}
.stButton > button[kind="primary"], .stFormSubmitButton > button[kind="primary"] {{
    background: #526fe0 !important;
    border-color: #6f89ed !important;
    color: #ffffff !important;
}}
.stButton > button[kind="primary"]:hover, .stFormSubmitButton > button[kind="primary"]:hover {{
    background: #7b98ff !important;
    box-shadow: 0 0 0 3px rgba(108,140,255,0.18);
}}
.stButton > button:focus-visible,
.stFormSubmitButton > button:focus-visible,
.stDownloadButton > button:focus-visible {{
    outline: 2px solid {theme.SERIES_AQUA};
    outline-offset: 2px;
}}
div[class*="st-key-del_"] button {{
    color: {theme.STATUS_CRITICAL};
    border-color: rgba(255,107,122,0.24) !important;
}}
.st-key-logout_btn button {{
    width: 100%;
    justify-content: flex-start;
    padding-left: 0.8rem;
    border: 0 !important;
    background: transparent !important;
    color: {theme.MUTED_INK};
    box-shadow: none !important;
}}
.st-key-logout_btn button:hover {{
    background: rgba(108,140,255,0.08) !important;
    color: {theme.PRIMARY_INK};
}}
div[class*="st-key-dashboard_hide_"] button {{
    width: 2.1rem;
    min-height: 2.1rem;
    padding: 0 !important;
    border-radius: 999px !important;
    color: {theme.MUTED_INK};
}}
div[class*="st-key-dashboard_hide_"] button:hover {{
    color: {theme.PRIMARY_INK};
}}

/* --------------------------------------------------- dropdowns / inputs -- */
div[data-baseweb="select"] > div {{
    min-height: 2.2rem;
    border-radius: 999px !important;
    border-color: rgba(151,178,218,0.16) !important;
    background: rgba(8,22,39,0.72) !important;
    box-shadow: none !important;
    font-size: 0.78rem;
    transition: border-color 0.15s ease, background 0.15s ease;
}}
div[data-baseweb="select"]:hover > div {{
    border-color: rgba(108,140,255,0.48) !important;
    background: rgba(108,140,255,0.08) !important;
}}
.stTextInput input, .stNumberInput input, .stDateInput input, .stTextArea textarea {{
    min-height: 2.65rem;
    border-radius: 12px !important;
    border-color: {theme.BORDER} !important;
    background: rgba(6,16,31,0.62) !important;
    transition: border-color 0.15s ease, box-shadow 0.15s ease;
}}
div[data-baseweb="select"]:focus-within > div,
.stTextInput input:focus, .stNumberInput input:focus, .stDateInput input:focus {{
    border-color: {theme.SERIES_BLUE} !important;
    box-shadow: 0 0 0 3px rgba(108,140,255,0.16) !important;
}}

div[data-testid="stSegmentedControl"] [data-baseweb="button-group"] {{
    overflow: hidden;
    padding: 3px;
    border: 1px solid {theme.BORDER};
    border-radius: 10px;
    background: rgba(6,16,31,0.55);
}}
div[data-testid="stSegmentedControl"] button {{
    border: 0 !important;
    border-radius: 7px !important;
}}

div[data-testid="stCheckbox"],
div[data-testid="stToggle"] {{
    padding: 0.15rem 0;
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
    overflow: hidden;
    background: rgba(13,27,46,0.72);
    border-radius: 14px !important;
    border: 1px solid {theme.BORDER} !important;
}}

div[data-testid="stMetric"] {{
    background: linear-gradient(145deg, rgba(17,36,58,0.82), rgba(10,27,47,0.70));
    border: 1px solid {theme.BORDER};
    border-radius: 16px;
    padding: 1rem 1.1rem;
}}

div[data-testid="stDataFrame"],
div[data-testid="stDataEditor"] {{
    position: relative;
    overflow: hidden;
    background: rgba(8,22,39,0.92);
    border: 1px solid rgba(151,178,218,0.18);
    border-radius: 16px;
    box-shadow:
        0 18px 42px rgba(0,0,0,0.18),
        inset 0 1px 0 rgba(255,255,255,0.025);
}}
div[data-testid="stDataFrame"] [role="columnheader"],
div[data-testid="stDataEditor"] [role="columnheader"] {{
    color: {theme.MUTED_INK} !important;
    background: #0d2036 !important;
    border-color: {theme.BORDER} !important;
    font-size: 0.68rem !important;
    font-weight: 750 !important;
    letter-spacing: 0.045em;
    text-transform: uppercase;
}}
div[data-testid="stDataFrame"] [role="gridcell"],
div[data-testid="stDataEditor"] [role="gridcell"] {{
    color: {theme.SECONDARY_INK} !important;
    border-color: rgba(151,178,218,0.09) !important;
    font-size: 0.78rem !important;
}}
div[data-testid="stDataFrame"] [role="row"]:hover [role="gridcell"],
div[data-testid="stDataEditor"] [role="row"]:hover [role="gridcell"] {{
    background: rgba(108,140,255,0.08) !important;
}}
div[data-testid="stDataFrame"] button,
div[data-testid="stDataEditor"] button {{
    border-radius: 999px !important;
    color: {theme.MUTED_INK} !important;
}}
div[data-testid="stTable"] {{
    overflow: hidden;
    border: 1px solid {theme.BORDER};
    border-radius: 12px;
}}
div[data-testid="stTable"] table {{
    margin: 0;
}}
div[data-testid="stTable"] th {{
    background: #10243b;
    color: {theme.PRIMARY_INK};
}}
div[data-testid="stTable"] td {{
    border-color: rgba(151,178,218,0.09);
}}

div[data-testid="stTabs"] [data-baseweb="tab-list"] {{
    gap: 6px;
    padding: 5px;
    border: 1px solid {theme.BORDER};
    border-radius: 12px;
    background: rgba(7,21,38,0.68);
}}
div[data-testid="stTabs"] [data-baseweb="tab"] {{
    min-height: 2.35rem;
    border-radius: 8px;
    padding: 0.35rem 0.8rem;
}}
div[data-testid="stTabs"] [aria-selected="true"] {{
    background: rgba(108,140,255,0.16);
    color: {theme.PRIMARY_INK};
}}

div[data-testid="stAlert"] {{
    border-radius: 14px;
    border: 1px solid {theme.BORDER};
    box-shadow: 0 10px 28px rgba(0,0,0,0.14);
}}

hr {{
    border-color: {theme.BORDER} !important;
}}

[data-testid="stCaptionContainer"] {{
    color: {theme.MUTED_INK};
}}

div[data-testid="stSlider"] [role="slider"] {{
    border: 2px solid {theme.PAGE_PLANE};
    box-shadow: 0 0 0 3px rgba(108,140,255,0.18);
}}

::-webkit-scrollbar {{
    width: 10px;
    height: 10px;
}}
::-webkit-scrollbar-track {{
    background: rgba(6,16,31,0.45);
}}
::-webkit-scrollbar-thumb {{
    background: #2a4564;
    border: 2px solid {theme.PAGE_PLANE};
    border-radius: 999px;
}}
::-webkit-scrollbar-thumb:hover {{
    background: {theme.SERIES_BLUE};
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

@media (max-width: 768px) {{
    .block-container {{
        padding: 1.25rem 1rem 3rem;
    }}

    h1 {{
        font-size: 2rem !important;
        line-height: 1.14 !important;
    }}

    h2 {{
        font-size: 1.45rem !important;
    }}

    div[data-testid="stHorizontalBlock"] {{
        flex-wrap: wrap !important;
        gap: 0.75rem !important;
    }}

    div[data-testid="stHorizontalBlock"] > div[data-testid="column"] {{
        flex: 1 1 100% !important;
        width: 100% !important;
        min-width: 100% !important;
    }}

    div[data-testid="stVerticalBlockBorderWrapper"] {{
        border-radius: 15px !important;
    }}

    .st-key-login_card {{
        margin-top: 1rem;
    }}

    .st-key-login_card div[data-testid="stVerticalBlockBorderWrapper"] {{
        padding: 0.25rem;
        border-radius: 18px !important;
    }}

    .stButton > button,
    .stFormSubmitButton > button,
    .stDownloadButton > button {{
        width: 100%;
        min-height: 2.9rem;
    }}

    .ft-card {{
        min-height: 120px;
        padding: 15px;
    }}

    .st-key-projection_panel div[data-testid="stVerticalBlockBorderWrapper"],
    .st-key-upcoming_panel div[data-testid="stVerticalBlockBorderWrapper"] {{
        height: auto;
        min-height: 0;
    }}

    .ft-upcoming-scroll {{
        height: auto;
        max-height: 350px;
    }}

    .ft-row {{
        align-items: flex-start;
        flex-wrap: wrap;
        gap: 8px;
        padding: 12px 2px;
    }}

    .ft-row-left {{
        flex: 1 1 calc(100% - 50px);
        min-width: 0;
    }}

    .ft-row > div:last-child {{
        width: 100%;
        justify-content: space-between;
        padding-left: 44px;
    }}

    .ft-row-name,
    .ft-row-sub {{
        overflow-wrap: anywhere;
    }}

    div[data-testid="stDataFrame"],
    div[data-testid="stDataEditor"] {{
        max-width: calc(100vw - 2rem);
        overflow-x: auto;
    }}

    div[role="radiogroup"] label {{
        flex: 1 1 auto;
        justify-content: center;
    }}
}}
</style>
"""


def inject_css() -> None:
    st.markdown(_CSS, unsafe_allow_html=True)
    # Always present in the DOM; the CSS above only shows it (and animates
    # it) while Streamlit's own status widget is mounted, i.e. mid-rerun.
    st.markdown('<div class="ft-loading-bar"></div>', unsafe_allow_html=True)


def section_header(title: str, description: str = "") -> None:
    description_html = (
        f'<div class="ft-section-description">{escape(description)}</div>'
        if description
        else ""
    )
    st.markdown(
        '<div class="ft-section-heading">'
        '<div class="ft-section-marker"></div>'
        '<div>'
        f'<div class="ft-section-title">{escape(title)}</div>'
        f'{description_html}'
        '</div>'
        '</div>',
        unsafe_allow_html=True,
    )


def sidebar_brand() -> None:
    with st.sidebar:
        st.markdown(
            '<div class="ft-sidebar-brand">'
            '<div class="ft-sidebar-mark">₱</div>'
            '<div>'
            '<div class="ft-sidebar-name">Financial Tracker</div>'
            '<div class="ft-sidebar-sub">PRIVATE WORKSPACE</div>'
            '</div>'
            '</div>',
            unsafe_allow_html=True,
        )


def pill(label: str, kind: str = "muted") -> str:
    return (
        f'<span class="ft-pill ft-pill-{escape(kind)}">'
        f'{escape(label)}</span>'
    )


def credit_card_html(
    card_name: str,
    due_this_month: float,
    active_count: int,
    due_month_label: str,
    hide_amount: bool = False,
) -> str:
    # Deliberately zero-indented / single-line: st.markdown still runs its
    # content through a markdown pass even in unsafe_allow_html mode, and
    # any line indented 4+ spaces reads as a fenced code block — which is
    # exactly what nested, pretty-printed HTML looks like. Multi-line HTML
    # with real indentation rendered as literal escaped text instead of
    # markup for anything past the first couple of nesting levels.
    start, end = theme.CARD_GRADIENTS.get(card_name, theme.CARD_GRADIENT_DEFAULT)
    safe_card_name = escape(card_name)
    logo = theme.CARD_LOGOS.get(card_name, card_name[:1].upper())
    plural = "installment" if active_count == 1 else "installments"
    displayed_amount = "••••••" if hide_amount else f"₱{due_this_month:,.2f}"
    return (
        f'<div class="ft-card" style="background: linear-gradient(135deg, {start}, {end});">'
        f'<div class="ft-card-top">'
        f'<div class="ft-card-brand">'
        f'<span class="ft-card-logo">{escape(logo)}</span>'
        f'<span>{safe_card_name}</span>'
        f'</div>'
        f'<div class="ft-card-active">{active_count} active {plural}</div>'
        f'</div>'
        f'<div class="ft-card-bottom"><div>'
        f'<div class="ft-card-label">Due {escape(due_month_label)}</div>'
        f'<div class="ft-card-amount">{displayed_amount}</div>'
        f'</div></div>'
        f'</div>'
    )


def payment_row_html(
    icon: str,
    name: str,
    subtitle: str,
    amount: float,
    pill_html: str = "",
    hide_amount: bool = False,
) -> str:
    displayed_amount = "••••••" if hide_amount else f"₱{amount:,.2f}"
    return (
        f'<div class="ft-row">'
        f'<div class="ft-row-left">'
        f'<div class="ft-row-icon">{escape(icon)}</div>'
        f'<div>'
        f'<div class="ft-row-name">{escape(name)}</div>'
        f'<div class="ft-row-sub">{escape(subtitle)}</div>'
        f'</div></div>'
        f'<div style="display:flex; align-items:center; gap:10px;">'
        f'{pill_html}'
        f'<div class="ft-row-amount">{displayed_amount}</div>'
        f'</div>'
        f'</div>'
    )
