"""Everything you are likely to want to change lives in this file.

app.py holds the UI wiring, spill_cost.py holds the cost model. Neither should
need editing to rebrand, retune, or change what the sales team can adjust.

Cost basis is Etkin (2004), EPA BOSCEM, presented at the Freshwater Spills
Symposium. Base tables are US dollars; see COST_BASE_YEAR. All Etkin figures
are per US GALLON in the source and converted internally - the only imperial
data in the model.
"""

# --- screen lock -----------------------------------------------------------
# NOT security. This file is downloaded by the browser and readable by anyone
# who visits the site. Real access control is Cloudflare Access, in front of
# the whole thing.
AUTH_USER = 'spilladmin'
AUTH_PASS = 'pipewise'

# --- wording ---------------------------------------------------------------
APP_TITLE = 'Release Cost Estimator'
LOCK_PROMPT = 'Sign in to run the model.'
DISCLAIMER = (
    'Order-of-magnitude planning estimate, not a quotation or a liability '
    'assessment. Hydrocarbon costs derive from Etkin (2004) EPA BOSCEM unit '
    'costs, which were built from marine and inland-waterway response data; '
    'onshore buried-pipeline response differs. Produced water is a separate '
    'excavation-based model and is an engineering estimate, not a published '
    'unit cost.')

# --- what the booth can change --------------------------------------------
SHOW_UNIT_TOGGLE = True
DEFAULT_UNITS = 'SI'                 # 'SI' or 'US'
DEFAULT_CURRENCY = 'CAD'             # 'CAD' or 'USD'
SHOW_DIAGNOSTICS = False

DEFAULT_SUBSTANCE = 'Crude oil'
DEFAULT_TERRAIN = 'Farmland / pasture'
DEFAULT_JURISDICTION = 'Canada'
DEFAULT_FLOW_M3D = 500.0
DEFAULT_REMOTENESS_KM = 5.0

FLOW_RANGE_M3D = (1.0, 50000.0)
REMOTENESS_RANGE_KM = (0.0, 300.0)

# Leak scenarios shown as markers. (label, percent of flow, days running).
# Volume = flow * pct/100 * days, so these move with the pipeline's flow rate.
# (label, leak rate as percent of flow, hours running before it is stopped).
# Volume = flow * pct/100 * hours/24, so both move with the pipeline's flow.
LEAK_SCENARIOS = [
    ('Pinhole', 0.5, 1440.0),
    ('Seep', 1.0, 336.0),
    ('Small leak', 1.5, 72.0),
    ('Large leak', 3.0, 12.0),
    ('Rupture', 10.0, 1.0),
]

SCENARIO_PCT_RANGE = (0.001, 100.0)
SCENARIO_HOURS_RANGE = (0.01, 26280.0)
MAX_SCENARIOS = 10

# Volume span drawn when no scenarios are loaded, as a multiple of daily flow.
NO_SCENARIO_SPAN = (0.001, 10.0)

# How far either side of the scenario span the plotted curve runs.
CURVE_SPAN_DECADES = 1.2

# Familiar volumes marked on the x axis for scale. Cubic metres.
REFERENCE_VOLUMES = [
    ('1 barrel', 0.159),
    ('Tanker truck', 35.0),
    ('Rail car', 110.0),
    ('Olympic pool', 2500.0),
]

# --- fixed model inputs ----------------------------------------------------
# Locked down and invisible to the sales team. Move a key out of this dict and
# into app.py only if you want it exposed at the booth.
MODEL = dict(
    target_year=2026,
    recovery_effectiveness=10,       # Etkin Table 1 mechanical column: 0/10/20/50
    min_event_cost_cad=15000.0,      # mobilisation, assessment, reporting floor
)

# --- economics -------------------------------------------------------------
# Etkin's tables carry no explicit base year. The paper is 2004 and its results
# were stated in 2002 dollars, so 2002 is used here. Set to 2004 if you decide
# otherwise; the difference is about 5 percent.
COST_BASE_YEAR = 2002

