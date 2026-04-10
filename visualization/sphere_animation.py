"""
visualization/sphere_animation.py
==================================
Optimized 3D ConOps scene for the LTA dashboard.

Key optimizations for Render free tier:
  1. Lazy loading: mesh JSON is read from disk only on first callback, not at import
  2. Module-level cache: mesh loaded once, reused for all subsequent callbacks
  3. Graceful fallback: if mesh file missing, renders a clean parametric sphere
  4. Light mesh is default: vca_shell_mesh_light.json (463 KB) used unless full requested
  5. Full mesh excluded from Render deploy via .gitignore (too large for free tier RAM)
"""

import json
import math
import os
import numpy as np
import plotly.graph_objects as go

# ── Color constants (match project palette) ───────────────────────────────────
C_TEXT      = "#E2E8F0"
C_TEXT_DIM  = "#718096"
TRANSPARENT = "rgba(0,0,0,0)"
BG_DARK     = "#0B0F14"
BG_MID      = "#111820"

STATE_COLORS = {
    "positive": "#4CAF50",
    "neutral":  "#FFC107",
    "negative": "#F44336",
}

# ── Module-level mesh cache (loaded once, reused forever) ─────────────────────
_MESH_CACHE = {}

# ── Path resolution ───────────────────────────────────────────────────────────
_HERE = os.path.dirname(os.path.abspath(__file__))
_DATA = os.path.join(_HERE, "..", "data")

MESH_PATHS = {
    "light": os.path.join(_DATA, "vca_shell_mesh_light.json"),
    "full":  os.path.join(_DATA, "vca_shell_mesh.json"),
}


# ── Mesh loader with cache ────────────────────────────────────────────────────
def _load_mesh(quality: str = "light") -> dict | None:
    """Load mesh from disk on first call, return cached version thereafter."""
    key = quality if quality in MESH_PATHS else "light"

    if key in _MESH_CACHE:
        return _MESH_CACHE[key]

    path = MESH_PATHS[key]

    # If full mesh not deployed (excluded by .gitignore), fall back to light
    if not os.path.exists(path):
        if key == "full":
            fallback = MESH_PATHS["light"]
            if os.path.exists(fallback):
                key = "light"
                path = fallback
            else:
                _MESH_CACHE[key] = None
                return None
        else:
            _MESH_CACHE[key] = None
            return None

    try:
        with open(path, "r") as f:
            mesh = json.load(f)
        _MESH_CACHE[key] = mesh
        return mesh
    except (json.JSONDecodeError, OSError):
        _MESH_CACHE[key] = None
        return None


# ── Parametric sphere fallback ────────────────────────────────────────────────
def _parametric_sphere(r: float = 5.1, n: int = 40) -> tuple:
    """Generate a simple UV sphere as fallback when mesh files unavailable."""
    u = np.linspace(0, 2 * math.pi, n)
    v = np.linspace(0, math.pi, n)
    x = r * np.outer(np.cos(u), np.sin(v)).flatten()
    y = r * np.outer(np.sin(u), np.sin(v)).flatten()
    z = r * np.outer(np.ones(n), np.cos(v)).flatten()

    # Build triangle indices
    i_idx, j_idx, k_idx = [], [], []
    for a in range(n - 1):
        for b in range(n - 1):
            p = a * n + b
            i_idx += [p, p + 1]
            j_idx += [p + n, p + n]
            k_idx += [p + n + 1, p + n + 1]

    return (x.tolist(), y.tolist(), z.tolist(),
            i_idx, j_idx, k_idx)


# ── Z offset for buoyancy state ───────────────────────────────────────────────
def _z_offset(buoyancy_state: str, net_force_N: float) -> float:
    """Compute shell Z position based on buoyancy state."""
    if buoyancy_state == "positive":
        magnitude = min(abs(net_force_N) / 5000.0, 1.0)
        return 0.4 + magnitude * 2.5
    elif buoyancy_state == "negative":
        magnitude = min(abs(net_force_N) / 5000.0, 1.0)
        return 0.4 - magnitude * 1.5
    else:
        return 0.4  # design gap: 0.40 m


