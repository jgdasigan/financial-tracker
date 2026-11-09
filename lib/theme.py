"""Shared color palette for charts, cards, and tables.

Values are the validated **dark-mode** steps from the reference palette
(dataviz skill) — this app commits to a single dark theme (see
.streamlit/config.toml) rather than adapting to the viewer's OS setting, so
we only need one column.
"""

# Categorical slots (fixed order — never cycle these)
SERIES_BLUE = "#6c8cff"     # income
SERIES_ORANGE = "#ff8a65"   # bills / commitments
SERIES_AQUA = "#35d6b4"     # savings balance
SERIES_VIOLET = "#aa8cff"   # secondary card accent (e.g. a second card brand)

# Status palette (fixed — meaning never carried by color alone; pair with icon/label)
STATUS_GOOD = "#45d483"
STATUS_WARNING = "#ffc857"
STATUS_SERIOUS = "#ff9f6e"
STATUS_CRITICAL = "#ff6b7a"

# Chrome / ink — dark surface set
PAGE_PLANE = "#06101f"
CHART_SURFACE = "#0d1b2e"
CARD_SURFACE = "#11243a"
PRIMARY_INK = "#f5f8ff"
SECONDARY_INK = "#c3cee0"
MUTED_INK = "#8fa2bd"
GRIDLINE = "#1d3550"
BASELINE = "#2a4564"
BORDER = "rgba(151, 178, 218, 0.16)"
SUCCESS_TEXT = "#45d483"

FONT_FAMILY = "'Manrope', system-ui, -apple-system, 'Segoe UI', sans-serif"

# A couple of distinct gradients for the credit-card visual, keyed by known
# card tags. Deliberately generic (not a copy of any real bank's card art) —
# just enough to tell cards apart at a glance. Anything not in this map
# (custom "Other" tags, "Cash") falls back to CARD_GRADIENT_DEFAULT.
CARD_GRADIENTS = {
    "RCBC": ("#4f6ff7", "#18367f"),
    "BDO": ("#b28a3d", "#66501f"),
    "Maribank CC": ("#ff7f6e", "#a6344f"),
    "Tiktok PayLater": ("#26344f", "#09111f"),
    "Shopee PayLater": ("#ff7148", "#9f2f24"),
}
CARD_GRADIENT_DEFAULT = (SERIES_VIOLET, "#503d9d")

CARD_LOGOS = {
    "RCBC": "R",
    "BDO": "BDO",
    "Maribank CC": "M",
    "Tiktok PayLater": "♪",
    "Shopee PayLater": "S",
}

# For the "outstanding balance by month" line chart: one line per card, plus
# a savings-balance line. Savings keeps SERIES_AQUA (same meaning as in the
# main projection chart); card lines cycle through the rest, deliberately
# *not* reusing aqua so a card's line is never confused with the savings
# line when both are on screen together.
CARD_LINE_COLORS = [SERIES_BLUE, SERIES_ORANGE, SERIES_VIOLET, "#ffc857"]
