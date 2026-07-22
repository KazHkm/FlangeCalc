
# Coefficient of friction values
COF = {
    "Molykote 1000": 0.13,
    "Molykote P37": 0.14
}

# Yield strength values (psi)
YIELD_STRENGTH = {
    "ASTM A193 - B7": 105000,
    "ASTM A193 - B8 C2": 100000
}

# Tensile stress area values (in²)
TENSILE_STRESS_AREA = {
    "1/2": 0.1419,
    "5/8": 0.226,
    "3/4": 0.334
}

# Percentage utilization factor
UTILIZATION_FACTOR = {
    "Spiral Wound": 0.50,  # SPW
    "CNAF": 0.30,
    "Rubber": 0.30,
    "RTJ": 0.40
}


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
    numerator, denominator = bolt_size.split("/")
    diameter = float(numerator) / float(denominator)

    # Torque in lb-ft
    torque_lbft = (bolt_load * nut_f * diameter) / 12

    # Convert to N·m if the metric is selected
    if "Metric" in unit_system:
        torque = torque_lbft * 1.35582
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
        "unit": unit,
        "30_percent": torque * 0.3,
        "60_percent": torque * 0.6
    }