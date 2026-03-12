"""
Parametric Design Dashboard - Multi-Page Application
=====================================================
LTA Vehicle with Rotational Spherical Lifting Structure

Pages:
    1. Dashboard - Interactive gauges and sliders
    2. Materials - Aerospace material comparison
    3. Sensitivity - Tornado chart, trade-off contours

Author: Nirmit Sachde, Northeastern University
Mentor: David W. Clark, P.E.
"""

import os
import dash
from dash import dcc, html, Input, Output, State, callback, ALL, ctx
import plotly.graph_objects as go
import numpy as np

from engine.buoyancy_calculator import (
    compute_buoyancy, BuoyancyResult, STANDARD_ATM_PRESSURE,
    convert_value, convert_input_to_si, UNIT_CONVERSIONS,
)
from engine.materials_db import (
    MATERIALS, MATERIAL_LOOKUP, MATERIAL_CATEGORIES, evaluate_material,
)
from engine.sensitivity import (
    compute_tornado, compute_tradeoff_grid, compute_feasibility_boundary,
)
from visualization.gauges import (
    build_lift_force_gauge, build_weight_force_gauge, build_net_force_gauge,
    build_brs_gauge, build_mass_available_gauge, build_buoyancy_state_indicator,
    STATE_COLORS, C_TEXT, C_TEXT_DIM, C_GREEN, C_AMBER, C_RED, C_CYAN, FONT_FAMILY,
    TRANSPARENT,
)
from pages import materials as materials_page
from pages import sensitivity as sensitivity_page
from visualization.sphere_animation import build_3d_scene

# ═══════════════════════════════════════════════════════════════════════════
# App Init — Bootstrap DARKLY for Render (Dash 2.18), --Dash-* vars for local (Dash 4.0)
# ═══════════════════════════════════════════════════════════════════════════

import dash_bootstrap_components as dbc

dbc_css = "https://cdn.jsdelivr.net/gh/AnnMarieW/dash-bootstrap-templates@V1.0.2/dbc.min.css"

app = dash.Dash(
    __name__,
    title="LTA Parametric Design Dashboard",
    update_title="Computing...",
    suppress_callback_exceptions=True,
    external_stylesheets=[dbc.themes.DARKLY, dbc_css],
    meta_tags=[{"name": "viewport", "content": "width=device-width, initial-scale=1.0"}],
)
server = app.server

# ═══════════════════════════════════════════════════════════════════════════
# Constants
# ═══════════════════════════════════════════════════════════════════════════
PAGE_BG = "#0B0F14"
CARD_BG = "#111820"
CARD_BORDER = "#1E2A38"
SECTION_BORDER = "#1A2535"
NAV_BG = "#0E1319"
NAV_ACTIVE = "#1A2535"

DEFAULTS = {
    "outer_radius": 5.1, "thickness": 0.0005,
    "material_density": 1100.0, "internal_pressure": 5066.25,
    "atm_pressure": 101325.0,
}

SLIDER_CONFIGS = [
    {"id": "slider-outer-radius", "label": "Outer Radius", "quantity_type": "length",
     "si_unit": "m", "imp_unit": "ft",
     "si": {"min": 1.0, "max": 20.0, "step": 0.1, "default": 5.1},
     "imp": {"min": 3.3, "max": 65.6, "step": 0.3, "default": 16.7},
     "tooltip": "Outer radius of the hollow sphere",
     "fmt": ".1f", "tooltip_transform": "fmtRadius"},
    {"id": "slider-thickness", "label": "Shell Thickness", "quantity_type": "length",
     "si_unit": "m", "imp_unit": "ft",
     "si": {"min": 0.0001, "max": 0.01, "step": 0.0001, "default": 0.0005},
     "imp": {"min": 0.0003, "max": 0.0328, "step": 0.0003, "default": 0.0016},
     "tooltip": "Wall thickness of sphere material",
     "fmt": ".4f", "tooltip_transform": "fmtThickness"},
    {"id": "slider-density", "label": "Material Density", "quantity_type": "density",
     "si_unit": "kg/m\u00b3", "imp_unit": "lb/ft\u00b3",
     "si": {"min": 100.0, "max": 8000.0, "step": 50.0, "default": 1100.0},
     "imp": {"min": 6.2, "max": 499.4, "step": 3.1, "default": 68.7},
     "tooltip": "Density of sphere shell material",
     "fmt": ".0f", "tooltip_transform": "fmtDensity"},
    {"id": "slider-internal-pressure", "label": "Internal Pressure", "quantity_type": "pressure",
     "si_unit": "Pa", "imp_unit": "psi",
     "si": {"min": 100.0, "max": 100000.0, "step": 100.0, "default": 5066.25},
     "imp": {"min": 0.015, "max": 14.5, "step": 0.015, "default": 0.735},
     "tooltip": "Reduced pressure inside the rotating sphere",
     "fmt": ".1f", "tooltip_transform": "fmtPressure"},
    {"id": "slider-atm-pressure", "label": "Atm. Pressure", "quantity_type": "pressure",
     "si_unit": "Pa", "imp_unit": "psi",
     "si": {"min": 80000.0, "max": 110000.0, "step": 100.0, "default": 101325.0},
     "imp": {"min": 11.6, "max": 15.95, "step": 0.015, "default": 14.696},
     "tooltip": "External atmospheric pressure",
     "fmt": ".1f", "tooltip_transform": "fmtPressure"},
]
SLIDER_LOOKUP = {c["id"]: c for c in SLIDER_CONFIGS}


