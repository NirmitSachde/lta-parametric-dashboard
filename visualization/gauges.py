"""
Pilot Gauge Components
======================
Builds Plotly indicator (gauge) figures for the parametric design dashboard.

Color philosophy follows FAA CFR Title 14 Part 25.1322 and SFTE Reference
Handbook guidelines for flight test UI design:
    - Red:    Warning — immediate action required
    - Amber:  Caution — loss of redundancy / attention needed
    - Green:  Normal — satisfactory operating condition
    - Cyan:   Advisory / informational

Colors are MUTED (reduced saturation + brightness) to reduce eye strain
on dark backgrounds, per flight test display best practices.

Reference:
    Moore Good Ideas, "UI Design for Flight Test" (2020)
    FAA HF-STD-001, Color standards for ATC displays
"""

import plotly.graph_objects as go

# ---------------------------------------------------------------------------
# Muted Aviation Color Palette (dark-background optimized)
# ---------------------------------------------------------------------------
# These are deliberately desaturated compared to pure #00FF00 / #FF0000
# to reduce eye strain while maintaining instant recognition.

C_GREEN = "#4CAF7D"       # Muted green  — normal / positive
C_GREEN_DIM = "#2E7D55"   # Dimmed green — gauge band background
C_AMBER = "#D4A847"       # Muted amber  — caution
C_AMBER_DIM = "#8B7430"   # Dimmed amber — gauge band background
C_RED = "#C75050"         # Muted red    — warning / negative
C_RED_DIM = "#7D3535"     # Dimmed red   — gauge band background
C_CYAN = "#5BA4B5"        # Muted cyan   — advisory / info

# Neutral tones
C_BG_GAUGE = "#141D26"    # Gauge face  — very dark blue-gray
C_BORDER = "#263040"      # Gauge border — subtle blue-gray
C_TICK = "#4A5568"        # Tick marks   — medium gray
C_TICK_LABEL = "#718096"  # Tick labels  — lighter gray
C_TEXT = "#CBD5E0"         # Primary text — warm light gray
C_TEXT_DIM = "#718096"     # Secondary text — muted gray
C_NEEDLE = "#E2E8F0"      # Gauge needle — near-white

# State color mapping
STATE_COLORS = {
    "Positive Buoyancy": C_GREEN,
    "Neutral Buoyancy":  C_AMBER,
    "Negative Buoyancy": C_RED,
}

# Transparent background (dashboard provides page bg)
TRANSPARENT = "rgba(0,0,0,0)"

# Font
FONT_FAMILY = "'JetBrains Mono', 'Fira Code', 'Courier New', monospace"


# ---------------------------------------------------------------------------
# Internal: base gauge builder
# ---------------------------------------------------------------------------
def _build_gauge(
    value: float,
    title: str,
    suffix: str,
    range_max: float,
    steps: list,
    bar_color: str = C_NEEDLE,
    number_format: str = ".1f",
    range_min: float = 0.0,
) -> go.Figure:
    """
    Build a single Plotly gauge with aviation-instrument styling.
    Colored arc bands show operating zones; needle indicates current value.
    """
    fig = go.Figure(
        go.Indicator(
            mode="gauge+number",
            value=value,
            number={
                "suffix": suffix,
                "font": {"size": 14, "color": C_TEXT, "family": FONT_FAMILY},
                "valueformat": number_format,
            },
            title={
                "text": title,
                "font": {"size": 11, "color": C_TEXT_DIM, "family": FONT_FAMILY},
            },
            gauge={
                "axis": {
                    "range": [range_min, range_max],
                    "tickwidth": 1,
                    "tickcolor": C_TICK,
                    "tickfont": {"size": 9, "color": C_TICK_LABEL},
                },
                "bar": {"color": bar_color, "thickness": 0.15},
                "bgcolor": C_BG_GAUGE,
                "borderwidth": 1,
                "bordercolor": C_BORDER,
                "steps": steps,
                "threshold": {
                    "line": {"color": C_NEEDLE, "width": 2},
                    "thickness": 0.75,
                    "value": value,
                },
            },
        )
    )

    fig.update_layout(
        paper_bgcolor=TRANSPARENT,
        plot_bgcolor=TRANSPARENT,
        font={"color": C_TEXT, "family": FONT_FAMILY},
        margin=dict(l=30, r=30, t=50, b=25),
        height=210,
    )

    return fig


# ---------------------------------------------------------------------------
# Public: Individual gauge builders
# ---------------------------------------------------------------------------

