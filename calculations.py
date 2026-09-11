import numpy as np
from htw_data import get_table, psi_to_bar
from htb_data import get_hydraulic_area

# Yield strength (psi), bracketed by bolt diameter (inches).
# Each entry is a list of (max_diameter_inclusive, yield_strength) tuples, sorted ascending by diameter.
YIELD_STRENGTH_TABLE = {
    "ASTM A193 - B7": [
        (2.625, 105000),   # up to 2-5/8"
        (4.0, 95000),       # 2-5/8" to 4"
        (7.0, 75000),       # 4-1/8" to 7"
    ],
    "ASTM A193 - B7M": [
        (4.0, 80000),        # under 4"
        (7.0, 75000),        # 4" to 7"
    ],
    "ASTM A193 - B16": [
        (2.625, 105000),    # up to 2-5/8"
        (4.0, 95000),        # 2-5/8" to 4"
        (7.0, 85000),        # 4-1/8" to 7"
    ],
    "ASTM A193 - L7": [
        (999, 105000),
    ],
    "ASTM A193 - L7M": [
        (999, 80000),
    ],
    "ISO 3506-1 - A2-70 (304SS)": [
        (999, 65267),
    ],
    "ISO 3506-1 - A4-70 (304SS)": [
        (999, 65267),
    ],
    "ASTM A193 - B8 Class 1": [
        (999, 30000),
    ],
    "ASTM A193 - B8M Class 1": [
        (999, 30000),
    ],
}

# Tensile stress area values (in²)
TENSILE_STRESS_AREA = {
    "1/2": 0.1419,
    "5/8": 0.226,
    "3/4": 0.334,
    "7/8": 0.462,
    "1": 0.606,
    "1 1/8": 0.790,
    "1 1/4": 1.000,
    "1 3/8": 1.233,
    "1 1/2": 1.492,
    "1 5/8": 1.780,
    "1 3/4": 2.080,
    "1 7/8": 2.410,
    "2": 2.770,
    "2 1/4": 3.560,
    "2 1/2": 4.440,
    "2 3/4": 5.430,
    "3": 6.510,
    "3 1/4": 7.690,
    "3 1/2": 8.960,
    "3 3/4": 10.340,
    "4": 11.810
}

# Flange Load Loss Factor, used to inflate the first tensioning pass so
# that elastic interaction between bolts is compensated for.
FLLF = 1.25

# Which pass letters are used for each coverage pattern, in tensioning
# order (first pass tensioned -> last pass tensioned).
COVERAGE_PASSES = {
    "100% Coverage": ["A"],
    "50% Coverage": ["A", "B"],
    "33% Coverage": ["A", "B", "C"],
    "25% Coverage": ["A", "B", "C", "D"],
}

# Shared dropdown option lists, derived from the tables above so the UI
# and the calculation tables can never drift out of sync.
BOLT_MATERIALS = list(YIELD_STRENGTH_TABLE.keys())
BOLT_SIZES = list(TENSILE_STRESS_AREA.keys())


def parse_bolt_size(bolt_size):
    """
    Convert a bolt-size string to a decimal inch value. Handles:
      "1"        -> 1.0
      "3/4"      -> 0.75
      "1 1/8"    -> 1.125
    """
    bolt_size = bolt_size.strip()
    if " " in bolt_size:
        whole_str, frac_str = bolt_size.split(" ", 1)
        whole = float(whole_str)
    else:
        whole = 0.0
        frac_str = bolt_size

    if "/" in frac_str:
        numerator, denominator = frac_str.split("/")
        frac_value = float(numerator) / float(denominator)
    else:
        frac_value = float(frac_str)

    return whole + frac_value


def get_yield_strength(bolt_material, bolt_size):
    """
    Look up yield strength (psi) for a material at a given bolt size,
    using the diameter brackets in YIELD_STRENGTH_TABLE. Falls back to
    the last (largest) bracket if the size exceeds every bracket defined
    for that material.
    """
    diameter = parse_bolt_size(bolt_size)
    brackets = YIELD_STRENGTH_TABLE[bolt_material]

    for max_diameter, value in brackets:
        if diameter <= max_diameter:
            return value

    # Size larger than any defined bracket - use the top bracket's value
    return brackets[-1][1]