# ═══════════════════════════════════════════════════════════════════════════
# Reusable Components
# ═══════════════════════════════════════════════════════════════════════════

def section_header(text):
    return html.H3(text, style={
        "fontSize": "13px", "color": "#7EC8DB", "letterSpacing": "2px",
        "margin": "0 0 10px 0", "paddingBottom": "6px",
        "borderBottom": f"1px solid {SECTION_BORDER}",
        "fontFamily": FONT_FAMILY, "fontWeight": "700", "textTransform": "uppercase",
    })


def make_slider_row(config):
    sid = config["id"]
    return html.Div(style={
        "backgroundColor": CARD_BG, "border": f"1px solid {CARD_BORDER}",
        "borderRadius": "6px", "padding": "10px 14px", "marginBottom": "8px",
        "--Dash-Fill-Inverse-Strong": "#141D26",
        "--Dash-Text-Primary": "#E2E8F0",
        "--Dash-Text-Strong": "#FFFFFF",
        "--Dash-Text-Weak": "rgba(255,255,255,0.4)",
        "--Dash-Stroke-Strong": "rgba(255,255,255,0.25)",
        "--Dash-Stroke-Weak": "rgba(255,255,255,0.12)",
        "--Dash-Fill-Interactive-Strong": "#5BA4B5",
        "--Dash-Fill-Weak": "rgba(255,255,255,0.06)",
        "--Dash-Fill-Primary-Hover": "rgba(255,255,255,0.10)",
        "--Dash-Shading-Strong": "rgba(0,0,0,0.6)",
    }, children=[
        html.Div(style={"display": "flex", "justifyContent": "space-between",
                         "alignItems": "center", "marginBottom": "6px"}, children=[
            html.Div(style={"display": "flex", "alignItems": "baseline", "gap": "8px"}, children=[
                html.Span(config["label"], style={
                    "color": "#E2E8F0", "fontSize": "13px", "fontFamily": FONT_FAMILY,
                    "fontWeight": "700", "textTransform": "uppercase", "letterSpacing": "0.5px",
                }, title=config["tooltip"]),
                html.Span(id=f"{sid}-unit", style={
                    "color": "#7EC8DB", "fontSize": "12px", "fontFamily": FONT_FAMILY,
                    "fontWeight": "600", "backgroundColor": "#1A2535",
                    "padding": "1px 6px", "borderRadius": "3px", "border": "1px solid #263040",
                }),
            ]),
            html.Div(style={
                "backgroundColor": "#0B0F14", "border": "1px solid #1E2A38",
                "borderRadius": "4px", "padding": "2px 10px", "minWidth": "90px",
                "textAlign": "right",
            }, children=[
                html.Span(id=f"{sid}-value", style={
                    "color": "#FFFFFF", "fontSize": "14px",
                    "fontFamily": FONT_FAMILY, "fontWeight": "700",
                }),
            ]),
        ]),
        dcc.Slider(id=sid, min=config["si"]["min"], max=config["si"]["max"],
                   step=config["si"]["step"], value=config["si"]["default"],
                   marks=None,
                   tooltip={"placement": "bottom", "always_visible": False},
                   updatemode="mouseup"),
    ])


def readout_row(label, value, color="#FFFFFF"):
    return html.Div(style={
        "display": "flex", "justifyContent": "space-between",
        "alignItems": "center", "padding": "5px 0",
        "borderBottom": f"1px solid {CARD_BORDER}",
    }, children=[
        html.Span(label, style={"color": "#A0AEC0", "fontSize": "11px",
                   "fontFamily": FONT_FAMILY, "fontWeight": "600",
                   "textTransform": "uppercase", "letterSpacing": "0.3px"}),
        html.Span(value, style={"color": color, "fontSize": "13px",
                   "fontFamily": FONT_FAMILY, "fontWeight": "700"}),
    ])


def gauge_card(graph_id):
    return html.Div(style={
        "flex": "1 1 140px", "minWidth": "140px",
        "backgroundColor": CARD_BG, "border": f"1px solid {CARD_BORDER}",
        "borderRadius": "6px", "padding": "8px",
    }, children=[dcc.Graph(id=graph_id, config={"displayModeBar": False})])


# ═══════════════════════════════════════════════════════════════════════════
# Dashboard Page Layout
# ═══════════════════════════════════════════════════════════════════════════

