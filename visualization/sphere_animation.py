"""
VCA Body Shell 3D Visualization
================================
Renders the VCA body shell STL with magnetic induction landing plate.
Animation: vertical Z-axis movement based on buoyancy state.

Landing system per David Clark's specifications:
    - Magnetic induction landing plate (no physical contact)
    - Design gap: 0.40m between bottom of shell and top of plate
    - Plate diameter: 130% of body shell diameter
    - ConOps visualization: hover, ascend, descend

Optimization: mesh loaded lazily on first callback and cached in memory.
Uses vca_shell_mesh_light.json by default (Render-safe), falls back to
vca_shell_mesh.json if light not found, falls back to parametric sphere
if neither exists.
"""

import json
import os
import numpy as np
import plotly.graph_objects as go
from visualization.gauges import (
    C_TEXT, C_TEXT_DIM, C_GREEN, C_AMBER, C_RED, C_CYAN, FONT_FAMILY, TRANSPARENT,
)

# ── Shell geometry constants (from STL analysis) ──────────────────────────────
SHELL_DIAMETER = 350.65
SHELL_HEIGHT   = 90.12
SHELL_BOTTOM_Z = -10.0
SHELL_TOP_Z    = 80.12

# Landing plate specs (David Clark)
PLATE_DIAMETER = SHELL_DIAMETER * 1.30
PLATE_THICKNESS = 3.0
DESIGN_GAP = 0.40 * 350.65 / 9.0
PLATE_Z = SHELL_BOTTOM_Z - DESIGN_GAP

# Animation Z offsets
Z_OFFSET_POSITIVE = 60.0
Z_OFFSET_NEUTRAL  = 0.0
Z_OFFSET_NEGATIVE = -15.0

# ── Lazy mesh cache ───────────────────────────────────────────────────────────
_mesh_cache = {}


def _data_dir():
    return os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")


def load_shell_mesh(quality="light"):
    """Load VCA shell mesh from JSON, cached after first load."""
    global _mesh_cache

    if quality in _mesh_cache:
        return _mesh_cache[quality]

    data_dir = _data_dir()

    # Preference order: requested quality -> other quality -> None
    candidates = {
        "light": [
            os.path.join(data_dir, "vca_shell_mesh_light.json"),
            os.path.join(data_dir, "vca_shell_mesh.json"),
        ],
        "full": [
            os.path.join(data_dir, "vca_shell_mesh.json"),
            os.path.join(data_dir, "vca_shell_mesh_light.json"),
        ],
    }

    for path in candidates.get(quality, candidates["light"]):
        if os.path.exists(path):
            try:
                with open(path, "r") as f:
                    mesh = json.load(f)
                _mesh_cache[quality] = mesh
                return mesh
            except (json.JSONDecodeError, OSError):
                continue

    _mesh_cache[quality] = None
    return None


# ── Landing plate ─────────────────────────────────────────────────────────────
def create_landing_plate(z_position, diameter, resolution=60):
    radius = diameter / 2.0
    angles = np.linspace(0, 2 * np.pi, resolution, endpoint=False)
    cx, cy = 0.0, 0.0
    x_vals = [cx] + [cx + radius * np.cos(a) for a in angles]
    y_vals = [cy] + [cy + radius * np.sin(a) for a in angles]
    z_vals = [z_position] * (resolution + 1)
    i_vals, j_vals, k_vals = [], [], []
    for idx in range(resolution):
        i_vals.append(0)
        j_vals.append(idx + 1)
        k_vals.append((idx + 1) % resolution + 1)
    return {"x": x_vals, "y": y_vals, "z": z_vals,
            "i": i_vals, "j": j_vals, "k": k_vals}


# ── Magnetic ring ─────────────────────────────────────────────────────────────
def create_magnetic_ring(z_position, inner_r, outer_r, resolution=60):
    angles = np.linspace(0, 2 * np.pi, resolution, endpoint=False)
    x_vals, y_vals, z_vals = [], [], []
    i_vals, j_vals, k_vals = [], [], []
    for a in angles:
        x_vals.append(inner_r * np.cos(a))
        y_vals.append(inner_r * np.sin(a))
        z_vals.append(z_position)
    for a in angles:
        x_vals.append(outer_r * np.cos(a))
        y_vals.append(outer_r * np.sin(a))
        z_vals.append(z_position)
    n = resolution
    for idx in range(n):
        next_idx = (idx + 1) % n
        i_vals.extend([idx, idx, n + idx])
        j_vals.extend([next_idx, n + idx, n + next_idx])
        k_vals.extend([n + idx, n + next_idx, next_idx])
    return {"x": x_vals, "y": y_vals, "z": z_vals,
            "i": i_vals, "j": j_vals, "k": k_vals}


