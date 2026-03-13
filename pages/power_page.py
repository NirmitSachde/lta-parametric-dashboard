"""
power_page.py
Onboard Power Consumption page for the LTA Parametric Dashboard.

Add to app.py:
    from pages.power_page import layout as power_layout, register_callbacks as power_callbacks
    power_callbacks(app)

Then wire the nav link to href="/power"
"""

import math
import dash
from dash import dcc, html, Input, Output, State, callback_context
import plotly.graph_objects as go

# ---------------------------------------------------------------------------
# Local import (adjust path as needed inside your project)
# ---------------------------------------------------------------------------
try:
    from engine.power_model import compute_power, GAS_PRESETS, BEARING_PRESETS
except ImportError:
    # fallback for standalone testing
    import sys, os
    sys.path.insert(0, os.path.dirname(__file__))
    from power_model import compute_power, GAS_PRESETS, BEARING_PRESETS

# ---------------------------------------------------------------------------
# Color palette (consistent with project)
# ---------------------------------------------------------------------------
CH_TEAL  = "#3D8B8B"
CH_CORAL = "#8B5A5A"
BG_DARK  = "#1a1a2e"
BG_MID   = "#16213e"
BG_CARD  = "#0f3460"
TEXT_PRI = "#e0e0e0"
TEXT_SEC = "#a0a0c0"
ACCENT   = "#00d4ff"
GREEN    = "#4CAF50"
AMBER    = "#FFC107"
RED_CLR  = "#F44336"

# ---------------------------------------------------------------------------
# Layout helpers
# ---------------------------------------------------------------------------
def _slider_block(label, id_, min_, max_, step, value, marks=None, tooltip=True):
    return html.Div([
        html.Label(label, style={"color": TEXT_SEC, "fontSize": "13px", "marginBottom": "4px"}),
        dcc.Slider(
            id=id_,
            min=min_, max=max_, step=step, value=value,
            marks=marks or {},
            tooltip={"placement": "bottom", "always_visible": tooltip},
            updatemode="drag",
        ),
    ], style={"marginBottom": "20px"})


def _kv_row(label, value_id, unit):
    return html.Div([
        html.Span(label, style={"color": TEXT_SEC, "fontSize": "13px", "flex": "1"}),
        html.Span(id=value_id, style={"color": ACCENT, "fontSize": "14px", "fontWeight": "600",
                                       "marginRight": "4px"}),
        html.Span(unit, style={"color": TEXT_SEC, "fontSize": "12px"}),
    ], style={"display": "flex", "alignItems": "center", "padding": "6px 0",
              "borderBottom": f"1px solid {BG_CARD}"})