def dashboard_layout():
    return html.Div([
        # Unit toggle
        html.Div(style={
            "display": "flex", "justifyContent": "flex-end", "alignItems": "center",
            "gap": "10px", "marginBottom": "14px", "flexWrap": "wrap",
        }, children=[
            html.Span("UNIT SYSTEM", style={
                "color": "#A0AEC0", "fontSize": "11px", "fontFamily": FONT_FAMILY,
                "fontWeight": "600", "letterSpacing": "1px",
            }),
            html.Div(style={
                "width": "240px", "minWidth": "200px",
                "--Dash-Fill-Inverse-Strong": "#141D26",
                "--Dash-Text-Primary": "#E2E8F0",
                "--Dash-Text-Strong": "#FFFFFF",
                "--Dash-Text-Weak": "rgba(255,255,255,0.4)",
                "--Dash-Stroke-Strong": "rgba(255,255,255,0.25)",
                "--Dash-Stroke-Weak": "rgba(255,255,255,0.12)",
                "--Dash-Fill-Interactive-Strong": "#5BA4B5",
                "--Dash-Fill-Weak": "rgba(255,255,255,0.06)",
                "--Dash-Fill-Primary-Hover": "rgba(255,255,255,0.10)",
                "--Dash-Shading-Strong": "rgba(0,0,0,0.6)",
            }, children=[
                dcc.Dropdown(id="unit-system-toggle", options=[
                    {"label": "SI  (m, kg, N, Pa)", "value": "SI"},
                    {"label": "Imperial  (ft, lb, lbf, psi)", "value": "Imperial"},
                ], value="SI", clearable=False, searchable=False),
            ]),
        ]),

        # Main grid: Left = Sliders + Computed, Right = Gauges + 3D
        html.Div(style={"display": "flex", "gap": "16px", "flexWrap": "wrap"}, children=[
            # LEFT: Sliders + Computed
            html.Div(style={"flex": "1 1 320px", "minWidth": "0"}, children=[
                section_header("Input Parameters"),
                *[make_slider_row(c) for c in SLIDER_CONFIGS],
                html.Div(style={"marginTop": "14px"}),
                section_header("Computed Values"),
                html.Div(id="computed-values-panel", style={
                    "backgroundColor": CARD_BG, "border": f"1px solid {CARD_BORDER}",
                    "borderRadius": "6px", "padding": "12px 14px",
                }),
            ]),
            # RIGHT: Gauges + 3D stacked
            html.Div(style={"flex": "2 1 400px", "minWidth": "0"}, children=[
                section_header("Instrument Panel"),
                dcc.Loading(type="circle", color="#5BA4B5", children=[
                    html.Div(style={"display": "flex", "gap": "10px", "marginBottom": "10px",
                                     "flexWrap": "wrap"}, children=[
                        gauge_card("gauge-lift"), gauge_card("gauge-weight"), gauge_card("gauge-net"),
                    ]),
                    html.Div(style={"display": "flex", "gap": "10px", "flexWrap": "wrap"}, children=[
                        gauge_card("gauge-brs"), gauge_card("gauge-mass-available"),
                        gauge_card("gauge-buoyancy-state"),
                    ]),
                ]),

                # 3D ConOps Visualization (inside right column, below gauges)
                html.Div(style={"marginTop": "12px"}, children=[
                    html.Div(style={"display": "flex", "justifyContent": "space-between",
                                     "alignItems": "center", "marginBottom": "8px"}, children=[
                        section_header("3D ConOps Visualization"),
                        html.Div(style={
                            "display": "flex", "gap": "8px", "alignItems": "center",
                            "--Dash-Fill-Inverse-Strong": "#141D26",
                            "--Dash-Text-Primary": "#E2E8F0",
                            "--Dash-Text-Strong": "#FFFFFF",
                            "--Dash-Stroke-Strong": "rgba(255,255,255,0.25)",
                            "--Dash-Fill-Interactive-Strong": "#5BA4B5",
                            "--Dash-Fill-Weak": "rgba(255,255,255,0.06)",
                            "--Dash-Fill-Primary-Hover": "rgba(255,255,255,0.10)",
                            "--Dash-Shading-Strong": "rgba(0,0,0,0.6)",
                        }, children=[
                            html.Span("MESH:", style={"color": C_TEXT_DIM, "fontSize": "10px",
                                       "fontFamily": FONT_FAMILY, "fontWeight": "600"}),
                            dcc.Dropdown(
                                id="mesh-quality-toggle",
                                options=[
                                    {"label": "Full Detail (slower)", "value": "full"},
                                    {"label": "Performance (faster)", "value": "light"},
                                ],
                                value="light", clearable=False, searchable=False,
                                style={"width": "180px", "fontSize": "11px"},
                            ),
                        ]),
                    ]),
                    dcc.Loading(type="dot", color="#5BA4B5", children=[
                        html.Div(style={
                            "backgroundColor": CARD_BG, "border": f"1px solid {CARD_BORDER}",
                            "borderRadius": "6px", "padding": "8px",
                        }, children=[
                            dcc.Graph(id="conops-3d-view", config={
                                "displayModeBar": True,
                                "modeBarButtonsToRemove": ["toImage", "sendDataToCloud"],
                                "displaylogo": False,
                            }),
                        ]),
                    ]),
                    html.P(
                        "VCA Body Shell with magnetic induction landing plate. "
                        "Shell position responds to buoyancy state. Design gap: 0.40m. "
                        "Click legend items to toggle Landing Plate and Magnetic Coil.",
                        style={"color": C_TEXT_DIM, "fontSize": "10px", "fontFamily": FONT_FAMILY,
                               "marginTop": "6px", "textAlign": "center"},
                    ),
                ]),
            ]),
        ]),
    ])


# ═══════════════════════════════════════════════════════════════════════════
# Navbar
# ═══════════════════════════════════════════════════════════════════════════

def make_nav_btn(label, page_id):
    return html.Button(label, id={"type": "nav-btn", "page": page_id}, n_clicks=0, style={
        "backgroundColor": "transparent", "color": C_TEXT_DIM,
        "border": "none", "padding": "10px 18px", "cursor": "pointer",
        "fontSize": "12px", "fontFamily": FONT_FAMILY, "fontWeight": "600",
        "letterSpacing": "1.5px", "textTransform": "uppercase",
        "borderBottom": "2px solid transparent", "transition": "all 0.2s",
    })


