# LTA Parametric Design Dashboard

**Live deployment:** https://lta-parametric-dashboard.onrender.com  
**Author:** Nirmit Sachde, M.S., Northeastern University  
**Mentor:** David W. Clark, P.E., Adaptive Concepts Academy  

A physics-accurate, web-deployed engineering dashboard for parametric design of a Lighter Than Air (LTA) vehicle featuring a Rotational Spherical Lifting Structure. Replaces the static Excel-based parametric model with an interactive, real-time visualization and analysis tool.

---

## Pages

### 1. Dashboard
Interactive parameter inputs (sliders + numeric entry) connected to live pilot-style gauges and a 3D ConOps visualization.

- 5 parametric inputs: outer radius, shell thickness, material density, internal pressure, atmospheric pressure
- 6 FAA-standard gauges: lift force, weight force, net force, BRS (rpm), available mass, buoyancy state indicator
- Buoyancy state logic: positive / neutral / negative with color-coded output
- Bidirectional SI / Imperial unit toggle
- 3D VCA body shell visualization (Mesh dropdown: Performance / Full Detail)
- Animated shell position responds to buoyancy state

### 2. Materials Comparison
Aerospace material feasibility assessment across 15 materials.

- Tabular comparison: density, available mass, BRS, stress, safety factor, pass/fail status
- "Use Material" button: applies selected density to Dashboard sliders
- Chart modes: available mass bar, density vs. mass bubble scatter, radar chart

### 3. Sensitivity Analysis
Parametric sensitivity and trade-off visualization.

- Tornado chart: one-at-a-time sensitivity at configurable variation percentage
- Trade-off contour: radius vs. thickness heat map for available mass
- Feasibility boundary: max thickness envelope for positive buoyancy

### 4. Power Model
Onboard power consumption model for the rotating spherical lifting structure.

**Physics chain:**
```
omega      = 2 * pi * rpm / 60                          [rad/s]
rho_gas    = rho_1atm * P_frac                          [kg/m3]
Re         = rho_gas * omega * R^2 / mu                 [-]
Cf         = 0.074 / Re^0.2                             [-]
P_gas_drag = (3 * pi^2 / 8) * rho_gas * Cf * omega^3 * R^5   [W]
P_bearings = Tb * omega                                 [W]
P_total    = P_gas_drag + P_bearings                    [W]
```

**Features:**
- Sliders for R, RPM, gas pressure fraction
- Gas type dropdown: Helium (default), Air, Hydrogen
- Bearing torque presets: Optimistic (10 N.m), Baseline (50 N.m), Conservative (200 N.m)
- Custom Tb input (overrides preset)
- Live baseline validation badge: P_gas_drag vs. 0.52 MW target (David Clark, 13 Mar 2026)
- Total power gauge with delta reference to 0.52 MW baseline
- Stacked power breakdown bar (gas drag vs. bearings)
- RPM sweep chart showing all 3 bearing presets simultaneously
- Export summary panel with clipboard copy

**Baseline validation:**  
R = 9.2 m, 600 rpm, Helium at 1% Patm, Tb = 50 N.m  
P_gas_drag = 0.545 MW (target ~0.52 MW, error 4.8%)

---

## Project Structure

```
project/
├── app.py                          # Main Dash app, routing, all callbacks
├── requirements.txt
├── README.md
├── assets/
│   └── style.css
├── data/
│   └── 7_Design_Parametric_Dashboard.xlsx
├── engine/
│   ├── buoyancy_calculator.py      # Core buoyancy physics engine
│   ├── materials_db.py             # 15-material aerospace database
│   ├── sensitivity.py              # Tornado, contour, boundary computation
│   └── power_model.py              # Onboard power consumption model (NEW)
├── pages/
│   ├── materials.py                # Materials page layout
│   ├── sensitivity.py              # Sensitivity page layout
│   └── power_page.py               # Power model page layout + callbacks (NEW)
├── visualization/
│   ├── gauges.py                   # FAA-standard pilot gauges
│   └── sphere_animation.py         # 3D VCA shell ConOps scene
└── tests/
    └── test_power_model.py         # Power model validation test suite (NEW)
```

---

## Physics Reference

- Fomin et al. (2005), "Developing a Parametric Design Tool for Lighter Than Air Vehicles," *Proceedings of the 2005 Systems and Information Engineering Design Symposium*, University of Virginia / Northrop Grumman TASC.
- VCA CAD/FEA Project Report, Shashidher Reddy Masannagari, M.S. Mechanical Engineering, Arizona State University.
- Mentor guidance: David W. Clark, P.E., Adaptive Concepts Academy (power model formulas, baseline validation target, 13 Mar 2026).

---

## Running Locally

```bash
conda activate aca_dashboard_project_1
pip install -r requirements.txt
python app.py
# open http://localhost:8050
```

## Running Tests

```bash
python -m pytest tests/test_power_model.py -v
```

---

## Deployment

Hosted on Render (free tier). Production uses Dash 2.18.x + Plotly 5.24.x (pinned in requirements.txt).

Render auto-deploys on push to `main` branch of `NirmitSachde/lta-parametric-dashboard`.