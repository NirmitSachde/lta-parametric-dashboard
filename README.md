# Parametric Design Dashboard
## Feasibility Assessment of Lighter Than Air Vehicle with Rotational Spherical Lifting Structure

**Student:** Nirmit Sachde, M.S., Northeastern University - Boston  
**Mentor:** David W. Clark, P.E.  
**Duration:** 16 weeks  

---

## Overview

Engineering dashboard that dynamically computes and visualizes buoyancy behavior of a rotational spherical LTA vehicle based on parametric design inputs. Features pilot-style gauges, real-time computation, and 3D animated sphere visualization.

---

## Project Structure

```
aca_dashboard_project/
├── app.py                              # Main Dash application (entry point)
├── engine/
│   ├── __init__.py
│   └── buoyancy_calculator.py          # Physics computation engine
├── visualization/
│   ├── __init__.py
│   ├── gauges.py                       # Pilot gauge components
│   └── sphere_animation.py            # 3D sphere mesh + animation
├── data/
│   └── 7 Design Parametric Dashboard.xlsx  # Reference spreadsheet
├── docs/                               # Documentation (Phase 6)
├── requirements.txt
├── README.md
└── .gitignore
```

---

## Setup Instructions

### Prerequisites
- Python 3.10+
- Anaconda (recommended)

### 1. Activate Conda Environment
```bash
conda activate aca_dashboard_project_1
```

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

### 3. Create Project Folders
```bash
mkdir -p engine visualization data docs
touch engine/__init__.py visualization/__init__.py
```

### 4. Run the Dashboard (Development)
```bash
python app.py
```
Then open http://127.0.0.1:8050 in your browser.

### 5. Run the Dashboard (Production)
```bash
gunicorn app:server --bind 0.0.0.0:8050
```

---

## Physics Reference

The parametric model computes buoyancy feasibility for a hollow rotating sphere:

| Parameter | Formula |
|---|---|
| Inner Radius | R_outer - thickness |
| Surface Area | 4 π R_outer² |
| Interior Void Volume | (4/3) π R_inner³ |
| Total Sphere Volume | (4/3) π R_outer³ |
| Shell Volume | V_total - V_inner |
| Sphere Mass | ρ_material × V_shell |
| Displaced Air Mass | ρ_air × V_inner × (1 - P_internal / P_atm) |
| Buoyancy State | Compare sphere mass vs displaced air mass |
| Available Mass | Displaced air mass - sphere mass |
| Balanced Rotational Speed | √((P_atm - P_internal) / (ρ_material × thickness × R_inner)) |

---

## Tech Stack

- **Dash / Plotly** — Interactive web dashboard
- **NumPy / Pandas** — Numerical computation
- **Trimesh** — 3D sphere mesh generation
- **Gunicorn** — Production WSGI server