# ═══════════════════════════════════════════════════════════════════════════
# Main Layout
# ═══════════════════════════════════════════════════════════════════════════

app.layout = html.Div(style={
    "backgroundColor": PAGE_BG, "color": C_TEXT, "fontFamily": FONT_FAMILY,
    "minHeight": "100vh", "padding": "0",
}, className="dbc", children=[
    # Shared state store (for cross-page data like material selection)
    dcc.Store(id="shared-density-store", data=None),
    dcc.Store(id="current-page-store", data="dashboard"),

    # Header + Nav
    html.Div(style={
        "backgroundColor": NAV_BG, "borderBottom": f"1px solid {SECTION_BORDER}",
        "padding": "12px 16px 0 16px",
    }, children=[
        html.H1("PARAMETRIC DESIGN DASHBOARD", style={
            "fontSize": "16px", "fontWeight": "600", "letterSpacing": "4px",
            "margin": "0 0 4px 0", "color": C_TEXT, "fontFamily": FONT_FAMILY,
        }),
        html.P("LTA Vehicle  \u00b7  Rotational Spherical Lifting Structure", style={
            "fontSize": "10px", "color": C_TEXT_DIM, "margin": "0 0 10px 0",
            "letterSpacing": "1.5px",
        }),
        # Navigation tabs
        html.Div(style={"display": "flex", "gap": "4px", "flexWrap": "wrap"}, children=[
            make_nav_btn("Dashboard", "dashboard"),
            make_nav_btn("Materials", "materials"),
            make_nav_btn("Sensitivity", "sensitivity"),
        ]),
    ]),

    # Page content with loading spinner
    dcc.Loading(
        id="page-loading",
        type="dot",
        color="#5BA4B5",
        fullscreen=False,
        style={"minHeight": "400px"},
        children=[
            html.Div(id="page-content", style={"padding": "16px"}),
        ],
    ),

    # Footer
    html.Div(style={
        "textAlign": "center", "padding": "12px 0", "marginTop": "16px",
        "borderTop": f"1px solid {SECTION_BORDER}", "color": "#4A5568",
        "fontSize": "10px", "fontFamily": FONT_FAMILY,
    }, children=[
        html.Span("Nirmit Sachde  \u00b7  Northeastern University  \u00b7  Mentor: David W. Clark, P.E."),
    ]),
])


# ═══════════════════════════════════════════════════════════════════════════
# NAVIGATION CALLBACK
# ═══════════════════════════════════════════════════════════════════════════

@callback(
    Output("page-content", "children"),
    Output("current-page-store", "data"),
    Output({"type": "nav-btn", "page": ALL}, "style"),
    Input({"type": "nav-btn", "page": ALL}, "n_clicks"),
    State("current-page-store", "data"),
    prevent_initial_call=False,
)
def navigate(n_clicks_list, current_page):
    triggered = ctx.triggered_id
    if triggered and isinstance(triggered, dict):
        page = triggered["page"]
    else:
        page = current_page or "dashboard"

    # Build styles: active page gets highlighted, others stay dim
    page_ids = ["dashboard", "materials", "sensitivity"]
    styles = []
    for pid in page_ids:
        if pid == page:
            styles.append({
                "backgroundColor": "#1A2535", "color": "#7EC8DB",
                "border": "none", "padding": "10px 18px", "cursor": "pointer",
                "fontSize": "12px", "fontFamily": FONT_FAMILY, "fontWeight": "700",
                "letterSpacing": "1.5px", "textTransform": "uppercase",
                "borderBottom": "2px solid #5BA4B5", "borderRadius": "4px 4px 0 0",
                "transition": "all 0.2s",
            })
        else:
            styles.append({
                "backgroundColor": "transparent", "color": C_TEXT_DIM,
                "border": "none", "padding": "10px 18px", "cursor": "pointer",
                "fontSize": "12px", "fontFamily": FONT_FAMILY, "fontWeight": "600",
                "letterSpacing": "1.5px", "textTransform": "uppercase",
                "borderBottom": "2px solid transparent",
                "transition": "all 0.2s",
            })

    if page == "materials":
        return materials_page.layout(), page, styles
    elif page == "sensitivity":
        return sensitivity_page.layout(), page, styles
    else:
        return dashboard_layout(), page, styles


# ═══════════════════════════════════════════════════════════════════════════
# DASHBOARD CALLBACKS
# ═══════════════════════════════════════════════════════════════════════════

# Slider value displays (formatted per parameter)
for cfg in SLIDER_CONFIGS:
    @callback(Output(f"{cfg['id']}-value", "children"), Input(cfg['id'], "value"))
    def _sv(value, _fmt=cfg.get("fmt", ".2f")):
        if value is None: return ""
        return f"{value:{_fmt}}"

# Slider unit labels
for cfg in SLIDER_CONFIGS:
    @callback(Output(f"{cfg['id']}-unit", "children"), Input("unit-system-toggle", "value"))
    def _su(us, si_u=cfg["si_unit"], imp_u=cfg["imp_unit"]):
        return imp_u if us == "Imperial" else si_u

