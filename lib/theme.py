"""Shared color palette for charts, cards, and tables.

Values are the validated **dark-mode** steps from the reference palette
(dataviz skill) — this app commits to a single dark theme (see
.streamlit/config.toml) rather than adapting to the viewer's OS setting, so
we only need one column.
"""

# Categorical slots (fixed order — never cycle these)
SERIES_BLUE = "#3987e5"     # income
SERIES_ORANGE = "#d95926"   # bills / commitments
SERIES_AQUA = "#199e70"     # savings balance
SERIES_VIOLET = "#9085e9"   # secondary card accent (e.g. a second card brand)

# Status palette (fixed — meaning never carried by color alone; pair with icon/label)
STATUS_GOOD = "#0ca30c"
STATUS_WARNING = "#fab219"
STATUS_SERIOUS = "#ec835a"
STATUS_CRITICAL = "#d03b3b"

# Chrome / ink — dark surface set
PAGE_PLANE = "#0d0d0d"
CHART_SURFACE = "#1a1a19"
CARD_SURFACE = "#212120"
PRIMARY_INK = "#ffffff"
SECONDARY_INK = "#c3c2b7"
MUTED_INK = "#898781"
GRIDLINE = "#2c2c2a"
BASELINE = "#383835"
BORDER = "rgba(255,255,255,0.10)"
SUCCESS_TEXT = "#0ca30c"

FONT_FAMILY = "system-ui, -apple-system, 'Segoe UI', sans-serif"

# A couple of distinct gradients for the credit-card visual, keyed by known
# card tags. Deliberately generic (not a copy of any real bank's card art) —
# just enough to tell cards apart at a glance. Anything not in this map
# (custom "Other" tags, "Cash") falls back to CARD_GRADIENT_DEFAULT.
CARD_GRADIENTS = {
    "RCBC": (SERIES_BLUE, "#1c5cab"),
    "BDO": (SERIES_AQUA, "#0d5c42"),
}
CARD_GRADIENT_DEFAULT = (SERIES_VIOLET, "#4a3aa7")

# For the "outstanding balance by month" line chart: one line per card, plus
# a savings-balance line. Savings keeps SERIES_AQUA (same meaning as in the
# main projection chart); card lines cycle through the rest, deliberately
# *not* reusing aqua so a card's line is never confused with the savings
# line when both are on screen together.
CARD_LINE_COLORS = [SERIES_BLUE, SERIES_ORANGE, SERIES_VIOLET, "#eda100"]
