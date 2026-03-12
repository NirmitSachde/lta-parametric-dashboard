"""
Sensitivity Analysis Page
=========================
Interactive sensitivity analysis with tornado, contour, feasibility boundary,
and operating envelope visualizations.
"""

from dash import html, dcc
from visualization.gauges import C_TEXT, C_TEXT_DIM, C_CYAN, FONT_FAMILY

CARD_BG = "#111820"
CARD_BORDER = "#1E2A38"

DASH_VARS = {
    "--Dash-Fill-Inverse-Strong": "#141D26",
    "--Dash-Text-Primary": "#E2E8F0",
    "--Dash-Text-Strong": "#FFFFFF",
    "--Dash-Stroke-Strong": "rgba(255,255,255,0.25)",
    "--Dash-Fill-Interactive-Strong": "#5BA4B5",
    "--Dash-Fill-Weak": "rgba(255,255,255,0.06)",
    "--Dash-Fill-Primary-Hover": "rgba(255,255,255,0.10)",
    "--Dash-Shading-Strong": "rgba(0,0,0,0.6)",
}


def layout():
    return html.Div([
        html.H2("SENSITIVITY ANALYSIS", style={
            "color": C_TEXT, "fontSize": "16px", "fontWeight": "700",
            "letterSpacing": "3px", "marginBottom": "6px", "fontFamily": FONT_FAMILY,
        }),
        html.P(
            "Explore how design parameters affect system performance. "
            "Select chart type and variation range below.",
            style={"color": C_TEXT_DIM, "fontSize": "11px", "marginBottom": "16px",
                   "fontFamily": FONT_FAMILY},
        ),

        # Controls
        html.Div(style={"display": "flex", "gap": "20px", "marginBottom": "16px",
                         "flexWrap": "wrap", "alignItems": "center"}, children=[
            html.Div(style={"display": "flex", "gap": "8px", "alignItems": "center"},
                     children=[
                html.Span("VARIATION:", style={"color": C_TEXT_DIM, "fontSize": "11px",
                           "fontFamily": FONT_FAMILY, "fontWeight": "600"}),
                html.Div(style={"width": "160px", **DASH_VARS}, children=[
                    dcc.Dropdown(
                        id="sensitivity-variation-pct",
                        options=[
                            {"label": "\u00b110%", "value": 10},
                            {"label": "\u00b120%", "value": 20},
                            {"label": "\u00b130%", "value": 30},
                            {"label": "\u00b150%", "value": 50},
                        ],
                        value=20, clearable=False, searchable=False,
                    ),
                ]),
            ]),
            html.Div(style={"display": "flex", "gap": "8px", "alignItems": "center"},
                     children=[
                html.Span("MATERIAL:", style={"color": C_TEXT_DIM, "fontSize": "11px",
                           "fontFamily": FONT_FAMILY, "fontWeight": "600"}),
                html.Div(style={"width": "200px", **DASH_VARS}, children=[
                    dcc.Dropdown(
                        id="sensitivity-material-density",
                        options=[
                            {"label": "Mylar (1390)", "value": 1390},
                            {"label": "Default (1100)", "value": 1100},
                            {"label": "CFRP (1600)", "value": 1600},
                            {"label": "Kapton (1420)", "value": 1420},
                            {"label": "Aluminum 6061 (2700)", "value": 2700},
                            {"label": "Titanium (4430)", "value": 4430},
                        ],
                        value=1100, clearable=False, searchable=False,
                    ),
                ]),
            ]),
        ]),

        # Tornado chart
        html.Div(style={
            "backgroundColor": CARD_BG, "border": f"1px solid {CARD_BORDER}",
            "borderRadius": "6px", "padding": "14px", "marginBottom": "14px",
        }, children=[
            html.H3("PARAMETER SENSITIVITY (TORNADO)", style={
                "color": "#7EC8DB", "fontSize": "13px", "fontWeight": "700",
                "letterSpacing": "2px", "marginBottom": "10px", "fontFamily": FONT_FAMILY,
            }),
            dcc.Graph(id="tornado-chart", config={"displayModeBar": False}),
        ]),

        # Two-column: contour + boundary
        html.Div(style={"display": "flex", "gap": "14px", "flexWrap": "wrap"}, children=[
            html.Div(style={
                "flex": "1 1 400px", "backgroundColor": CARD_BG,
                "border": f"1px solid {CARD_BORDER}",
                "borderRadius": "6px", "padding": "14px",
            }, children=[
                html.H3("RADIUS vs THICKNESS TRADE-OFF", style={
                    "color": "#7EC8DB", "fontSize": "13px", "fontWeight": "700",
                    "letterSpacing": "2px", "marginBottom": "10px", "fontFamily": FONT_FAMILY,
                }),
                dcc.Graph(id="tradeoff-contour", config={"displayModeBar": False}),
            ]),
            html.Div(style={
                "flex": "1 1 400px", "backgroundColor": CARD_BG,
                "border": f"1px solid {CARD_BORDER}",
                "borderRadius": "6px", "padding": "14px",
            }, children=[
                html.H3("FEASIBILITY ENVELOPE", style={
                    "color": "#7EC8DB", "fontSize": "13px", "fontWeight": "700",
                    "letterSpacing": "2px", "marginBottom": "10px", "fontFamily": FONT_FAMILY,
                }),
                dcc.Graph(id="feasibility-boundary", config={"displayModeBar": False}),
            ]),
        ]),
    ])