"""
Hydraulic Bolt Tensioning (HBT) tool data.

A hydraulic tensioner converts hydraulic pressure into bolt load through
its "hydraulic effective area" (in²). Each tool covers a range of bolt
sizes it can be fitted to.

Data is organised as:

    TENSIONER_DATA[brand][tool_name] -> hydraulic effective area (in²)

Sources:
1. Hydratight - HT/HL series hydraulic bolt tensioning tools
   (tool bolt-range / hydraulic area chart)

To add another brand or tool, add another entry with the same shape -
the GUI and calculation code read this structure directly, so nothing
else needs to change.
"""

TENSIONER_DATA = {
    "Hydratight": {
        'HT01 (1" - 1-1/8")': 3.53,
        'HL01 (1-1/4" - 1-3/8")': 5.4,
        'HL02 (1-1/4" - 1-1/2")': 6.63,
        'HL03 (1-1/2" - 1-3/4")': 9.16,
        'HL04 (1-5/8" - 2")': 12.22,
        'HL05 (1-7/8" - 2-1/4")': 15.34,
        'HL06 (2-1/4" - 2-1/2")': 19.75,
        'HL07 (2-1/2" - 2-3/4")': 24.71,
        'HL08 (2-3/4" - 3")': 28.4,
        'HL85 (3" - 3-1/2")': 33.76,
        'HL10 (3-3/4" - 4")': 40.53,
    }
}


def get_tensioner_brands():
    return list(TENSIONER_DATA.keys())


def get_tensioner_tools(brand):
    return list(TENSIONER_DATA.get(brand, {}).keys())


def get_hydraulic_area(brand, tool):
    """Hydraulic effective area (in²) for a given brand/tool."""
    return TENSIONER_DATA.get(brand, {}).get(tool)
