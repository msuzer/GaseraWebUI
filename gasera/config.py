# gasera_config.py

# IP or hostname of the Gasera device or simulator
GASERA_IP_ADDRESS = "192.168.1.100"
GASERA_PORT_NUMBER = 8888

# Optional: Mapping of CAS codes to gas names
CAS_NAMES = {
    "74-82-8": "Methane",
    "124-38-9": "Carbon Dioxide",
    "7732-18-5": "Water Vapor",
    "630-08-0": "Carbon Monoxide",
    "10024-97-2": "Nitrous Oxide",
    "7664-41-7": "Ammonia",
    "7446-09-5": "Sulfur Dioxide",
    "7782-44-7": "Oxygen",
    "75-07-0": "Acetaldehyde",
    "64-17-5": "Ethanol",
    "67-56-1": "Methanol"
}

def get_gas_name(cas):
    return CAS_NAMES.get(cas, None)
# Consistent color mapping for charting (Chart.js, Bootstrap-safe)
CAS_COLORS = {
    "74-82-8": "#1f77b4",     # CH₄
    "124-38-9": "#ff7f0e",    # CO₂
    "7732-18-5": "#2ca02c",   # H₂O
    "630-08-0": "#d62728",    # CO
    "10024-97-2": "#9467bd",  # N₂O
    "7664-41-7": "#8c564b",   # NH₃
    "7446-09-5": "#e377c2",   # SO₂
    "7782-44-7": "#7f7f7f",   # O₂
    "75-07-0": "#bcbd22",     # Acetaldehyde
    "64-17-5": "#17becf",     # Ethanol
    "67-56-1": "#a05d56",     # Methanol
}

def get_color_for_cas(cas):
    return CAS_COLORS.get(cas, "#999")