# US CPI-U annual averages. Extend this list as new years publish; the model
# interpolates between entries and extrapolates past the end at CPI_FORWARD_RATE.
# 2025 and 2026 are estimates pending final annual averages.
CPI_US = {
    2002: 179.9, 2003: 184.0, 2004: 188.9, 2005: 195.3, 2006: 201.6,
    2007: 207.342, 2008: 215.303, 2009: 214.537, 2010: 218.056,
    2011: 224.939, 2012: 229.594, 2013: 232.957, 2014: 236.736,
    2015: 237.017, 2016: 240.007, 2017: 245.120, 2018: 251.107,
    2019: 255.657, 2020: 258.811, 2021: 270.970, 2022: 292.655,
    2023: 304.702, 2024: 313.689, 2025: 322.4, 2026: 333.5,
}
CPI_FORWARD_RATE = 0.025

USD_TO_CAD = 1.37

# Regional cost-level factors, Etkin (2000) worldwide cleanup cost analysis.
# US response is substantially more expensive than Canadian for the same spill.
JURISDICTION = {
    'United States': 1.00,
    'Canada': 0.25,
    'Europe': 0.18,
    'Asia': 0.10,
}

# Etkin's tables are US-based, so the factor above applies to them directly.
# The produced-water unit rates below are already Canadian, so the salt model
# uses the factor normalised against this reference instead of double counting.
JURISDICTION_REFERENCE = 'Canada'

# Global scale on the final answer. Left at 1.0 until the model is calibrated
# against real incident cost data; this is the hook for that calibration.
CALIBRATION = 1.0

# Remoteness multiplier = min(1 + a*log10(1 + km/k0), cap). Rises quickly over
# the first few km as road access degrades, then saturates once the response is
# flying crews and equipment in and further distance stops mattering much.
REMOTENESS_A = 0.94
REMOTENESS_K0_KM = 5.0
REMOTENESS_CAP = 1.60

# --- Etkin Table 1: per-gallon response cost, USD, mechanical recovery ------
# grade -> effectiveness percent -> [(volume_gal_anchor, cost_per_gal), ...]
# Anchors are the geometric midpoints of Etkin's volume bands, since the
# tabulated value represents the band rather than its edge.
VOLUME_ANCHORS_GAL = [354.0, 707.0, 3162.0, 31623.0, 316228.0, 3162278.0]

RESPONSE_USD_PER_GAL = {
    'light_fuels': {
        0:  [100, 98, 97, 87, 74, 31],
        10: [85, 83, 82, 72, 62, 26],
        20: [70, 68, 67, 59, 49, 17],
        50: [57, 55, 54, 41, 26, 12],
    },
    'heavy_oils': {
        0:  [440, 438, 436, 410, 179, 87],
        10: [386, 385, 384, 359, 154, 77],
        20: [335, 334, 333, 308, 128, 67],
        50: [310, 309, 308, 267, 103, 36],
    },
    'crude_oils': {
        0:  [220, 218, 215, 195, 123, 92],
        10: [199, 197, 195, 185, 118, 82],
        20: [189, 187, 185, 174, 113, 76],
        50: [153, 151, 149, 138, 92, 64],
    },
    # Etkin tabulates volatile distillates for mechanical 10% only. Other
    # effectiveness levels are scaled by the Table 6 adjustment factors.
    'volatile_distillates': {
        10: [103, 102, 100, 55, 23, 7],
    },
}

# Etkin Table 6, mechanical recovery adjustment factors.
EFFECTIVENESS_FACTOR = {0: 1.15, 10: 1.00, 20: 0.85, 50: 0.55}

# --- Etkin Tables 2 and 3: per-gallon damage base costs, USD ---------------
SOCIOECONOMIC_USD_PER_GAL = {
    'volatile_distillates': [65, 265, 400, 180, 90, 70],
    'light_fuels':          [80, 330, 500, 200, 100, 90],
    'heavy_oils':           [150, 600, 900, 500, 200, 175],
    'crude_oils':           [50, 200, 300, 140, 70, 60],
}

ENVIRONMENTAL_USD_PER_GAL = {
    'volatile_distillates': [48, 45, 35, 30, 15, 10],
    'light_fuels':          [85, 80, 70, 65, 30, 25],
    'heavy_oils':           [95, 90, 85, 75, 40, 35],
    'crude_oils':           [90, 87, 80, 73, 35, 30],
}

