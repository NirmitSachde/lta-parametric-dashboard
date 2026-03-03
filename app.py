"""
Parametric Design Dashboard — Main Application
===============================================
Feasibility Assessment of LTA Vehicle with Rotational Spherical Lifting Structure

Entry point for the Dash web application.

Run (development):  python app.py
Run (production):   gunicorn app:server --bind 0.0.0.0:8050
Access:             http://127.0.0.1:8050

UI Design Philosophy:
    - Dark background per flight test display standards (reduces eye strain)
    - Muted alert colors per FAA CFR 14 Part 25.1322 (red/amber/green)
    - Monospace typography for engineering precision readability
    - Minimal visual noise — data first, decoration last

Author: Nirmit Sachde, Northeastern University
Mentor: David W. Clark, P.E.
"""

import dash
from dash import dcc, html, Input, Output, callback
import plotly.graph_objects as go

from engine.buoyancy_calculator import (
    compute_buoyancy,
    BuoyancyResult,
    STANDARD_ATM_PRESSURE,
    RHO_AIR_SEA_LEVEL,
    convert_value,
    convert_input_to_si,
    UNIT_CONVERSIONS,
)
from visualization.gauges import (
    build_lift_force_gauge,
    build_weight_force_gauge,
    build_net_force_gauge,
    build_brs_gauge,
    build_mass_available_gauge,
    build_buoyancy_state_indicator,
    STATE_COLORS,
    C_TEXT,
    C_TEXT_DIM,
    C_CYAN,
    C_GREEN,
    C_AMBER,
    C_RED,
    FONT_FAMILY,
)

# ---------------------------------------------------------------------------
# App Initialization
# ---------------------------------------------------------------------------
app = dash.Dash(
    __name__,
    title="LTA Parametric Design Dashboard",
    update_title="Computing...",
)
server = app.server  # Expose for gunicorn

# ---------------------------------------------------------------------------
# Default Input Values (from Excel baseline)
# ---------------------------------------------------------------------------
DEFAULTS = {
    "outer_radius": 5.1,
    "thickness": 0.0005,
    "material_density": 1100.0,
    "internal_pressure": 5066.25,
    "atm_pressure": 101325.0,
}

# ---------------------------------------------------------------------------
# Slider Configurations
# ---------------------------------------------------------------------------
SLIDER_CONFIGS = [
    {
        "id": "slider-outer-radius",
        "label": "Outer Radius",
        "quantity_type": "length",
        "si_unit": "m",
        "imp_unit": "ft",
        "si": {"min": 1.0, "max": 20.0, "step": 0.1, "default": 5.1},
        "imp": {"min": 3.3, "max": 65.6, "step": 0.3, "default": 16.7},
        "tooltip": "Outer radius of the hollow sphere",
    },
    {
        "id": "slider-thickness",
        "label": "Shell Thickness",
        "quantity_type": "length",
        "si_unit": "m",
        "imp_unit": "ft",
        "si": {"min": 0.0001, "max": 0.01, "step": 0.0001, "default": 0.0005},
        "imp": {"min": 0.0003, "max": 0.0328, "step": 0.0003, "default": 0.0016},
        "tooltip": "Wall thickness of sphere material",
    },
    {
        "id": "slider-density",
        "label": "Material Density",
        "quantity_type": "density",
        "si_unit": "kg/m³",
        "imp_unit": "lb/ft³",
        "si": {"min": 100.0, "max": 8000.0, "step": 50.0, "default": 1100.0},
        "imp": {"min": 6.2, "max": 499.4, "step": 3.1, "default": 68.7},
        "tooltip": "Density of sphere shell material",
    },
    {
        "id": "slider-internal-pressure",
        "label": "Internal Pressure",
        "quantity_type": "pressure",
        "si_unit": "Pa",
        "imp_unit": "psi",
        "si": {"min": 100.0, "max": 100000.0, "step": 100.0, "default": 5066.25},
        "imp": {"min": 0.015, "max": 14.5, "step": 0.015, "default": 0.735},
        "tooltip": "Reduced pressure inside the rotating sphere",
    },
    {
        "id": "slider-atm-pressure",
        "label": "Atmospheric Pressure",
        "quantity_type": "pressure",
        "si_unit": "Pa",
        "imp_unit": "psi",
        "si": {"min": 80000.0, "max": 110000.0, "step": 100.0, "default": 101325.0},
        "imp": {"min": 11.6, "max": 15.95, "step": 0.015, "default": 14.696},
        "tooltip": "External atmospheric pressure",
    },
]

