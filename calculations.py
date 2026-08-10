import numpy as np
from htw_data import get_table

# Coefficient of friction values
COF = {
    "Molykote 1000": 0.13,
    "Molykote P37": 0.14,
    "Copa Slip": 0.12,
    "PTFE Coated": 0.08,
    "No Lubricant": 0.16
}

# Yield strength values (psi)
YIELD_STRENGTH = {
    "ASTM A193 - B7": 105000,
    "ASTM A193 - B7M": 80000,
    "ASTM A193 - B16": 105000,
    "ASTM A193 - L7": 105000,
    "ASTM A193 - L7M": 80000,
    "ISO 3506-1 - A2-70 (304SS)": 65267,
    "ISO 3506-1 - A4-70 (304SS)": 65267,
    "ASTM A193 - B8 Class 1": 30000,
    "ASTM A193 - B8M Class 1": 30000,
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
    "1 1/2": 1.492
}

# Percentage utilization factor
UTILIZATION_FACTOR = {
    "Spiral Wound": 0.50,  # SPW
    "CNAF": 0.30,
    "Rubber": 0.30,
    "RTJ": 0.40,
    "Teflon": 0.40
}


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


def calculate_torque(bolt_material, gasket_type, lubricant, bolt_size, unit_system):

    # T = F × K × D / 12 (for lb-ft)

    # Where:
    # F = tensile stress area × yield strength × utilization factor
    # K = coefficient of friction + 0.04
    # D = bolt diameter (inches)

    # Get the values from dictionaries
    yield_strength = YIELD_STRENGTH[bolt_material]
    ts_area = TENSILE_STRESS_AREA[bolt_size]
    utilization_f = UTILIZATION_FACTOR[gasket_type]
    cof = COF[lubricant]

    # Bolt load
    bolt_load = ts_area * yield_strength * utilization_f

    if unit_system == "Metric (N·m, mm, N)":
        bolt_load_f = bolt_load * 4.44822
        bolt_load_unit = "N"
    else:
        bolt_load_f = bolt_load
        bolt_load_unit = "lbf"

    # Nut factor
    nut_f = cof + 0.04

    # Bolt diameter (convert string to float)
    diameter = parse_bolt_size(bolt_size)

    # Torque in lb-ft
    torque_lbft = (bolt_load * nut_f * diameter) / 12

    # Always keep an N·m value around - the HTW pressure charts are metric
    # regardless of which unit system the user picked for display.
    torque_nm = torque_lbft * 1.35582

    # Convert to N·m if the metric is selected for display
    if "Metric" in unit_system:
        torque = torque_nm
        unit = "N·m"
    else:
        torque = torque_lbft
        unit = "lb-ft"

    return {
        "bolt_load": bolt_load_f,
        "bolt_load_unit": bolt_load_unit,
        "nut_factor": nut_f,
        "yield_strength": yield_strength,
        "tensile_area": ts_area,
        "utilization_factor": utilization_f,
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