def build_lift_force_gauge(lift_force_N: float, range_max: float = 10000.0) -> go.Figure:
    """Lift Force gauge — higher is better (green at top)."""
    return _build_gauge(
        value=lift_force_N,
        title="LIFT FORCE",
        suffix=" N",
        range_max=range_max,
        steps=[
            {"range": [0, range_max * 0.4], "color": C_RED_DIM},
            {"range": [range_max * 0.4, range_max * 0.7], "color": C_AMBER_DIM},
            {"range": [range_max * 0.7, range_max], "color": C_GREEN_DIM},
        ],
        bar_color=C_NEEDLE,
    )


def build_weight_force_gauge(weight_force_N: float, range_max: float = 10000.0) -> go.Figure:
    """Weight Force gauge — lower is better (green at bottom)."""
    return _build_gauge(
        value=weight_force_N,
        title="WEIGHT FORCE",
        suffix=" N",
        range_max=range_max,
        steps=[
            {"range": [0, range_max * 0.4], "color": C_GREEN_DIM},
            {"range": [range_max * 0.4, range_max * 0.7], "color": C_AMBER_DIM},
            {"range": [range_max * 0.7, range_max], "color": C_RED_DIM},
        ],
        bar_color=C_NEEDLE,
    )


def build_net_force_gauge(net_force_N: float, range_max: float = 10000.0) -> go.Figure:
    """
    Net Force gauge — symmetric around zero.
    Positive (ascending) = green needle, Negative (descending) = red needle.
    """
    sym = abs(range_max)
    bar_color = C_GREEN if net_force_N >= 0 else C_RED

    return _build_gauge(
        value=net_force_N,
        title="NET FORCE",
        suffix=" N",
        range_min=-sym,
        range_max=sym,
        steps=[
            {"range": [-sym, -sym * 0.2], "color": C_RED_DIM},
            {"range": [-sym * 0.2, sym * 0.2], "color": C_AMBER_DIM},
            {"range": [sym * 0.2, sym], "color": C_GREEN_DIM},
        ],
        bar_color=C_NEEDLE,
    )


def build_brs_gauge(brs_rpm: float, range_max: float = 5000.0) -> go.Figure:
    """Balanced Rotational Speed gauge (RPM). Lower = easier to achieve."""
    return _build_gauge(
        value=brs_rpm,
        title="BRS",
        suffix=" RPM",
        range_max=range_max,
        steps=[
            {"range": [0, range_max * 0.35], "color": C_GREEN_DIM},
            {"range": [range_max * 0.35, range_max * 0.65], "color": C_AMBER_DIM},
            {"range": [range_max * 0.65, range_max], "color": C_RED_DIM},
        ],
        bar_color=C_NEEDLE,
        number_format=".0f",
    )


def build_mass_available_gauge(
    mass_available_kg: float,
    range_max: float = 1000.0,
) -> go.Figure:
    """Mass Available for Components gauge — higher is better."""
    return _build_gauge(
        value=max(mass_available_kg, 0.0),
        title="AVAILABLE MASS",
        suffix=" kg",
        range_max=range_max,
        steps=[
            {"range": [0, range_max * 0.3], "color": C_RED_DIM},
            {"range": [range_max * 0.3, range_max * 0.6], "color": C_AMBER_DIM},
            {"range": [range_max * 0.6, range_max], "color": C_GREEN_DIM},
        ],
        bar_color=C_NEEDLE,
        number_format=".1f",
    )


def build_buoyancy_state_indicator(buoyancy_state: str) -> go.Figure:
    """
    Buoyancy state indicator — prominent color-coded status display.
    Fixed layout: title on top, state text below, no overlap.
    """
    color = STATE_COLORS.get(buoyancy_state, C_TEXT_DIM)
    short_label = buoyancy_state.replace(" Buoyancy", "").upper()

    fig = go.Figure(
        go.Indicator(
            mode="number",
            # We use the title for the heading and number for the state
            title={
                "text": "BUOYANCY STATE",
                "font": {"size": 11, "color": C_TEXT_DIM, "family": FONT_FAMILY},
            },
            number={
                "font": {"size": 30, "color": color, "family": FONT_FAMILY},
                # Suffix trick: display the state label as the number text
            },
            value=None,
        )
    )

    # Add the state text as an annotation (avoids title/number overlap)
    fig.update_layout(
        paper_bgcolor=TRANSPARENT,
        plot_bgcolor=TRANSPARENT,
        font={"color": C_TEXT, "family": FONT_FAMILY},
        margin=dict(l=20, r=20, t=40, b=20),
        height=210,
        annotations=[
            dict(
                text=f"<b>{short_label}</b>",
                x=0.5,
                y=0.4,
                xref="paper",
                yref="paper",
                showarrow=False,
                font=dict(size=32, color=color, family=FONT_FAMILY),
            ),
        ],
    )

    return fig