# Build a lookup dict for quick access in callbacks
SLIDER_LOOKUP = {cfg["id"]: cfg for cfg in SLIDER_CONFIGS}

# ---------------------------------------------------------------------------
# Color Palette (page-level)
# ---------------------------------------------------------------------------
PAGE_BG = "#0B0F14"          # Near-black with blue undertone
CARD_BG = "#111820"          # Card surface — slightly lighter
CARD_BORDER = "#1E2A38"      # Subtle border — low contrast
SECTION_BORDER = "#1A2535"   # Section dividers
INPUT_BG = "#0E1319"         # Input area background (slightly darker)
ACCENT = "#3B82A0"           # Muted teal-blue — section headers
SLIDER_COLOR = "#2A6F8A"     # Slider track color


# ---------------------------------------------------------------------------
# Helper: Build a slider row
# ---------------------------------------------------------------------------
def make_slider_row(config: dict) -> html.Div:
    """Build a labeled slider with live value readout and dynamic unit label."""
    slider_id = config["id"]
    value_display_id = f"{slider_id}-value"
    unit_display_id = f"{slider_id}-unit"

    return html.Div(
        style={
            "backgroundColor": CARD_BG,
            "border": f"1px solid {CARD_BORDER}",
            "borderRadius": "6px",
            "padding": "10px 14px",
            "marginBottom": "8px",
        },
        children=[
            # Row 1: Label + unit badge + current value
            html.Div(
                style={
                    "display": "flex",
                    "justifyContent": "space-between",
                    "alignItems": "center",
                    "marginBottom": "6px",
                },
                children=[
                    # Left: label + unit
                    html.Div(
                        style={"display": "flex", "alignItems": "baseline", "gap": "8px"},
                        children=[
                            html.Span(
                                config["label"],
                                style={
                                    "color": "#E2E8F0",
                                    "fontSize": "13px",
                                    "fontFamily": FONT_FAMILY,
                                    "fontWeight": "700",
                                    "textTransform": "uppercase",
                                    "letterSpacing": "0.5px",
                                },
                                title=config["tooltip"],
                            ),
                            html.Span(
                                id=unit_display_id,
                                style={
                                    "color": "#7EC8DB",
                                    "fontSize": "12px",
                                    "fontFamily": FONT_FAMILY,
                                    "fontWeight": "600",
                                    "backgroundColor": "#1A2535",
                                    "padding": "1px 6px",
                                    "borderRadius": "3px",
                                    "border": "1px solid #263040",
                                },
                            ),
                        ],
                    ),
                    # Right: current value
                    html.Span(
                        id=value_display_id,
                        style={
                            "color": "#FFFFFF",
                            "fontSize": "14px",
                            "fontFamily": FONT_FAMILY,
                            "fontWeight": "700",
                        },
                    ),
                ],
            ),
            # Slider
            dcc.Slider(
                id=slider_id,
                min=config["si"]["min"],
                max=config["si"]["max"],
                step=config["si"]["step"],
                value=config["si"]["default"],
                marks=None,
                tooltip={"placement": "bottom", "always_visible": False},
                updatemode="drag",
            ),
        ],
    )


# ---------------------------------------------------------------------------
# Helper: Computed value row
# ---------------------------------------------------------------------------
def readout_row(label: str, value: str, color: str = "#FFFFFF") -> html.Div:
    """Single row in the computed values panel."""
    return html.Div(
        style={
            "display": "flex",
            "justifyContent": "space-between",
            "alignItems": "center",
            "padding": "5px 0",
            "borderBottom": f"1px solid {CARD_BORDER}",
        },
        children=[
            html.Span(
                label,
                style={
                    "color": "#A0AEC0",
                    "fontSize": "11px",
                    "fontFamily": FONT_FAMILY,
                    "fontWeight": "600",
                    "textTransform": "uppercase",
                    "letterSpacing": "0.3px",
                },
            ),
            html.Span(
                value,
                style={
                    "color": color,
                    "fontSize": "13px",
                    "fontFamily": FONT_FAMILY,
                    "fontWeight": "700",
                },
            ),
        ],
    )


