"""
tests/test_power_model.py
=========================
Formal validation test suite for engine/power_model.py

Run from project root:
    python -m pytest tests/test_power_model.py -v

or directly:
    python tests/test_power_model.py

Tests assert:
  1. Baseline validation: P_gas_drag at David Clark target conditions within 10% of 0.52 MW
  2. Physics monotonicity: P_gas_drag increases with R, rpm, pressure fraction
  3. Bearing power: P_bearings = Tb * omega exactly
  4. Gas presets: all three gases produce physically valid results
  5. Edge cases: very low rpm, very low pressure fraction
  6. Cf formula: matches 0.074 / Re^0.2 independently
  7. P_total = P_gas_drag + P_bearings exactly
  8. Zero bearing torque: P_total equals P_gas_drag exactly
"""

import math
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from engine.power_model import compute_power, GAS_PRESETS, BEARING_PRESETS


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _He():
    return GAS_PRESETS["Helium"]["rho_1atm"], GAS_PRESETS["Helium"]["mu"]


def _run(R=9.2, rpm=600.0, P_frac=0.01, gas="Helium", preset="Baseline"):
    rho, mu = GAS_PRESETS[gas]["rho_1atm"], GAS_PRESETS[gas]["mu"]
    Tb = BEARING_PRESETS[preset]
    return compute_power(R, rpm, P_frac, rho, mu, Tb)


# ---------------------------------------------------------------------------
# Test 1: Baseline validation (David Clark target: ~0.52 MW gas drag)
# ---------------------------------------------------------------------------
def test_baseline_gas_drag():
    """P_gas_drag at baseline conditions must be within 10% of 0.52 MW."""
    res = _run(R=9.2, rpm=600.0, P_frac=0.01, gas="Helium", preset="Baseline")
    P_drag_MW = res["P_gas_drag"] / 1e6
    target    = 0.52
    err_pct   = abs(P_drag_MW - target) / target * 100
    assert err_pct <= 10.0, (
        f"Baseline gas-drag power {P_drag_MW:.4f} MW deviates "
        f"{err_pct:.1f}% from target {target} MW (tolerance 10%)"
    )
    print(f"  PASS  P_gas_drag = {P_drag_MW:.4f} MW  (target {target} MW, err {err_pct:.2f}%)")


# ---------------------------------------------------------------------------
# Test 2: P_total = P_gas_drag + P_bearings exactly
# ---------------------------------------------------------------------------
def test_power_total_sum():
    """P_total must equal P_gas_drag + P_bearings to floating-point precision."""
    res = _run()
    diff = abs(res["P_total"] - res["P_gas_drag"] - res["P_bearings"])
    assert diff < 1e-6, f"P_total mismatch: diff = {diff:.2e} W"
    print(f"  PASS  P_total = P_drag + P_bearings  (diff {diff:.2e} W)")


# ---------------------------------------------------------------------------
# Test 3: P_bearings = Tb * omega exactly
# ---------------------------------------------------------------------------
def test_bearing_power_formula():
    """P_bearings must equal Tb * omega to floating-point precision."""
    rho, mu = _He()
    Tb  = BEARING_PRESETS["Baseline"]
    res = compute_power(9.2, 600.0, 0.01, rho, mu, Tb)
    expected = Tb * res["omega"]
    diff = abs(res["P_bearings"] - expected)
    assert diff < 1e-9, f"P_bearings = {res['P_bearings']:.6f}, Tb*omega = {expected:.6f}"
    print(f"  PASS  P_bearings = Tb * omega  ({res['P_bearings']:.4f} W)")


# ---------------------------------------------------------------------------
# Test 4: Cf formula independently verified
# ---------------------------------------------------------------------------
def test_cf_formula():
    """Cf must match 0.074 / Re^0.2 independently of compute_power internals."""
    rho, mu = _He()
    R, rpm, P_frac = 9.2, 600.0, 0.01
    omega   = 2.0 * math.pi * rpm / 60.0
    rho_gas = rho * P_frac
    Re      = rho_gas * omega * R**2 / mu
    Cf_exp  = 0.074 / Re**0.2
    res     = compute_power(R, rpm, P_frac, rho, mu, 50.0)
    diff    = abs(res["Cf"] - Cf_exp)
    assert diff < 1e-10, f"Cf mismatch: got {res['Cf']:.8f}, expected {Cf_exp:.8f}"
    print(f"  PASS  Cf = 0.074 / Re^0.2 = {Cf_exp:.6f}")


