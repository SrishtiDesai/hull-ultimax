"""
Simplified pressure-hull physics for Hull Forge.

IMPORTANT: this is a teaching-grade model, not engineering software.
- Elastic buckling: classic long thin cylinder under external pressure
      P_buckle = 2E / (1 - v^2) * (t/D)^3
- Crushing (material strength): thin-wall hoop stress, P_crush = S * t / R
- Fatigue: strength and stiffness knock-down that grows with dive count,
      knockdown(N) = max(0.2, 1 - a * log10(1 + N))
- Sphere: P_buckle = 2E / sqrt(3(1 - v^2)) * (t/R)^2 * imperfection, P_crush = 2 S t / R
- Real shells buckle below the ideal formulas because of imperfections, so an
  imperfection factor is applied (0.8 cylinder, 0.3 sphere; textbook-style values).
  The 'a' values below are ILLUSTRATIVE, chosen so composites degrade
  faster than metals (the real-world pattern). They are not validated data.
"""
import math

RHO_SEAWATER = 1025.0   # kg/m^3
G = 9.81                # m/s^2
MPA = 1e6

# E = Young's modulus (MPa), S = compressive strength (MPa),
# rho = density (kg/m^3), a = fatigue degradation rate (illustrative)
MATERIALS = {
    "cfrp":     {"E": 70_000,  "nu": 0.30, "S": 600, "rho": 1600, "a": 0.20,
                 "note": "Carbon-fibre composite: light, but degrades with pressure cycling"},
    "titanium": {"E": 110_000, "nu": 0.34, "S": 880, "rho": 4500, "a": 0.02,
                 "note": "Ti-6Al-4V: strong, fatigue-tolerant, heavy"},
    "steel":    {"E": 205_000, "nu": 0.29, "S": 690, "rho": 7850, "a": 0.03,
                 "note": "HY-100 style steel: cheap and tough, very heavy"},
}

REQUIRED_SAFETY_FACTOR = 1.5   # collapse pressure must exceed 1.5x operating pressure
MAX_WEIGHT_RATIO = 0.70        # hull mass / displaced water mass (must still float)


def knockdown(material: str, dives: int) -> float:
    a = MATERIALS[material]["a"]
    return max(0.2, 1.0 - a * math.log10(1 + dives))


IMPERFECTION = {"cylinder": 0.8, "sphere": 0.3}


def collapse_pressure_mpa(material, diameter_m, thickness_mm, dives, shape="cylinder"):
    m = MATERIALS[material]
    t = thickness_mm / 1000.0
    R = diameter_m / 2.0
    kd = knockdown(material, dives)
    E, S, nu = m["E"] * kd, m["S"] * kd, m["nu"]
    if shape == "sphere":
        p_buckle = IMPERFECTION["sphere"] * 2 * E / math.sqrt(3 * (1 - nu ** 2)) * (t / R) ** 2
        p_crush = 2 * S * t / R
    else:
        p_buckle = IMPERFECTION["cylinder"] * 2 * E / (1 - nu ** 2) * (t / diameter_m) ** 3
        p_crush = S * t / R
    return min(p_buckle, p_crush), p_buckle, p_crush


def evaluate_design(material, diameter_m, thickness_mm, depth_m, planned_dives, crew,
                    shape="cylinder", length_m=3.0):
    """Run the hull through its whole service life. Returns a plain dict."""
    if shape not in ("cylinder", "sphere"):
        return {"error": "shape must be 'cylinder' or 'sphere'"}
    if material not in MATERIALS:
        return {"error": f"Unknown material '{material}'. Choose from {list(MATERIALS)}"}
    if thickness_mm <= 0 or diameter_m <= 0 or length_m <= 0:
        return {"error": "diameter, thickness and length must be positive"}

    m = MATERIALS[material]
    t = thickness_mm / 1000.0
    p_op = RHO_SEAWATER * G * depth_m / MPA

    # Geometry / buoyancy checks
    inner_d = diameter_m - t
    R_mid = diameter_m / 2
    if shape == "sphere":
        min_inner_d = 1.5 + 0.15 * crew
        min_len = 0.0
        shell_mass = m["rho"] * 4 * math.pi * R_mid ** 2 * t
        displaced = RHO_SEAWATER * (4 / 3) * math.pi * (R_mid + t / 2) ** 3
    else:
        min_inner_d = 1.0 + 0.1 * crew
        min_len = 0.6 * crew
        shell_mass = m["rho"] * math.pi * diameter_m * t * length_m
        displaced = RHO_SEAWATER * math.pi * (R_mid + t / 2) ** 2 * length_m
    weight_ratio = shell_mass / displaced

    # Life simulation: find the first dive where collapse margin is lost
    first_unsafe = None   # safety factor below requirement
    implosion = None      # collapse pressure below operating pressure
    for n in range(0, planned_dives + 1):
        pc, _, _ = collapse_pressure_mpa(material, diameter_m, thickness_mm, n, shape)
        sf = pc / p_op
        if first_unsafe is None and sf < REQUIRED_SAFETY_FACTOR:
            first_unsafe = n
        if sf < 1.0:
            implosion = n
            break

    pc0, pb0, py0 = collapse_pressure_mpa(material, diameter_m, thickness_mm, 0, shape)
    pc_end, _, _ = collapse_pressure_mpa(material, diameter_m, thickness_mm,
                                         implosion if implosion else planned_dives, shape)
    governing = "elastic buckling" if pb0 < py0 else "material crushing"

    problems = []
    if inner_d < min_inner_d:
        problems.append(f"Interior too small for {crew} crew: inner diameter {inner_d:.2f} m < {min_inner_d:.2f} m")
    if shape == "cylinder" and length_m < min_len:
        problems.append(f"Hull too short for {crew} crew: {length_m:.2f} m < {min_len:.2f} m")
    if weight_ratio > MAX_WEIGHT_RATIO:
        problems.append(f"Too heavy to float: hull/displacement ratio {weight_ratio:.2f} > {MAX_WEIGHT_RATIO}")
    if implosion is not None:
        problems.append(f"HULL IMPLODES on dive {implosion} (collapse pressure fell below {p_op:.1f} MPa)")
    elif first_unsafe is not None:
        problems.append(f"Safety factor drops below {REQUIRED_SAFETY_FACTOR} at dive {first_unsafe}")

    return {
        "passed": not problems,
        "problems": problems,
        "operating_pressure_mpa": round(p_op, 1),
        "collapse_pressure_new_mpa": round(pc0, 1),
        "collapse_pressure_end_of_life_mpa": round(pc_end, 1),
        "safety_factor_new": round(pc0 / p_op, 2),
        "safety_factor_end_of_life": round(pc_end / p_op, 2),
        "shape": shape,
        "governing_failure_mode": governing,
        "implosion_dive": implosion,
        "first_unsafe_dive": first_unsafe,
        "required_safety_factor": REQUIRED_SAFETY_FACTOR,
        "max_weight_ratio": MAX_WEIGHT_RATIO,
        "hull_mass_kg": round(shell_mass),
        "weight_ratio": round(weight_ratio, 2),
        "material_note": m["note"],
    }


def fatigue_curve(material, diameter_m, thickness_mm, depth_m, max_dives, shape="cylinder"):
    """Safety factor vs dive count, for plotting in the demo."""
    p_op = RHO_SEAWATER * G * depth_m / MPA
    return [(n, collapse_pressure_mpa(material, diameter_m, thickness_mm, n, shape)[0] / p_op)
            for n in range(0, max_dives + 1, max(1, max_dives // 100))]