# ---------------------------------------------------------------------------
# Section header component
# ---------------------------------------------------------------------------
def section_header(text: str) -> html.Div:
    return html.Div(
        style={"marginBottom": "10px"},
        children=[
            html.H3(
                text,
                style={
                    "fontSize": "13px",
                    "color": "#7EC8DB",
                    "letterSpacing": "2px",
                    "margin": "0",
                    "paddingBottom": "6px",
                    "borderBottom": f"1px solid {SECTION_BORDER}",
                    "fontFamily": FONT_FAMILY,
                    "fontWeight": "700",
                    "textTransform": "uppercase",
                },
            ),
        ],
    )


# ---------------------------------------------------------------------------
# Layout
# ---------------------------------------------------------------------------
app.layout = html.Div(
    style={
        "backgroundColor": PAGE_BG,
        "color": C_TEXT,
        "fontFamily": FONT_FAMILY,
        "minHeight": "100vh",
        "padding": "16px 20px",
    },
    children=[
        # --- CSS overrides injected via hidden markdown ---
        html.Div(
            id="_css-overrides",
            children=[],
            style={"display": "none"},
        ),

        # ===== HEADER =====
        html.Div(
            style={
                "textAlign": "center",
                "padding": "14px 0 12px 0",
                "borderBottom": f"1px solid {SECTION_BORDER}",
                "marginBottom": "16px",
            },
            children=[
                html.H1(
                    "PARAMETRIC DESIGN DASHBOARD",
                    style={
                        "fontSize": "18px",
                        "fontWeight": "600",
                        "letterSpacing": "4px",
                        "margin": "0",
                        "color": C_TEXT,
                        "fontFamily": FONT_FAMILY,
                    },
                ),
                html.P(
                    "Lighter Than Air Vehicle  ·  Rotational Spherical Lifting Structure",
                    style={
                        "fontSize": "10px",
                        "color": C_TEXT_DIM,
                        "margin": "6px 0 0 0",
                        "letterSpacing": "1.5px",
                        "fontFamily": FONT_FAMILY,
                    },
                ),
            ],
        ),

        # ===== UNIT SYSTEM TOGGLE =====
        html.Div(
            style={
                "display": "flex",
                "justifyContent": "flex-end",
                "alignItems": "center",
                "gap": "10px",
                "marginBottom": "14px",
                "padding": "0 4px",
            },
            children=[
                html.Span(
                    "UNIT SYSTEM",
                    style={
                        "color": "#A0AEC0",
                        "fontSize": "11px",
                        "fontFamily": FONT_FAMILY,
                        "fontWeight": "600",
                        "letterSpacing": "1px",
                        "textTransform": "uppercase",
                    },
                ),
                dcc.Dropdown(
                    id="unit-system-toggle",
                    options=[
                        {"label": "SI  (m, kg, N, Pa)", "value": "SI"},
                        {"label": "Imperial  (ft, lb, lbf, psi)", "value": "Imperial"},
                    ],
                    value="SI",
                    clearable=False,
                    searchable=False,
                    style={
                        "width": "260px",
                        "backgroundColor": CARD_BG,
                        "fontFamily": FONT_FAMILY,
                        "fontSize": "12px",
                    },
                ),
            ],
        ),

        # ===== MAIN GRID =====
        html.Div(
            style={"display": "flex", "gap": "16px", "flexWrap": "wrap"},
            children=[
                # ----- LEFT: Input Sliders + Computed Values -----
                html.Div(
                    style={
                        "flex": "0 0 340px",
                        "minWidth": "300px",
                    },
                    children=[
                        section_header("Input Parameters"),
                        *[make_slider_row(cfg) for cfg in SLIDER_CONFIGS],

                        html.Div(style={"marginTop": "14px"}),
                        section_header("Computed Values"),
                        html.Div(
                            id="computed-values-panel",
                            style={
                                "backgroundColor": CARD_BG,
                                "border": f"1px solid {CARD_BORDER}",
                                "borderRadius": "6px",
                                "padding": "12px 14px",
                            },
                        ),
                    ],
                ),

                # ----- RIGHT: Instrument Panel (Gauges) -----
                html.Div(
                    style={"flex": "1", "minWidth": "480px"},
                    children=[
                        section_header("Instrument Panel"),

                        # Row 1: Lift, Weight, Net Force
                        html.Div(
                            style={"display": "flex", "gap": "10px", "marginBottom": "10px", "flexWrap": "wrap"},
                            children=[
                                html.Div(
                                    style={
                                        "flex": "1",
                                        "minWidth": "180px",
                                        "backgroundColor": CARD_BG,
                                        "border": f"1px solid {CARD_BORDER}",
                                        "borderRadius": "6px",
                                        "padding": "8px",
                                    },
                                    children=[dcc.Graph(id="gauge-lift", config={"displayModeBar": False})],
                                ),
                                html.Div(
                                    style={
                                        "flex": "1",
                                        "minWidth": "180px",
                                        "backgroundColor": CARD_BG,
                                        "border": f"1px solid {CARD_BORDER}",
                                        "borderRadius": "6px",
                                        "padding": "8px",
                                    },
                                    children=[dcc.Graph(id="gauge-weight", config={"displayModeBar": False})],
                                ),
                                html.Div(
                                    style={
                                        "flex": "1",
                                        "minWidth": "180px",
                                        "backgroundColor": CARD_BG,
                                        "border": f"1px solid {CARD_BORDER}",
                                        "borderRadius": "6px",
                                        "padding": "8px",
                                    },
                                    children=[dcc.Graph(id="gauge-net", config={"displayModeBar": False})],
                                ),
                            ],
                        ),

                        # Row 2: BRS, Mass Available, Buoyancy State
                        html.Div(
                            style={"display": "flex", "gap": "10px", "flexWrap": "wrap"},
                            children=[
                                html.Div(
                                    style={
                                        "flex": "1",
                                        "minWidth": "180px",
                                        "backgroundColor": CARD_BG,
                                        "border": f"1px solid {CARD_BORDER}",
                                        "borderRadius": "6px",
                                        "padding": "8px",
                                    },
                                    children=[dcc.Graph(id="gauge-brs", config={"displayModeBar": False})],
                                ),
                                html.Div(
                                    style={
                                        "flex": "1",
                                        "minWidth": "180px",
                                        "backgroundColor": CARD_BG,
                                        "border": f"1px solid {CARD_BORDER}",
                                        "borderRadius": "6px",
                                        "padding": "8px",
                                    },
                                    children=[dcc.Graph(id="gauge-mass-available", config={"displayModeBar": False})],
                                ),
                                html.Div(
                                    style={
                                        "flex": "1",
                                        "minWidth": "180px",
                                        "backgroundColor": CARD_BG,
                                        "border": f"1px solid {CARD_BORDER}",
                                        "borderRadius": "6px",
                                        "padding": "8px",
                                    },
                                    children=[dcc.Graph(id="gauge-buoyancy-state", config={"displayModeBar": False})],
                                ),
                            ],
                        ),
                    ],
                ),
            ],
        ),

        # ===== FOOTER =====
        html.Div(
            style={
                "textAlign": "center",
                "padding": "12px 0",
                "marginTop": "16px",
                "borderTop": f"1px solid {SECTION_BORDER}",
                "color": "#4A5568",
                "fontSize": "10px",
                "fontFamily": FONT_FAMILY,
                "letterSpacing": "0.5px",
            },
            children=[
                html.Span("Nirmit Sachde  ·  Northeastern University  ·  Mentor: David W. Clark, P.E."),
            ],
        ),
    ],
)