# Slider range conversion on unit toggle
for cfg in SLIDER_CONFIGS:
    @callback(
        Output(cfg["id"], "value"), Output(cfg["id"], "min"),
        Output(cfg["id"], "max"), Output(cfg["id"], "step"),
        Input("unit-system-toggle", "value"), Input(cfg["id"], "value"),
        prevent_initial_call=True,
    )
    def _sr(unit_system, current_value, _cfg=cfg):
        sys_key = "imp" if unit_system == "Imperial" else "si"
        new_min, new_max, new_step = _cfg[sys_key]["min"], _cfg[sys_key]["max"], _cfg[sys_key]["step"]
        if ctx.triggered_id == "unit-system-toggle":
            factor = UNIT_CONVERSIONS[_cfg["quantity_type"]]["Imperial"]["factor"]
            new_value = current_value * factor if unit_system == "Imperial" else current_value / factor
            new_value = max(new_min, min(new_max, new_value))
        else:
            new_value = current_value
        return new_value, new_min, new_max, new_step

# Master dashboard computation
@callback(
    Output("gauge-lift", "figure"), Output("gauge-weight", "figure"),
    Output("gauge-net", "figure"), Output("gauge-brs", "figure"),
    Output("gauge-mass-available", "figure"), Output("gauge-buoyancy-state", "figure"),
    Output("computed-values-panel", "children"),
    Output("conops-3d-view", "figure"),
    Input("slider-outer-radius", "value"), Input("slider-thickness", "value"),
    Input("slider-density", "value"), Input("slider-internal-pressure", "value"),
    Input("slider-atm-pressure", "value"), Input("unit-system-toggle", "value"),
    Input("mesh-quality-toggle", "value"),
)
def update_dashboard(outer_radius, thickness, density, internal_pressure, atm_pressure, unit_system, mesh_quality):
    us = unit_system or "SI"
    if us == "Imperial":
        outer_radius = convert_input_to_si(outer_radius, "length", "Imperial")
        thickness = convert_input_to_si(thickness, "length", "Imperial")
        density = convert_input_to_si(density, "density", "Imperial")
        internal_pressure = convert_input_to_si(internal_pressure, "pressure", "Imperial")
        atm_pressure = convert_input_to_si(atm_pressure, "pressure", "Imperial")
    if internal_pressure >= atm_pressure: internal_pressure = atm_pressure - 100.0
    if thickness >= outer_radius: thickness = outer_radius * 0.01

    try:
        result = compute_buoyancy(outer_radius, thickness, density, internal_pressure, atm_pressure)
    except (ValueError, ZeroDivisionError) as e:
        empty = go.Figure()
        empty.update_layout(paper_bgcolor=TRANSPARENT, plot_bgcolor=TRANSPARENT, height=210)
        err = html.Div(f"Error: {e}", style={"color": C_RED, "fontSize": "11px"})
        return empty, empty, empty, empty, empty, empty, err, empty

    # Convert for display
    lift_val, fu = convert_value(result.lift_force_N, "force", us)
    weight_val, _ = convert_value(result.weight_force_N, "force", us)
    net_val, _ = convert_value(result.net_force_N, "force", us)
    mass_val, mu = convert_value(result.mass_available_kg, "mass", us)

    force_max = max(abs(lift_val), abs(weight_val), 10.0) * 1.5
    brs_max = max(result.balanced_rotational_speed_rpm, 500.0) * 1.5
    mass_max = max(abs(mass_val), 10.0) * 1.5

    gl = build_lift_force_gauge(lift_val, force_max)
    gw = build_weight_force_gauge(weight_val, force_max)
    gn = build_net_force_gauge(net_val, force_max)
    gb = build_brs_gauge(result.balanced_rotational_speed_rpm, brs_max)
    gm = build_mass_available_gauge(mass_val, mass_max)
    gs = build_buoyancy_state_indicator(result.buoyancy_state)
    for fig, suf in [(gl, f" {fu}"), (gw, f" {fu}"), (gn, f" {fu}"), (gm, f" {mu}")]:
        fig.data[0].number.suffix = suf

    sc = STATE_COLORS.get(result.buoyancy_state, C_TEXT)
    ri, lu = convert_value(result.geometry.inner_radius_m, "length", us)
    ra, au = convert_value(result.geometry.surface_area_m2, "area", us)
    rv, vu = convert_value(result.geometry.interior_void_volume_m3, "volume", us)
    rsv, _ = convert_value(result.geometry.shell_volume_m3, "volume", us)
    rm, mmu = convert_value(result.sphere_mass_kg, "mass", us)
    rd, _ = convert_value(result.displaced_air_mass_kg, "mass", us)
    rav, _ = convert_value(result.mass_available_kg, "mass", us)

    panel = html.Div([
        readout_row("Inner Radius", f"{ri:.4f} {lu}"),
        readout_row("Surface Area", f"{ra:.2f} {au}"),
        readout_row("Interior Volume", f"{rv:.2f} {vu}"),
        readout_row("Shell Volume", f"{rsv:.6f} {vu}"),
        readout_row("Sphere Mass", f"{rm:.3f} {mmu}"),
        readout_row("Displaced Air Mass", f"{rd:.3f} {mmu}"),
        readout_row("Mass Available", f"{rav:.3f} {mmu}", color=sc),
        readout_row("BRS (rad/s)", f"{result.balanced_rotational_speed_rad_s:.2f}"),
        readout_row("BRS (RPM)", f"{result.balanced_rotational_speed_rpm:.0f}"),
        html.Div(style={"display": "flex", "justifyContent": "space-between",
                         "padding": "8px 0 2px 0"}, children=[
            html.Span("BUOYANCY", style={"color": "#A0AEC0", "fontSize": "11px",
                       "fontFamily": FONT_FAMILY, "fontWeight": "600"}),
            html.Span(result.buoyancy_state.upper(), style={
                "color": sc, "fontSize": "13px", "fontWeight": "700",
                "fontFamily": FONT_FAMILY, "letterSpacing": "1px"}),
        ]),
    ])
    # Build 3D ConOps visualization
    quality = mesh_quality or "full"
    fig_3d = build_3d_scene(result.buoyancy_state, result.net_force_N, quality=quality)

    return gl, gw, gn, gb, gm, gs, panel, fig_3d