# --- substance to Etkin grade ---------------------------------------------
# Etkin's own category footnotes: light fuels include light crude and light
# oils; heavy oils include heavy crude, lube oil and tars; crude oils cover
# crude not specifically identified as heavy or light; volatile distillates
# are gasoline, jet fuel, kerosene, No.1 fuel oil and crude condensate.
SUBSTANCE_GRADE = {
    'Crude oil': 'crude_oils',
    'Light crude': 'light_fuels',
    'Heavy crude': 'heavy_oils',
    'Bitumen / dilbit': 'heavy_oils',
    'Condensate': 'volatile_distillates',
    'NGL / HVP liquids': 'volatile_distillates',
    'Refined products (diesel, jet)': 'light_fuels',
    'Produced water': None,          # handled by the salt model below
}

# --- terrain presets -------------------------------------------------------
# Each preset fixes the four Etkin modifier choices so the booth picks one
# thing instead of four. (medium T4, socioeconomic T5, freshwater T7, wildlife T8)
TERRAIN = {
    'Farmland / pasture':      dict(medium=0.7, socio=1.0, freshwater=0.9, wildlife=2.2),
    'Dry grassland / prairie': dict(medium=0.7, socio=1.0, freshwater=0.9, wildlife=0.5),
    'Forest / bush':           dict(medium=0.8, socio=0.7, freshwater=0.9, wildlife=2.9),
    'Taiga / boreal':          dict(medium=0.9, socio=0.7, freshwater=0.9, wildlife=3.0),
    'Muskeg / wetland':        dict(medium=1.6, socio=0.7, freshwater=1.7, wildlife=4.0),
    'Watercourse crossing':    dict(medium=1.0, socio=1.0, freshwater=1.6, wildlife=1.5),
    'Lake / standing water':   dict(medium=1.0, socio=1.0, freshwater=1.6, wildlife=3.8),
    'Residential / developed': dict(medium=0.5, socio=0.7, freshwater=0.9, wildlife=0.7),
    'Industrial site':         dict(medium=0.5, socio=0.3, freshwater=0.4, wildlife=0.4),
    'Tundra':                  dict(medium=1.3, socio=0.7, freshwater=0.9, wildlife=2.5),
}

# --- produced water --------------------------------------------------------
# Etkin has no salt category. Brine cost is driven by the volume of soil that
# has to be excavated and replaced, not by the volume of brine, because
# chloride and sodium migrate and the land stays unusable until the soil is
# removed or leached below the Alberta Tier 1 guideline.
#
# SOIL_PER_BRINE is an engineering estimate: infiltration into pore space plus
# lateral and vertical migration of the salt front. It is the single biggest
# lever in this model and the first thing to calibrate against real incident
# data. Unit rates are 2026 CAD per cubic metre of soil, from current Canadian
# excavate-and-dispose pricing, with the observed economy of scale.
SALT = dict(
    soil_per_brine=10.0,
    unit_cost_cad_per_m3_soil=150.0,
    reference_soil_m3=200.0,
    scale_exponent=-0.215,           # 200 m3 at 150/m3 falling to ~75/m3 at 5000 m3
    consulting_uplift=1.20,          # delineation, oversight, confirmation sampling
    damage_ratio=0.40,               # lost land use, referenced to farmland
    damage_reference_sensitivity=1.55,
    unit_cost_year=2026,
)

# --- plot appearance -------------------------------------------------------
CHART_TITLE = 'Leak Cost Estimate'
CHART_HEIGHT_PX = 640
PLOT_MAX_VH = 58

PLOT_RCPARAMS = {
    'font.size': 13.0,
    'axes.labelsize': 14.0,
    'axes.labelcolor': '#14202B',
    'axes.edgecolor': '#8A9BA6',
    'xtick.labelsize': 12.0,
    'ytick.labelsize': 12.0,
    'xtick.color': '#14202B',
    'ytick.color': '#14202B',
    'text.color': '#14202B',
    'figure.facecolor': 'white',
    'savefig.facecolor': 'white',
    'savefig.dpi': 200.0,
}

# --- interface colours -----------------------------------------------------
INK = '#14202B'
MUTED = '#3F5361'
RULE = '#B9C6CF'
PANEL = '#E3EAEF'
DEEP = '#173F52'
SIGNAL = '#9E5408'

# Chart-only colours. GRID is the plot gridlines, REF the dashed reference
# volume markers. Darken these if the chart is washed out on a bright screen.
GRID = '#AAB9C3'
REF = '#8A9BA6'