# ---------------------------------------------------------------------------
# Callbacks: Slider value displays (number only)
# ---------------------------------------------------------------------------
for cfg in SLIDER_CONFIGS:
    @callback(
        Output(f"{cfg['id']}-value", "children"),
        Input(cfg['id'], "value"),
    )
    def update_slider_display(value):
        if value is None:
            return ""
        if abs(value) < 0.01:
            return f"{value:.4f}"
        elif abs(value) < 1:
            return f"{value:.3f}"
        elif abs(value) < 100:
            return f"{value:.1f}"
        else:
            return f"{value:,.0f}"


# ---------------------------------------------------------------------------
# Callbacks: Slider unit labels (update when unit system changes)
# ---------------------------------------------------------------------------
for cfg in SLIDER_CONFIGS:
    @callback(
        Output(f"{cfg['id']}-unit", "children"),
        Input("unit-system-toggle", "value"),
    )
    def update_unit_label(unit_system, si_u=cfg["si_unit"], imp_u=cfg["imp_unit"]):
        if unit_system == "Imperial":
            return imp_u
        return si_u


# ---------------------------------------------------------------------------
# Callbacks: Slider range + value conversion on unit system change
# When user toggles SI ↔ Imperial, convert current slider value and update
# min/max/step to match the new unit system.
# ---------------------------------------------------------------------------
for cfg in SLIDER_CONFIGS:
    @callback(
        Output(cfg["id"], "value"),
        Output(cfg["id"], "min"),
        Output(cfg["id"], "max"),
        Output(cfg["id"], "step"),
        Input("unit-system-toggle", "value"),
        Input(cfg["id"], "value"),
        prevent_initial_call=True,
    )
    def update_slider_range(
        unit_system,
        current_value,
        _cfg=cfg,
    ):
        from dash import ctx

        sys_key = "imp" if unit_system == "Imperial" else "si"
        new_min = _cfg[sys_key]["min"]
        new_max = _cfg[sys_key]["max"]
        new_step = _cfg[sys_key]["step"]

        # Only convert value when the UNIT TOGGLE triggered (not slider drag)
        if ctx.triggered_id == "unit-system-toggle":
            qt = _cfg["quantity_type"]
            factor = UNIT_CONVERSIONS[qt]["Imperial"]["factor"]
            if unit_system == "Imperial":
                new_value = current_value * factor
            else:
                new_value = current_value / factor
            # Clamp to new range
            new_value = max(new_min, min(new_max, new_value))
        else:
            new_value = current_value

        return new_value, new_min, new_max, new_step