# ═══════════════════════════════════════════════════════════════════════════
# MATERIALS PAGE CALLBACKS
# ═══════════════════════════════════════════════════════════════════════════

# Muted chart colors for dark background
CH_TEAL = "#3D8B8B"
CH_CORAL = "#8B5A5A"
CH_SAND = "#8B7D5A"
CH_BLUE = "#4A7A9B"
CH_PURPLE = "#7A6A9B"

@callback(
    Output("materials-table-container", "children"),
    Output("material-feasibility-chart", "figure"),
    Input("material-category-filter", "value"),
    Input("material-chart-selector", "value"),
)
def update_materials_page(category, chart_type):
    r, t, p_int, p_atm = 5.1, 0.0005, 5066.25, 101325.0

    mats = MATERIALS if category == "all" else [m for m in MATERIALS if m.category == category]
    evals = [evaluate_material(m, r, t, p_int, p_atm) for m in mats]

    # Build table
    header = html.Thead(html.Tr([
        html.Th(h, style={"padding": "10px 6px", "color": "#7EC8DB", "fontSize": "10px",
                 "fontWeight": "700", "textTransform": "uppercase", "letterSpacing": "0.5px",
                 "borderBottom": f"2px solid {CARD_BORDER}", "textAlign": a,
                 "fontFamily": FONT_FAMILY})
        for h, a in [("Material", "left"), ("Type", "left"), ("Density", "right"),
                      ("Avail Mass", "right"), ("BRS RPM", "right"),
                      ("Stress MPa", "right"), ("Safety", "right"),
                      ("Status", "center"), ("", "center")]
    ]))

    rows = [materials_page.make_material_row(e["material"], e) for e in evals]
    table = html.Table([header, html.Tbody(rows)], style={
        "width": "100%", "borderCollapse": "collapse", "fontFamily": FONT_FAMILY,
    })

    # Build selected chart
    fig = go.Figure()
    names = [e["material"].name for e in evals]
    masses = [e["mass_available_kg"] for e in evals]

    if chart_type == "bubble":
        # Density vs Available Mass bubble chart (size = safety factor)
        densities = [e["material"].density_kg_m3 for e in evals]
        safety_factors = [min(e["safety_factor"], 50) for e in evals]
        feasible = [e["feasible_overall"] for e in evals]
        colors = [CH_TEAL if f else CH_CORAL for f in feasible]

        fig.add_trace(go.Scatter(
            x=densities, y=masses, mode="markers+text",
            marker=dict(
                size=[max(s * 2, 8) for s in safety_factors],
                color=colors, opacity=0.7,
                line=dict(width=1, color="rgba(255,255,255,0.2)"),
            ),
            text=names, textposition="top center",
            textfont=dict(size=8, color=C_TEXT_DIM),
            hovertemplate="<b>%{text}</b><br>Density: %{x:.0f} kg/m³<br>"
                          "Available Mass: %{y:.1f} kg<extra></extra>",
        ))
        fig.add_hline(y=0, line_dash="dot", line_color=CH_SAND, line_width=1,
                      annotation_text="Buoyancy threshold",
                      annotation_font=dict(size=9, color=CH_SAND))
        fig.update_layout(
            xaxis=dict(title="Material Density (kg/m³)", gridcolor="#1A2535"),
            yaxis=dict(title="Available Mass (kg)", gridcolor="#1A2535"),
            height=420,
        )

    elif chart_type == "radar":
        # Radar chart comparing top feasible materials
        feasible_evals = [e for e in evals if e["feasible_overall"]]
        if len(feasible_evals) == 0:
            feasible_evals = evals[:5]  # fallback

        radar_colors = [CH_TEAL, CH_BLUE, CH_PURPLE, CH_SAND, "#6B8B8B", "#8B6B8B"]
        categories = ["Available Mass", "Safety Factor", "Low Density", "Low BRS", "Low Stress"]

        for idx, e in enumerate(feasible_evals[:6]):
            # Normalize each dimension to 0-100 scale
            mass_norm = max(0, min(100, (e["mass_available_kg"] / 500) * 100))
            sf_norm = max(0, min(100, (min(e["safety_factor"], 20) / 20) * 100))
            density_norm = max(0, min(100, (1 - e["material"].density_kg_m3 / 8000) * 100))
            brs_norm = max(0, min(100, (1 - min(e["brs_rpm"], 5000) / 5000) * 100))
            stress_norm = max(0, min(100, (1 - min(e["total_stress_MPa"], 500) / 500) * 100))

            vals = [mass_norm, sf_norm, density_norm, brs_norm, stress_norm]
            vals.append(vals[0])  # close the polygon
            cats = categories + [categories[0]]

            fig.add_trace(go.Scatterpolar(
                r=vals, theta=cats, fill="toself",
                fillcolor=f"rgba{tuple(list(int(radar_colors[idx][i:i+2], 16) for i in (1,3,5)) + [0.1])}",
                line=dict(color=radar_colors[idx], width=2),
                name=e["material"].name,
            ))

        fig.update_layout(
            polar=dict(
                bgcolor="#0B0F14",
                radialaxis=dict(visible=True, range=[0, 100], gridcolor="#1A2535",
                                tickfont=dict(size=8, color=C_TEXT_DIM)),
                angularaxis=dict(gridcolor="#1A2535",
                                 tickfont=dict(size=10, color=C_TEXT)),
            ),
            height=450,
            legend=dict(font=dict(size=10, color=C_TEXT_DIM)),
        )

    else:
        # Default: Available mass bar chart with muted colors
        colors = [CH_TEAL if m > 0 else CH_CORAL for m in masses]
        fig.add_trace(go.Bar(
            x=names, y=masses, marker_color=colors,
            text=[f"{m:.0f}" for m in masses], textposition="outside",
            textfont={"size": 10, "color": C_TEXT_DIM},
            marker=dict(line=dict(width=0)),
        ))
        fig.add_hline(y=0, line_dash="dot", line_color=CH_SAND, line_width=1)
        fig.update_layout(
            xaxis={"tickangle": -45, "gridcolor": "#1A2535", "tickfont": {"size": 9}},
            yaxis={"title": "Available Mass (kg)", "gridcolor": "#1A2535"},
            height=400,
        )

    # Common layout for all chart types
    fig.update_layout(
        paper_bgcolor=TRANSPARENT, plot_bgcolor=TRANSPARENT,
        font={"color": C_TEXT, "family": FONT_FAMILY, "size": 11},
        margin=dict(l=60, r=20, t=20, b=100),
        showlegend=(chart_type == "radar"),
    )

    return table, fig