# ── Main scene builder ────────────────────────────────────────────────────────
def build_3d_scene(
    buoyancy_state: str,
    net_force_N: float,
    quality: str = "light",
) -> go.Figure:
    """
    Build the 3D ConOps visualization.

    Parameters
    ----------
    buoyancy_state : "positive" | "neutral" | "negative"
    net_force_N    : net vertical force in Newtons
    quality        : "light" (default, Render-safe) | "full" (local only)

    Returns
    -------
    Plotly Figure
    """
    state_color = STATE_COLORS.get(buoyancy_state, STATE_COLORS["neutral"])
    z_off = _z_offset(buoyancy_state, net_force_N)

    fig = go.Figure()

    # ── Shell mesh (or parametric fallback) ───────────────────────────────────
    mesh = _load_mesh(quality)

    if mesh is not None:
        x = [v + 0      for v in mesh["x"]]
        y = [v + 0      for v in mesh["y"]]
        z = [v + z_off  for v in mesh["z"]]
        fig.add_trace(go.Mesh3d(
            x=x, y=y, z=z,
            i=mesh["i"], j=mesh["j"], k=mesh["k"],
            color="#8B9EB5",
            opacity=0.75,
            flatshading=False,
            lighting=dict(
                ambient=0.5,
                diffuse=0.7,
                specular=0.3,
                roughness=0.6,
                fresnel=0.2,
            ),
            lightposition=dict(x=1000, y=1000, z=2000),
            name="VCA Shell",
            showlegend=True,
            hoverinfo="skip",
        ))
    else:
        # Parametric sphere fallback
        sx, sy, sz, si, sj, sk = _parametric_sphere(r=5.1)
        sz = [v + z_off for v in sz]
        fig.add_trace(go.Mesh3d(
            x=sx, y=sy, z=sz,
            i=si, j=sj, k=sk,
            color="#8B9EB5", opacity=0.75,
            name="VCA Shell (parametric)",
            showlegend=True, hoverinfo="skip",
        ))

    # ── Landing plate ─────────────────────────────────────────────────────────
    plate_r = 7.0
    theta   = np.linspace(0, 2 * math.pi, 64)
    px = (plate_r * np.cos(theta)).tolist()
    py = (plate_r * np.sin(theta)).tolist()
    pz = [0.0] * 64

    fig.add_trace(go.Scatter3d(
        x=px, y=py, z=pz,
        mode="lines",
        line=dict(color="#4A7A9B", width=3),
        name="Landing Plate",
        showlegend=True,
        hoverinfo="skip",
    ))

    # ── Magnetic coil ─────────────────────────────────────────────────────────
    coil_r = 3.5
    cx = (coil_r * np.cos(theta)).tolist()
    cy = (coil_r * np.sin(theta)).tolist()
    cz = [0.02] * 64

    fig.add_trace(go.Scatter3d(
        x=cx, y=cy, z=cz,
        mode="lines",
        line=dict(color="#FFC107", width=2),
        name="Magnetic Coil",
        showlegend=True,
        hoverinfo="skip",
    ))

    # ── State arrow ───────────────────────────────────────────────────────────
    arrow_tip  = z_off + (1.5 if buoyancy_state == "positive" else
                          -1.0 if buoyancy_state == "negative" else 0)
    arrow_base = z_off

    fig.add_trace(go.Scatter3d(
        x=[0, 0], y=[0, 0], z=[arrow_base, arrow_tip],
        mode="lines",
        line=dict(color=state_color, width=6),
        name=f"State: {buoyancy_state.capitalize()}",
        showlegend=True,
        hoverinfo="skip",
    ))

    # ── Layout ────────────────────────────────────────────────────────────────
    axis_style = dict(
        showbackground=False,
        showgrid=False,
        zeroline=False,
        showticklabels=False,
        title="",
    )

    fig.update_layout(
        scene=dict(
            xaxis=dict(**axis_style),
            yaxis=dict(**axis_style),
            zaxis=dict(**axis_style, range=[-3, 12]),
            bgcolor=BG_DARK,
            aspectmode="data",
            camera=dict(
                eye=dict(x=1.4, y=1.4, z=0.8),
                up=dict(x=0, y=0, z=1),
            ),
        ),
        uirevision="constant",
        paper_bgcolor=TRANSPARENT,
        plot_bgcolor=TRANSPARENT,
        font=dict(color=C_TEXT, size=11),
        margin=dict(l=0, r=0, t=0, b=0),
        height=400,
        legend=dict(
            font=dict(color=C_TEXT, size=10),
            bgcolor="rgba(11,15,20,0.7)",
            bordercolor="#1E2A38",
            borderwidth=1,
            x=0.01, y=0.99,
        ),
    )

    return fig