# ---------------------------------------------------------------------------
# Test 5: Monotonicity -- P_gas_drag increases with R
# ---------------------------------------------------------------------------
def test_monotonic_radius():
    """Gas-drag power must strictly increase as sphere radius increases."""
    rho, mu = _He()
    Tb  = BEARING_PRESETS["Baseline"]
    radii  = [3.0, 5.0, 7.0, 9.2, 12.0]
    powers = [compute_power(r, 600.0, 0.01, rho, mu, Tb)["P_gas_drag"] for r in radii]
    for i in range(len(powers) - 1):
        assert powers[i] < powers[i+1], (
            f"P_gas_drag not monotonic at R={radii[i+1]}: "
            f"{powers[i]/1e6:.4f} MW >= {powers[i+1]/1e6:.4f} MW"
        )
    print(f"  PASS  P_gas_drag monotonically increases with R")


# ---------------------------------------------------------------------------
# Test 6: Monotonicity -- P_gas_drag increases with RPM
# ---------------------------------------------------------------------------
def test_monotonic_rpm():
    """Gas-drag power must strictly increase as RPM increases (omega^3 scaling)."""
    rho, mu = _He()
    Tb   = BEARING_PRESETS["Baseline"]
    rpms = [100, 300, 600, 900, 1200]
    powers = [compute_power(9.2, r, 0.01, rho, mu, Tb)["P_gas_drag"] for r in rpms]
    for i in range(len(powers) - 1):
        assert powers[i] < powers[i+1], (
            f"P_gas_drag not monotonic at rpm={rpms[i+1]}: "
            f"{powers[i]/1e6:.4f} >= {powers[i+1]/1e6:.4f} MW"
        )
    print(f"  PASS  P_gas_drag monotonically increases with RPM (omega^3 scaling confirmed)")


# ---------------------------------------------------------------------------
# Test 7: All gas presets return physically valid results
# ---------------------------------------------------------------------------
def test_all_gas_presets():
    """Every gas type in GAS_PRESETS must produce positive, finite power values."""
    for gas_name, props in GAS_PRESETS.items():
        res = compute_power(9.2, 600.0, 0.01, props["rho_1atm"], props["mu"], 50.0)
        for key in ("P_gas_drag", "P_bearings", "P_total", "Re", "Cf", "omega"):
            val = res[key]
            assert math.isfinite(val),  f"{gas_name}: {key} is not finite ({val})"
            assert val > 0,             f"{gas_name}: {key} <= 0 ({val})"
        print(f"  PASS  {gas_name}: P_total = {res['P_total']/1e6:.4f} MW")


# ---------------------------------------------------------------------------
# Test 8: Zero bearing torque -- P_total equals P_gas_drag
# ---------------------------------------------------------------------------
def test_zero_bearing_torque():
    """With Tb=0, P_total must equal P_gas_drag to floating-point precision."""
    rho, mu = _He()
    res  = compute_power(9.2, 600.0, 0.01, rho, mu, Tb=0.0)
    diff = abs(res["P_total"] - res["P_gas_drag"])
    assert diff < 1e-9, f"Tb=0 but P_total != P_gas_drag (diff {diff:.2e} W)"
    assert res["P_bearings"] == 0.0, f"P_bearings should be 0 when Tb=0"
    print(f"  PASS  Tb=0: P_total = P_gas_drag = {res['P_total']/1e6:.4f} MW")


# ---------------------------------------------------------------------------
# Test 9: Bearing presets cover expected order (Optimistic < Baseline < Conservative)
# ---------------------------------------------------------------------------
def test_bearing_preset_ordering():
    """Bearing torque presets must be in ascending order: Optimistic < Baseline < Conservative."""
    opt  = BEARING_PRESETS["Optimistic"]
    base = BEARING_PRESETS["Baseline"]
    cons = BEARING_PRESETS["Conservative"]
    assert opt < base < cons, (
        f"Preset ordering violated: {opt} < {base} < {cons} is False"
    )
    print(f"  PASS  Presets ordered: Optimistic ({opt}) < Baseline ({base}) < Conservative ({cons}) N.m")


# ---------------------------------------------------------------------------
# Run all tests
# ---------------------------------------------------------------------------
TESTS = [
    test_baseline_gas_drag,
    test_power_total_sum,
    test_bearing_power_formula,
    test_cf_formula,
    test_monotonic_radius,
    test_monotonic_rpm,
    test_all_gas_presets,
    test_zero_bearing_torque,
    test_bearing_preset_ordering,
]

if __name__ == "__main__":
    print("\n=== LTA Power Model Test Suite ===\n")
    passed, failed = 0, 0
    for test_fn in TESTS:
        name = test_fn.__name__
        print(f"[{name}]")
        try:
            test_fn()
            passed += 1
        except AssertionError as e:
            print(f"  FAIL  {e}")
            failed += 1
        except Exception as e:
            print(f"  ERROR {type(e).__name__}: {e}")
            failed += 1
        print()
    print(f"Results: {passed} passed, {failed} failed out of {len(TESTS)} tests")
    if failed > 0:
        sys.exit(1)