# ---------------------------------------------------------------------------
# Page layout
# ---------------------------------------------------------------------------
layout = html.Div([
    # Header
    html.Div([
        html.H2("Onboard Power Consumption Model",
                style={"color": ACCENT, "margin": "0", "fontSize": "20px"}),
        html.P("Rotational gas-drag and bearing power for the spherical lifting structure",
               style={"color": TEXT_SEC, "margin": "4px 0 0 0", "fontSize": "13px"}),
    ], style={"padding": "20px 24px 12px", "borderBottom": f"1px solid {BG_CARD}"}),

    # Main body
    html.Div([
        # LEFT: inputs
        html.Div([
            html.H4("Design Inputs", style={"color": TEXT_PRI, "marginBottom": "16px",
                                             "fontSize": "15px"}),

            _slider_block("Sphere Radius R [m]", "pw-radius",
                          min_=1.0, max_=15.0, step=0.1, value=9.2,
                          marks={1: "1", 5: "5", 9.2: "9.2", 12: "12", 15: "15"}),

            _slider_block("Rotational Speed [rpm]", "pw-rpm",
                          min_=10, max_=1500, step=10, value=600,
                          marks={10: "10", 300: "300", 600: "600", 1000: "1000", 1500: "1500"}),

            _slider_block("Interior Gas Pressure [% Patm]", "pw-pfrac",
                          min_=0.1, max_=10.0, step=0.1, value=1.0,
                          marks={0.1: "0.1%", 1: "1%", 5: "5%", 10: "10%"}),

            html.Label("Gas Type", style={"color": TEXT_SEC, "fontSize": "13px"}),
            dcc.Dropdown(
                id="pw-gas",
                options=[{"label": g, "value": g} for g in GAS_PRESETS],
                value="Helium",
                clearable=False,
                style={"backgroundColor": BG_MID, "color": TEXT_PRI, "marginBottom": "20px",
                       "--Dash-background-color": BG_MID, "--Dash-color": TEXT_PRI},
            ),

            html.Label("Bearing Torque Preset", style={"color": TEXT_SEC, "fontSize": "13px"}),
            dcc.RadioItems(
                id="pw-tb-preset",
                options=[
                    {"label": f"Optimistic  (10 N.m)",    "value": "Optimistic"},
                    {"label": f"Baseline    (50 N.m)",    "value": "Baseline"},
                    {"label": f"Conservative (200 N.m)", "value": "Conservative"},
                ],
                value="Baseline",
                labelStyle={"display": "block", "color": TEXT_PRI, "fontSize": "13px",
                            "marginBottom": "6px"},
                style={"marginBottom": "20px"},
            ),

            html.Label("Custom Bearing Torque Tb [N.m]", style={"color": TEXT_SEC, "fontSize": "13px"}),
            dcc.Input(
                id="pw-tb-custom",
                type="number", min=0, max=5000, step=1, value=50,
                style={"backgroundColor": BG_MID, "color": TEXT_PRI, "border": f"1px solid {BG_CARD}",
                       "borderRadius": "4px", "padding": "6px 10px", "width": "100%",
                       "marginBottom": "8px", "fontSize": "13px"},
            ),
            html.Small("Overrides preset when changed manually",
                       style={"color": TEXT_SEC, "fontSize": "11px"}),

        ], style={"flex": "0 0 300px", "padding": "20px 24px",
                  "borderRight": f"1px solid {BG_CARD}"}),

        # MIDDLE: computed outputs + gauge
        html.Div([
            html.H4("Computed Outputs", style={"color": TEXT_PRI, "marginBottom": "8px",
                                                "fontSize": "15px"}),
            _kv_row("Angular velocity omega",     "pw-out-omega",    "rad/s"),
            _kv_row("Equatorial surface speed",   "pw-out-Veq",      "m/s"),
            _kv_row("Gas density (interior)",     "pw-out-rho",      "kg/m3"),
            _kv_row("Reynolds number Re",         "pw-out-Re",       ""),
            _kv_row("Friction coefficient Cf",    "pw-out-Cf",       ""),
            _kv_row("Gas-drag power P_drag",      "pw-out-Pdrag",    "kW"),
            _kv_row("Bearing power P_bearings",   "pw-out-Pbear",    "kW"),
            _kv_row("TOTAL onboard power P_total","pw-out-Ptotal",   "MW"),

            # Total power gauge
            html.Div([
                dcc.Graph(id="pw-gauge-total", config={"displayModeBar": False},
                          style={"height": "220px"}),
            ], style={"marginTop": "12px"}),

        ], style={"flex": "1", "padding": "20px 24px",
                  "borderRight": f"1px solid {BG_CARD}"}),

        # RIGHT: breakdown chart + Re sweep
        html.Div([
            html.H4("Power Breakdown", style={"color": TEXT_PRI, "marginBottom": "8px",
                                               "fontSize": "15px"}),
            dcc.Graph(id="pw-bar-breakdown", config={"displayModeBar": False},
                      style={"height": "200px", "marginBottom": "12px"}),

            html.H4("RPM Sweep", style={"color": TEXT_PRI, "marginBottom": "8px",
                                         "fontSize": "15px"}),
            dcc.Graph(id="pw-sweep-chart", config={"displayModeBar": False},
                      style={"height": "220px"}),

        ], style={"flex": "1", "padding": "20px 24px"}),

    ], style={"display": "flex", "flexDirection": "row", "flex": "1", "overflow": "hidden"}),

], style={"display": "flex", "flexDirection": "column", "height": "100%",
          "backgroundColor": BG_DARK, "color": TEXT_PRI, "fontFamily": "Arial, sans-serif"})