# ═══════════════════════════════════════════════════════════════════════════
# SENSITIVITY PAGE CALLBACKS
# ═══════════════════════════════════════════════════════════════════════════

@callback(
    Output("tornado-chart", "figure"),
    Output("tradeoff-contour", "figure"),
    Output("feasibility-boundary", "figure"),
    Input("current-page-store", "data"),
    Input("sensitivity-variation-pct", "value"),
    Input("sensitivity-material-density", "value"),
)
def update_sensitivity_page(current_page, variation_pct, mat_density):
    if current_page != "sensitivity":
        empty = go.Figure()
        empty.update_layout(paper_bgcolor=TRANSPARENT, plot_bgcolor=TRANSPARENT, height=100)
        return empty, empty, empty

    var_pct = variation_pct or 20
    density = mat_density or 1100.0

    base = {
        "outer_radius_m": 5.1, "thickness_m": 0.0005,
        "material_density_kg_m3": density, "internal_pressure_Pa": 5066.25,
        "atmospheric_pressure_Pa": 101325.0,
    }

    # --- Tornado (muted colors) ---
    tornado_data, base_mass = compute_tornado(base, variation_pct=var_pct)
    fig_tornado = go.Figure()
    params = [d["parameter"] for d in tornado_data]
    deltas_low = [d["delta_low"] for d in tornado_data]
    deltas_high = [d["delta_high"] for d in tornado_data]

    fig_tornado.add_trace(go.Bar(
        y=params, x=deltas_low, orientation="h", name=f"-{var_pct}%",
        marker_color=CH_CORAL, text=[f"{d:.1f}" for d in deltas_low],
        textposition="outside", textfont={"size": 10, "color": C_TEXT_DIM},
    ))
    fig_tornado.add_trace(go.Bar(
        y=params, x=deltas_high, orientation="h", name=f"+{var_pct}%",
        marker_color=CH_TEAL, text=[f"{d:.1f}" for d in deltas_high],
        textposition="outside", textfont={"size": 10, "color": C_TEXT_DIM},
    ))
    fig_tornado.update_layout(
        barmode="overlay", paper_bgcolor=TRANSPARENT, plot_bgcolor=TRANSPARENT,
        font={"color": C_TEXT, "family": FONT_FAMILY, "size": 11},
        xaxis={"title": f"Change in Available Mass (kg) @ \u00b1{var_pct}%",
               "gridcolor": "#1A2535", "zeroline": True, "zerolinecolor": "#4A5568"},
        yaxis={"gridcolor": "#1A2535"},
        margin=dict(l=150, r=80, t=20, b=40), height=300,
        legend={"font": {"size": 10}, "orientation": "h", "y": -0.15},
    )

    # --- Trade-off contour (muted colorscale) ---
    radii, thicknesses, mass_grid = compute_tradeoff_grid(
        density, 5066.25, 101325.0, r_steps=50, t_steps=50)

    fig_contour = go.Figure(go.Contour(
        x=radii, y=thicknesses * 1000, z=mass_grid,
        colorscale=[[0, CH_CORAL], [0.35, CH_SAND], [0.5, "#3A4A5A"], [0.75, CH_BLUE], [1, CH_TEAL]],
        contours_showlabels=True,
        contours=dict(labelfont=dict(size=9, color=C_TEXT)),
        colorbar=dict(title=dict(text="Mass (kg)", font=dict(size=10, color=C_TEXT_DIM)),
                      tickfont=dict(size=9, color=C_TEXT_DIM)),
    ))
    fig_contour.update_layout(
        paper_bgcolor=TRANSPARENT, plot_bgcolor=TRANSPARENT,
        font={"color": C_TEXT, "family": FONT_FAMILY, "size": 11},
        xaxis={"title": "Outer Radius (m)", "gridcolor": "#1A2535"},
        yaxis={"title": "Thickness (mm)", "gridcolor": "#1A2535"},
        margin=dict(l=60, r=20, t=20, b=50), height=400,
    )

    # --- Feasibility boundary (muted) ---
    radii_b, max_t = compute_feasibility_boundary(density, 5066.25, 101325.0)
    fig_boundary = go.Figure()
    fig_boundary.add_trace(go.Scatter(
        x=radii_b, y=max_t * 1000, mode="lines", fill="tozeroy",
        line={"color": CH_TEAL, "width": 2},
        fillcolor=CH_TEAL.replace(")", ",0.1)").replace("rgb", "rgba") if "rgb" in CH_TEAL
               else "rgba(61,139,139,0.12)",
        name="Feasible Region",
    ))
    fig_boundary.add_trace(go.Scatter(
        x=radii_b, y=max_t * 1000 * 1.5, mode="lines",
        line={"color": CH_CORAL, "width": 1, "dash": "dot"},
        fill="tonexty",
        fillcolor="rgba(139,90,90,0.08)",
        name="Infeasible Region",
    ))
    fig_boundary.update_layout(
        paper_bgcolor=TRANSPARENT, plot_bgcolor=TRANSPARENT,
        font={"color": C_TEXT, "family": FONT_FAMILY, "size": 11},
        xaxis={"title": "Outer Radius (m)", "gridcolor": "#1A2535"},
        yaxis={"title": "Max Thickness (mm)", "gridcolor": "#1A2535"},
        margin=dict(l=60, r=20, t=20, b=50), height=380,
        showlegend=True, legend={"font": {"size": 10}},
    )
    fig_boundary.add_annotation(
        x=10, y=max_t[len(max_t)//2]*1000*0.4,
        text="POSITIVE<br>BUOYANCY", showarrow=False,
        font={"size": 12, "color": CH_TEAL}, opacity=0.5,
    )

    return fig_tornado, fig_contour, fig_boundary


# ═══════════════════════════════════════════════════════════════════════════
# MATERIAL "USE" BUTTON -> Store density + navigate to dashboard
# ═══════════════════════════════════════════════════════════════════════════

@callback(
    Output("shared-density-store", "data"),
    Output("page-content", "children", allow_duplicate=True),
    Output("current-page-store", "data", allow_duplicate=True),
    Output({"type": "nav-btn", "page": ALL}, "style", allow_duplicate=True),
    Input({"type": "use-material-btn", "index": ALL}, "n_clicks"),
    prevent_initial_call=True,
)
def on_use_material(n_clicks_list):
    if not ctx.triggered_id or not any(n for n in n_clicks_list if n):
        return dash.no_update, dash.no_update, dash.no_update, [dash.no_update] * 3
    mat_name = ctx.triggered_id["index"]
    mat = MATERIAL_LOOKUP.get(mat_name)
    if mat:
        # Build nav styles with dashboard highlighted
        page_ids = ["dashboard", "materials", "sensitivity"]
        styles = []
        for pid in page_ids:
            if pid == "dashboard":
                styles.append({
                    "backgroundColor": "#1A2535", "color": "#7EC8DB",
                    "border": "none", "padding": "10px 18px", "cursor": "pointer",
                    "fontSize": "12px", "fontFamily": FONT_FAMILY, "fontWeight": "700",
                    "letterSpacing": "1.5px", "textTransform": "uppercase",
                    "borderBottom": "2px solid #5BA4B5", "borderRadius": "4px 4px 0 0",
                    "transition": "all 0.2s",
                })
            else:
                styles.append({
                    "backgroundColor": "transparent", "color": C_TEXT_DIM,
                    "border": "none", "padding": "10px 18px", "cursor": "pointer",
                    "fontSize": "12px", "fontFamily": FONT_FAMILY, "fontWeight": "600",
                    "letterSpacing": "1.5px", "textTransform": "uppercase",
                    "borderBottom": "2px solid transparent",
                    "transition": "all 0.2s",
                })
        return mat.density_kg_m3, dashboard_layout(), "dashboard", styles
    return dash.no_update, dash.no_update, dash.no_update, [dash.no_update] * 3


# ═══════════════════════════════════════════════════════════════════════════
# When dashboard loads, check if shared-density-store has a value and apply it
# ═══════════════════════════════════════════════════════════════════════════

@callback(
    Output("slider-density", "value", allow_duplicate=True),
    Input("shared-density-store", "data"),
    Input("unit-system-toggle", "value"),
    prevent_initial_call=True,
)
def apply_shared_density(density_si, unit_system):
    if density_si is None:
        return dash.no_update
    us = unit_system or "SI"
    if us == "Imperial":
        val, _ = convert_value(density_si, "density", "Imperial")
        return val
    return density_si


# ═══════════════════════════════════════════════════════════════════════════
# Run
# ═══════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8050))
    debug = os.environ.get("RENDER") is None
    app.run(debug=debug, host="0.0.0.0", port=port)