def calculate_bolt_load(bolt_material, utilization_factor, bolt_size):
    """
    F = tensile stress area x yield strength x utilization factor

    utilization_factor is now a user-supplied fraction (e.g. 0.5),
    not looked up from a gasket-type table.
    """
    yield_strength = get_yield_strength(bolt_material, bolt_size)
    ts_area = TENSILE_STRESS_AREA[bolt_size]
    return ts_area * yield_strength * utilization_factor


def calculate_torque(bolt_material, utilization_factor, cof, bolt_size, unit_system):
    bolt_load = calculate_bolt_load(bolt_material, utilization_factor, bolt_size)

    if unit_system == "Metric (N·m, mm, N)":
        bolt_load_f = bolt_load * 4.44822
        bolt_load_unit = "N"
    else:
        bolt_load_f = bolt_load
        bolt_load_unit = "lbf"

    nut_f = cof + 0.04
    diameter = parse_bolt_size(bolt_size)
    torque_lbft = (bolt_load * nut_f * diameter) / 12
    torque_nm = torque_lbft * 1.35582

    if "Metric" in unit_system:
        torque = torque_nm
        unit = "N·m"
    else:
        torque = torque_lbft
        unit = "lb-ft"

    return {
        "bolt_load": bolt_load_f,
        "bolt_load_lbf": bolt_load,
        "bolt_load_unit": bolt_load_unit,
        "nut_factor": nut_f,
        "yield_strength": get_yield_strength(bolt_material, bolt_size),
        "tensile_area": TENSILE_STRESS_AREA[bolt_size],
        "utilization_factor": utilization_factor,
        "torque": torque,
        "torque_nm": torque_nm,
        "unit": unit,
        "30_percent": torque * 0.3,
        "60_percent": torque * 0.6
    }


def calculate_pressure(torque_nm, brand, drive_type, model, hex_size):
    """
    Interpolate (or extrapolate, with a flag) the hydraulic pressure (bar)
    required to achieve torque_nm on the given HTW brand/drive-type/model/
    drive-size, using linear interpolation against the vendor's Bar/Nm chart.

    Returns a dict: pressure (bar), table (the (pressure, torque) pairs
    used, for plotting), and out_of_range (True if torque_nm fell outside
    the chart and had to be extrapolated).
    """
    table = get_table(brand, drive_type, model, hex_size)
    pressures = np.array([p for p, t in table], dtype=float)
    torques = np.array([t for p, t in table], dtype=float)

    out_of_range = torque_nm < torques[0] or torque_nm > torques[-1]

    if out_of_range and torque_nm > torques[-1]:
        # Linear extrapolation past the top of the chart using the last segment
        slope = (pressures[-1] - pressures[-2]) / (torques[-1] - torques[-2])
        pressure = pressures[-1] + slope * (torque_nm - torques[-1])
    elif out_of_range and torque_nm < torques[0]:
        pressure = 0.0
    else:
        pressure = float(np.interp(torque_nm, torques, pressures))

    return {
        "pressure": pressure,
        "table": table,
        "out_of_range": out_of_range
    }