# ---------------------------------------------------------------------------
# Callbacks
# ---------------------------------------------------------------------------
def register_callbacks(app):

    @app.callback(
        Output("pw-tb-custom", "value"),
        Input("pw-tb-preset", "value"),
    )
    def sync_tb_from_preset(preset):
        return BEARING_PRESETS[preset]

    @app.callback(
        [
            Output("pw-out-omega",   "children"),
            Output("pw-out-Veq",     "children"),
            Output("pw-out-rho",     "children"),
            Output("pw-out-Re",      "children"),
            Output("pw-out-Cf",      "children"),
            Output("pw-out-Pdrag",   "children"),
            Output("pw-out-Pbear",   "children"),
            Output("pw-out-Ptotal",  "children"),
            Output("pw-gauge-total",    "figure"),
            Output("pw-bar-breakdown",  "figure"),
            Output("pw-sweep-chart",    "figure"),
        ],
        [
            Input("pw-radius",    "value"),
            Input("pw-rpm",       "value"),
            Input("pw-pfrac",     "value"),
            Input("pw-gas",       "value"),
            Input("pw-tb-custom", "value"),
        ],
    )
    def update_power(R, rpm, pfrac, gas, Tb):
        R    = float(R or 9.2)
        rpm  = float(rpm or 600)
        pfrac = float(pfrac or 1.0) / 100.0   # convert % -> fraction
        gas  = gas or "Helium"
        Tb   = float(Tb or 50)

        props = GAS_PRESETS.get(gas, GAS_PRESETS["Helium"])
        res = compute_power(R, rpm, pfrac, props["rho_1atm"], props["mu"], Tb)

        # --- text outputs ---
        omega_str  = f"{res['omega']:.3f}"
        Veq_str    = f"{res['V_equator']:.2f}"
        rho_str    = f"{res['rho_gas']:.5f}"
        Re_str     = f"{res['Re']:.3e}"
        Cf_str     = f"{res['Cf']:.5f}"
        Pdrag_str  = f"{res['P_gas_drag']/1e3:.2f}"
        Pbear_str  = f"{res['P_bearings']/1e3:.2f}"
        Ptot_str   = f"{res['P_total']/1e6:.4f}"

        Ptot_MW   = res["P_total"] / 1e6
        Pdrag_MW  = res["P_gas_drag"] / 1e6
        Pbear_MW  = res["P_bearings"] / 1e6

        # colour based on total power
        if Ptot_MW < 0.3:
            g_color = GREEN
        elif Ptot_MW < 1.0:
            g_color = AMBER
        else:
            g_color = RED_CLR

        # --- gauge ---
        gauge_max = max(2.0, Ptot_MW * 1.5)
        gauge_fig = go.Figure(go.Indicator(
            mode="gauge+number+delta",
            value=Ptot_MW,
            number={"suffix": " MW", "font": {"color": TEXT_PRI, "size": 20}},
            delta={"reference": 0.52, "relative": False,
                   "suffix": " MW vs baseline",
                   "font": {"size": 11}},
            gauge={
                "axis": {"range": [0, gauge_max], "tickcolor": TEXT_SEC,
                         "tickfont": {"color": TEXT_SEC, "size": 10}},
                "bar": {"color": g_color, "thickness": 0.15},
                "bgcolor": BG_MID,
                "bordercolor": BG_CARD,
                "steps": [
                    {"range": [0,           gauge_max*0.3], "color": "#1a2e1a"},
                    {"range": [gauge_max*0.3, gauge_max*0.6], "color": "#2e2a1a"},
                    {"range": [gauge_max*0.6, gauge_max],    "color": "#2e1a1a"},
                ],
                "threshold": {"line": {"color": ACCENT, "width": 2},
                              "thickness": 0.75, "value": 0.52},
            },
            title={"text": "Total Onboard Power", "font": {"color": TEXT_SEC, "size": 13}},
        ))
        gauge_fig.update_layout(
            paper_bgcolor=BG_DARK, font_color=TEXT_PRI, height=220,
            margin=dict(l=20, r=20, t=30, b=10),
        )

        # --- bar breakdown ---
        bar_fig = go.Figure([
            go.Bar(name="Gas Drag", x=["Power Breakdown"], y=[Pdrag_MW],
                   marker_color=CH_TEAL, text=[f"{Pdrag_MW:.3f} MW"], textposition="auto"),
            go.Bar(name="Bearings", x=["Power Breakdown"], y=[Pbear_MW],
                   marker_color=CH_CORAL, text=[f"{Pbear_MW*1e3:.1f} kW"], textposition="auto"),
        ])
        bar_fig.update_layout(
            barmode="stack", paper_bgcolor=BG_DARK, plot_bgcolor=BG_MID,
            font_color=TEXT_PRI, height=200, margin=dict(l=20, r=10, t=10, b=30),
            yaxis_title="MW", legend=dict(orientation="h", y=1.1, font_size=11),
            xaxis=dict(showgrid=False), yaxis=dict(gridcolor=BG_CARD),
        )

        # --- RPM sweep (50 to 1500 rpm) ---
        rpms  = list(range(50, 1501, 25))
        pdrag_sweep, pbear_sweep, ptot_sweep = [], [], []
        for r_ in rpms:
            s = compute_power(R, r_, pfrac, props["rho_1atm"], props["mu"], Tb)
            pdrag_sweep.append(s["P_gas_drag"] / 1e6)
            pbear_sweep.append(s["P_bearings"] / 1e6)
            ptot_sweep.append(s["P_total"] / 1e6)

        sweep_fig = go.Figure([
            go.Scatter(x=rpms, y=pdrag_sweep, name="P_drag",
                       line=dict(color=CH_TEAL, width=2)),
            go.Scatter(x=rpms, y=pbear_sweep, name="P_bearings",
                       line=dict(color=CH_CORAL, width=1.5, dash="dot")),
            go.Scatter(x=rpms, y=ptot_sweep, name="P_total",
                       line=dict(color=ACCENT, width=2.5)),
            go.Scatter(x=[rpm], y=[Ptot_MW], mode="markers",
                       marker=dict(color=g_color, size=10, symbol="circle"),
                       name="Current", showlegend=True),
        ])
        sweep_fig.update_layout(
            paper_bgcolor=BG_DARK, plot_bgcolor=BG_MID, font_color=TEXT_PRI,
            height=220, margin=dict(l=40, r=10, t=10, b=40),
            xaxis=dict(title="RPM", gridcolor=BG_CARD),
            yaxis=dict(title="Power [MW]", gridcolor=BG_CARD),
            legend=dict(font_size=10, bgcolor="rgba(0,0,0,0)"),
        )

        return (omega_str, Veq_str, rho_str, Re_str, Cf_str,
                Pdrag_str, Pbear_str, Ptot_str,
                gauge_fig, bar_fig, sweep_fig)