# ---------------------------------------------------------------------------
# Callback: Master computation + gauge updates
# ---------------------------------------------------------------------------
@callback(
    Output("gauge-lift", "figure"),
    Output("gauge-weight", "figure"),
    Output("gauge-net", "figure"),
    Output("gauge-brs", "figure"),
    Output("gauge-mass-available", "figure"),
    Output("gauge-buoyancy-state", "figure"),
    Output("computed-values-panel", "children"),
    Input("slider-outer-radius", "value"),
    Input("slider-thickness", "value"),
    Input("slider-density", "value"),
    Input("slider-internal-pressure", "value"),
    Input("slider-atm-pressure", "value"),
    Input("unit-system-toggle", "value"),
)
def update_dashboard(
    outer_radius: float,
    thickness: float,
    density: float,
    internal_pressure: float,
    atm_pressure: float,
    unit_system: str,
):
    """
    Master callback: recompute buoyancy and update all gauges + readouts.
    Slider values are in the currently active unit system — convert to SI first.
    """
    us = unit_system or "SI"

    # --- Convert slider values to SI for computation ---
    if us == "Imperial":
        outer_radius = convert_input_to_si(outer_radius, "length", "Imperial")
        thickness = convert_input_to_si(thickness, "length", "Imperial")
        density = convert_input_to_si(density, "density", "Imperial")
        internal_pressure = convert_input_to_si(internal_pressure, "pressure", "Imperial")
        atm_pressure = convert_input_to_si(atm_pressure, "pressure", "Imperial")

    # --- Guard rails (in SI) ---
    if internal_pressure >= atm_pressure:
        internal_pressure = atm_pressure - 100.0
    if thickness >= outer_radius:
        thickness = outer_radius * 0.01

    # --- Compute (always in SI) ---
    try:
        result: BuoyancyResult = compute_buoyancy(
            outer_radius_m=outer_radius,
            thickness_m=thickness,
            material_density_kg_m3=density,
            internal_pressure_Pa=internal_pressure,
            atmospheric_pressure_Pa=atm_pressure,
        )
    except (ValueError, ZeroDivisionError) as e:
        empty = go.Figure()
        empty.update_layout(
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            height=210,
        )
        error_msg = html.Div(
            f"Computation error: {str(e)}",
            style={"color": C_RED, "fontSize": "11px", "fontFamily": FONT_FAMILY},
        )
        return empty, empty, empty, empty, empty, empty, error_msg

    # --- Convert display values to selected unit system ---
    lift_val, force_unit = convert_value(result.lift_force_N, "force", us)
    weight_val, _ = convert_value(result.weight_force_N, "force", us)
    net_val, _ = convert_value(result.net_force_N, "force", us)
    mass_avail_val, mass_unit = convert_value(result.mass_available_kg, "mass", us)
    brs_rpm = result.balanced_rotational_speed_rpm  # RPM is same in both

    # --- Dynamic gauge ranges ---
    force_max = max(abs(lift_val), abs(weight_val), 10.0) * 1.5
    brs_max = max(brs_rpm, 500.0) * 1.5
    mass_max = max(abs(mass_avail_val), 10.0) * 1.5

    # --- Build gauges with converted values and units ---
    gauge_lift = build_lift_force_gauge(lift_val, force_max)
    gauge_weight = build_weight_force_gauge(weight_val, force_max)
    gauge_net = build_net_force_gauge(net_val, force_max)
    gauge_brs = build_brs_gauge(brs_rpm, brs_max)
    gauge_mass = build_mass_available_gauge(mass_avail_val, mass_max)
    gauge_state = build_buoyancy_state_indicator(result.buoyancy_state)

    # Update gauge suffixes based on unit system
    for fig, suffix in [
        (gauge_lift, f" {force_unit}"),
        (gauge_weight, f" {force_unit}"),
        (gauge_net, f" {force_unit}"),
        (gauge_mass, f" {mass_unit}"),
    ]:
        fig.data[0].number.suffix = suffix

    # --- Build computed values panel with unit conversions ---
    state_color = STATE_COLORS.get(result.buoyancy_state, C_TEXT)

    r_inner, len_unit = convert_value(result.geometry.inner_radius_m, "length", us)
    r_area, area_unit = convert_value(result.geometry.surface_area_m2, "area", us)
    r_vol, vol_unit = convert_value(result.geometry.interior_void_volume_m3, "volume", us)
    r_shell_vol, _ = convert_value(result.geometry.shell_volume_m3, "volume", us)
    r_mass, mass_u = convert_value(result.sphere_mass_kg, "mass", us)
    r_disp, _ = convert_value(result.displaced_air_mass_kg, "mass", us)
    r_avail, _ = convert_value(result.mass_available_kg, "mass", us)

    computed_panel = html.Div([
        readout_row("Inner Radius", f"{r_inner:.4f} {len_unit}"),
        readout_row("Surface Area", f"{r_area:.2f} {area_unit}"),
        readout_row("Interior Volume", f"{r_vol:.2f} {vol_unit}"),
        readout_row("Shell Volume", f"{r_shell_vol:.6f} {vol_unit}"),
        readout_row("Sphere Mass", f"{r_mass:.3f} {mass_u}"),
        readout_row("Displaced Air Mass", f"{r_disp:.3f} {mass_u}"),
        readout_row("Mass Available", f"{r_avail:.3f} {mass_u}", color=state_color),
        readout_row("BRS (rad/s)", f"{result.balanced_rotational_speed_rad_s:.2f}"),
        readout_row("BRS (RPM)", f"{result.balanced_rotational_speed_rpm:.0f}"),
        # Buoyancy state — final row, emphasized
        html.Div(
            style={
                "display": "flex",
                "justifyContent": "space-between",
                "alignItems": "center",
                "padding": "8px 0 2px 0",
            },
            children=[
                html.Span(
                    "BUOYANCY",
                    style={
                        "color": "#A0AEC0",
                        "fontSize": "11px",
                        "fontFamily": FONT_FAMILY,
                        "fontWeight": "600",
                        "textTransform": "uppercase",
                        "letterSpacing": "1px",
                    },
                ),
                html.Span(
                    result.buoyancy_state.upper(),
                    style={
                        "color": state_color,
                        "fontSize": "13px",
                        "fontWeight": "700",
                        "fontFamily": FONT_FAMILY,
                        "letterSpacing": "1px",
                    },
                ),
            ],
        ),
    ])

    return gauge_lift, gauge_weight, gauge_net, gauge_brs, gauge_mass, gauge_state, computed_panel


# ---------------------------------------------------------------------------
# Run
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    import os
    port = int(os.environ.get("PORT", 8050))
    debug = os.environ.get("RENDER") is None  # Debug only when running locally
    app.run(debug=debug, host="0.0.0.0", port=port)