# ── Main scene builder ────────────────────────────────────────────────────────
def build_3d_scene(buoyancy_state, net_force_N=0.0, quality="light"):
    """
    Build the complete 3D ConOps visualization.

    Parameters
    ----------
    buoyancy_state : str
        "Positive Buoyancy", "Neutral Buoyancy", or "Negative Buoyancy"
    net_force_N : float
        Net vertical force for proportional animation offset.
    quality : str
        "light" (default, Render-safe) or "full" (local only)
    """
    mesh = load_shell_mesh(quality)

    # Z offset based on buoyancy state
    if buoyancy_state == "Positive Buoyancy":
        z_offset = min(Z_OFFSET_POSITIVE, max(10.0, abs(net_force_N) / 100.0))
    elif buoyancy_state == "Negative Buoyancy":
        z_offset = Z_OFFSET_NEGATIVE
    else:
        z_offset = Z_OFFSET_NEUTRAL

    # Shell color matches buoyancy state
    state_colors = {
        "Positive Buoyancy": C_GREEN,
        "Neutral Buoyancy":  C_AMBER,
        "Negative Buoyancy": C_RED,
    }
    shell_color = state_colors.get(buoyancy_state, C_TEXT_DIM)

    fig = go.Figure()

    # ── VCA Body Shell ────────────────────────────────────────────────────────
    if mesh:
        z_shifted = [z + z_offset for z in mesh["z"]]
        fig.add_trace(go.Mesh3d(
            x=mesh["x"], y=mesh["y"], z=z_shifted,
            i=mesh["i"], j=mesh["j"], k=mesh["k"],
            color=shell_color,
            opacity=0.85,
            flatshading=True,
            lighting=dict(
                ambient=0.4, diffuse=0.6, specular=0.3,
                roughness=0.5, fresnel=0.2,
            ),
            lightposition=dict(x=200, y=200, z=300),
            name="VCA Body Shell",
            showlegend=True,
            hoverinfo="name",
        ))
    else:
        # Parametric sphere fallback
        u = np.linspace(0, 2 * np.pi, 30)
        v = np.linspace(0, np.pi, 20)
        r = SHELL_DIAMETER / 2
        x = r * np.outer(np.cos(u), np.sin(v)).flatten()
        y = r * np.outer(np.sin(u), np.sin(v)).flatten()
        z = (r * np.outer(np.ones(np.size(u)), np.cos(v)).flatten()
             + SHELL_TOP_Z / 2 + z_offset)
        fig.add_trace(go.Scatter3d(
            x=x, y=y, z=z, mode="markers",
            marker=dict(size=1, color=shell_color, opacity=0.5),
            name="VCA Shell (simplified)",
        ))

    # ── Landing Plate (legend-toggleable) ─────────────────────────────────────
    plate = create_landing_plate(PLATE_Z, PLATE_DIAMETER)
    fig.add_trace(go.Mesh3d(
        x=plate["x"], y=plate["y"], z=plate["z"],
        i=plate["i"], j=plate["j"], k=plate["k"],
        color="#4A7A9B",
        opacity=0.6,
        flatshading=True,
        name="Landing Plate",
        showlegend=True,
        visible="legendonly",
        hoverinfo="name",
    ))

    # ── Magnetic Coil (legend-toggleable) ─────────────────────────────────────
    coil_inner = PLATE_DIAMETER * 0.15
    coil_outer = PLATE_DIAMETER * 0.25
    coil = create_magnetic_ring(PLATE_Z + PLATE_THICKNESS, coil_inner, coil_outer)
    fig.add_trace(go.Mesh3d(
        x=coil["x"], y=coil["y"], z=coil["z"],
        i=coil["i"], j=coil["j"], k=coil["k"],
        color="#FFC107",
        opacity=0.8,
        flatshading=True,
        name="Magnetic Coil",
        showlegend=True,
        visible="legendonly",
        hoverinfo="name",
    ))

    # ── Layout ────────────────────────────────────────────────────────────────
    axis_style = dict(
        showbackground=False,
        showgrid=False,
        zeroline=False,
        showticklabels=False,
        title="",
    )

    z_range_min = PLATE_Z - 20
    z_range_max = SHELL_TOP_Z + Z_OFFSET_POSITIVE + 20

    fig.update_layout(
        scene=dict(
            xaxis=dict(**axis_style),
            yaxis=dict(**axis_style),
            zaxis=dict(**axis_style, range=[z_range_min, z_range_max]),
            bgcolor=TRANSPARENT,
            aspectmode="data",
            camera=dict(
                eye=dict(x=1.5, y=1.5, z=0.8),
                up=dict(x=0, y=0, z=1),
            ),
        ),
        uirevision="constant",
        paper_bgcolor=TRANSPARENT,
        plot_bgcolor=TRANSPARENT,
        margin=dict(l=0, r=0, t=30, b=0),
        height=450,
        showlegend=True,
        legend=dict(
            font=dict(size=10, color=C_TEXT_DIM),
            bgcolor="rgba(0,0,0,0)",
            x=0.01, y=0.99,
        ),
        annotations=[
            dict(
                text=f"<b>{buoyancy_state.upper()}</b>",
                x=0.5, y=0.97, xref="paper", yref="paper",
                showarrow=False,
                font=dict(size=14, color=shell_color, family=FONT_FAMILY),
            ),
        ],
        font=dict(color=C_TEXT, family=FONT_FAMILY),
    )

    return fig