def calculate_tensioning(bolt_material, utilization_factor, bolt_size, grip_length, brand, tool, coverage, unit_system):
    """
    Calculate hydraulic bolt-tensioning pressures.

    Bolt Load (F)   = tensile stress area x yield strength x utilization factor
    TLLF            = Tool Load Loss Factor = 1.01 + (bolt diameter / grip length)
    Pressure (T)    = (Bolt Load / Hydraulic Area) x TLLF        [psi]

    Coverage passes (FLLF = Flange Load Loss Factor = 1.25):
      100% Coverage: single pass, pressure = T
      50% Coverage:  Pass B = T,  Pass A = Pass B x FLLF
      33% Coverage:  Pass C = T,  Pass A = Pass C x FLLF,
                     Pass B = Pass A - ((Pass A - Pass C) / 2)
      25% Coverage:  Pass D = T,  Pass A = Pass D x FLLF,
                     Pass B = Pass A - ((Pass A - Pass D) / 3),
                     Pass C = Pass B - ((Pass A - Pass D) / 3)

    grip_length is in inches. Returns pressures in both psi and bar so the
    caller can display either unit without recomputing.
    """
    if grip_length <= 0:
        raise ValueError("Grip length must be greater than zero.")

    diameter = parse_bolt_size(bolt_size)
    bolt_load = calculate_bolt_load(bolt_material, utilization_factor, bolt_size)

    tllf = 1.01 + (diameter / grip_length)

    area = get_hydraulic_area(brand, tool)
    if not area:
        raise ValueError(f"No hydraulic area found for {brand} / {tool}")

    base_pressure_psi = (bolt_load / area) * tllf

    if coverage == "100% Coverage":
        pass_a = base_pressure_psi
        passes_psi = {"A": pass_a}
    elif coverage == "50% Coverage":
        pass_b = base_pressure_psi
        pass_a = pass_b * FLLF
        passes_psi = {"A": pass_a, "B": pass_b}
    elif coverage == "33% Coverage":
        pass_c = base_pressure_psi
        pass_a = pass_c * FLLF
        pass_b = pass_a - ((pass_a - pass_c) / 2)
        passes_psi = {"A": pass_a, "B": pass_b, "C": pass_c}
    elif coverage == "25% Coverage":
        pass_d = base_pressure_psi
        pass_a = pass_d * FLLF
        pass_b = pass_a - ((pass_a - pass_d) / 3)
        pass_c = pass_b - ((pass_a - pass_d) / 3)
        passes_psi = {"A": pass_a, "B": pass_b, "C": pass_c, "D": pass_d}
    else:
        raise ValueError(f"Unknown coverage: {coverage}")

    passes_bar = {letter: psi_to_bar(p) for letter, p in passes_psi.items()}

    imperial = unit_system == "Imperial (psi, lbf)"
    display_unit = "psi" if imperial else "bar"
    passes_display = passes_psi if imperial else passes_bar
    bolt_load_display = bolt_load if imperial else bolt_load * 4.44822
    bolt_load_unit = "lbf" if imperial else "N"

    return {
        "bolt_load": bolt_load_display,
        "bolt_load_unit": bolt_load_unit,
        "tllf": tllf,
        "diameter": diameter,
        "area_in2": area,
        "base_pressure_psi": base_pressure_psi,
        "passes_psi": passes_psi,
        "passes_bar": passes_bar,
        "passes": passes_display,
        "unit": display_unit,
        "coverage": coverage,
    }


def assign_bolt_passes(num_bolts, coverage):
    """
    Assign a tensioning pass letter to each bolt position (in order
    around the flange) for the given coverage pattern, so that no two
    adjacent bolts belong to the same pass - e.g. for 50% coverage,
    bolts alternate A / B / A / B ... around the flange.

    Returns a list of pass letters, one per bolt, in bolt order.
    """
    pass_sequence = COVERAGE_PASSES[coverage]
    num_groups = len(pass_sequence)
    return [pass_sequence[i % num_groups] for i in range(num_bolts)]


def generate_crisscross_order(num_bolts):
    """
    Generate the star/crisscross bolt-tightening order. Bolts are split
    into 4 groups by (bolt_index % 4), the groups are visited in
    bit-reversed order (0, 2, 1, 3), and each group is stepped through
    sequentially with a stride of 4.

    Examples (1-indexed, clockwise):
      8 bolts:  1-5-3-7-2-6-4-8
      12 bolts: 1-5-9-3-7-11-2-6-10-4-8-12
      16 bolts: 1-5-9-13-3-7-11-15-2-6-10-14-4-8-12-16
      20 bolts: 1-5-9-13-17-3-7-11-15-19-2-6-10-14-18-4-8-12-16-20
      24 bolts: 1-5-9-13-17-21-3-7-11-15-19-23-2-6-10-14-18-22-4-8-12-16-20-24
      28 bolts: 1-5-9-13-17-21-25-3-7-11-15-19-23-27-2-6-10-14-18-22-26-4-8-12-16-20-24-28

    Holds for any bolt count divisible by 4 (covers every UI option:
    4, 8, 12, 16, 20, 24, 28). Falls back to a greedy farthest-point
    approximation otherwise.
    """
    if num_bolts <= 0:
        return []

    if num_bolts % 4 == 0:
        group_size = num_bolts // 4
        group_start_order = [0, 2, 1, 3]
        order = []
        for group_start in group_start_order:
            for j in range(group_size):
                order.append(group_start + 4 * j)
        return order

    order = [0]
    remaining = list(range(1, num_bolts))
    while remaining:
        def min_dist(x):
            return min(min(abs(x - s), num_bolts - abs(x - s)) for s in order)
        best = max(remaining, key=lambda x: (min_dist(x), -x))
        order.append(best)
        remaining.remove(best)
    return order