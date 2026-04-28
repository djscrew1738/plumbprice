"""
LLM Agent Orchestrator — Classifies and routes pricing requests.
RULE: Agent classifies and routes. PricingEngine calculates. Never the reverse.

Classification pipeline (in order):
  1. Keyword classifier  — fast, deterministic, always runs first
  2. Hermes LLM          — called when keyword confidence < threshold or no match
  3. Unclassified         — polite fallback if neither resolves a task_code
"""

import re
from typing import NamedTuple, Optional
import structlog

from app.config import settings
from app.services.pricing_engine import pricing_engine, EstimateResult, MaterialItem
from app.services.supplier_service import supplier_service, MATERIAL_ASSEMBLIES
from app.services.labor_engine import get_template, LABOR_TEMPLATES as LABOR_MAP
from app.services.llm_service import llm_service
from app.services.rag_service import rag_service

logger = structlog.get_logger()

# Word-to-digit map for spoken quantities
_WORD_NUMBERS: dict[str, int] = {
    "one": 1, "two": 2, "three": 3, "four": 4, "five": 5,
    "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10,
    "a": 1, "an": 1,
}


def _extract_quantity(msg_lower: str) -> int:
    """Extract a quantity from natural language (e.g. '3 toilets', 'two faucets')."""
    m = re.search(r'\b([2-9]|1[0-9]|20)\b', msg_lower)
    if m:
        return int(m.group(1))
    for word, val in _WORD_NUMBERS.items():
        if re.search(rf'\b{word}\b', msg_lower):
            return val
    return 1


# ─── Input Normalization ──────────────────────────────────────────────────────

# Applied before classification so abbreviations and misspellings resolve cleanly.
_NORMALIZE_PATTERNS: list[tuple[re.Pattern, str]] = [
    (re.compile(r'\bwh\b',                re.I), 'water heater'),
    (re.compile(r'\bft\.?\s*worth\b',     re.I), 'fort worth'),
    (re.compile(r'\bftw\b',               re.I), 'fort worth'),
    (re.compile(r'\bn\.?\s*richland\b',   re.I), 'north richland hills'),
    (re.compile(r'\bN\.?R\.?H\.?\b',      re.I), 'north richland hills'),
    (re.compile(r'\bno\s+hot\s+water\b',  re.I), 'water heater repair'),
    (re.compile(r'\bhot\s+water\s+out\b', re.I), 'water heater repair'),
    (re.compile(r'\bwon\'?t\s+flush\b',   re.I), 'toilet clogged'),
    (re.compile(r'\bbacked?\s*up\b',      re.I), 'clogged drain'),
    (re.compile(r'\bback\s*flow\b',       re.I), 'backflow'),
    (re.compile(r'\bdripp?ing\b',         re.I), 'leaking repair'),
    (re.compile(r'\bnot\s+working\b',     re.I), 'repair'),
    (re.compile(r'\bbroken\b',            re.I), 'repair'),
    (re.compile(r'\bout\s+of\s+service\b',re.I), 'repair'),
    (re.compile(r'\bno\s+water\b',        re.I), 'water main repair'),
    (re.compile(r'\bwater\s+is\s+off\b',  re.I), 'water main repair'),
    (re.compile(r'\binstant\s+hot\b',     re.I), 'tankless water heater'),
    (re.compile(r'\bpoly\s*b\b',          re.I), 'polybutylene repipe'),
    (re.compile(r'\bgalv\b',              re.I), 'galvanized repipe'),
]


def _normalize(message: str) -> str:
    """Apply abbreviation/alias normalization before classification."""
    result = message
    for pattern, replacement in _NORMALIZE_PATTERNS:
        result = pattern.sub(replacement, result)
    return result


_TEMPLATE_TOKEN_RE = re.compile(r"[a-z0-9]+")
_TEMPLATE_MATCH_STOPWORDS = {
    "a", "an", "and", "bathroom", "bid", "building", "by", "cost", "estimate",
    "for", "from", "help", "how", "in", "install", "installed", "job", "line",
    "me", "my", "need", "new", "of", "on", "per", "plumber", "plumbing",
    "price", "quote", "repair", "replace", "replacement", "service", "set",
    "the", "to", "unit", "with",
}


def _tokenize_template_match(text: str) -> set[str]:
    tokens = {
        token
        for token in _TEMPLATE_TOKEN_RE.findall(text.lower())
        if len(token) > 1 and token not in _TEMPLATE_MATCH_STOPWORDS
    }
    if "restroom" in tokens:
        tokens.add("bath")
    return tokens


class _TemplateSearchEntry(NamedTuple):
    code_phrase: str
    core_tokens: set[str]
    note_tokens: set[str]


def _build_template_search_index() -> dict[str, _TemplateSearchEntry]:
    index: dict[str, _TemplateSearchEntry] = {}
    for code, template in LABOR_MAP.items():
        code_phrase = code.replace("_", " ").lower()
        core_tokens = _tokenize_template_match(f"{code_phrase} {template.name}")
        note_tokens = _tokenize_template_match(template.notes or "")
        index[code] = _TemplateSearchEntry(
            code_phrase=code_phrase,
            core_tokens=core_tokens,
            note_tokens=note_tokens,
        )
    return index


_TEMPLATE_SEARCH_INDEX = _build_template_search_index()


# ─── Job Classification ───────────────────────────────────────────────────────

TASK_KEYWORDS: dict[str, dict] = {
    "TOILET_REPLACE_STANDARD": {
        "keywords": ["toilet", "commode", "throne", "water closet"],
        "keywords_exact": ["wc"],          # requires word boundary
        "actions": ["replace", "install", "swap", "new", "fix"],
        "assembly": "TOILET_INSTALL_KIT",
        "default_access": "first_floor",
        "priority": 2,
    },
    "TOILET_COMFORT_HEIGHT": {
        "keywords": ["comfort height", "ada toilet", "tall toilet", "elongated comfort"],
        "actions": ["replace", "install"],
        "assembly": "TOILET_INSTALL_KIT",
        "default_access": "first_floor",
    },
    "WH_50G_GAS_STANDARD": {
        "keywords": ["water heater", "hot water heater", "50 gallon", "50g", "gas water heater"],
        "actions": ["replace", "install", "new", "swap"],
        "assembly": "WH_50G_GAS_KIT",
        "default_access": "first_floor",
        "priority": 2,
    },
    "WH_50G_GAS_ATTIC": {
        "keywords": ["water heater", "hot water heater"],
        "access_required": "attic",
        "assembly": "WH_50G_GAS_ATTIC_KIT",
        "default_access": "attic",
        "priority": 1,
    },
    "WH_40G_GAS_STANDARD": {
        "keywords": ["40 gallon", "40g", "water heater"],
        "actions": ["replace", "install"],
        "assembly": "WH_40G_GAS_KIT",
        "default_access": "first_floor",
        "priority": 1,
    },
    "WH_50G_ELECTRIC_STANDARD": {
        "keywords": ["electric water heater", "electric wh"],
        "actions": ["replace", "install"],
        "assembly": "WH_50G_ELECTRIC_KIT",
        "default_access": "first_floor",
        "priority": 1,
    },
    "WH_TANKLESS_GAS": {
        "keywords": ["tankless", "on demand", "instantaneous", "combi"],
        "actions": ["install", "replace"],
        "assembly": "WH_TANKLESS_GAS_KIT",
        "default_access": "first_floor",
        "priority": 1,
    },
    "PRV_REPLACE": {
        "keywords": ["prv", "pressure reducing valve", "pressure regulator", "pressure reducer"],
        "actions": ["replace", "install", "fix"],
        "assembly": "PRV_KIT",
        "default_access": "first_floor",
        "priority": 2,
    },
    "HOSE_BIB_REPLACE": {
        "keywords": ["hose bib", "hose bibb", "outdoor faucet", "sillcock", "outside faucet", "exterior faucet"],
        "actions": ["replace", "install", "fix", "repair"],
        "assembly": "HOSE_BIB_KIT",
        "default_access": "first_floor",
        "priority": 2,
    },
    "SHOWER_VALVE_REPLACE": {
        "keywords": ["shower valve", "shower cartridge", "shower mixing valve", "shower faucet", "shower control"],
        "actions": ["replace", "install", "fix", "repair"],
        "assembly": "SHOWER_VALVE_KIT",
        "default_access": "first_floor",
        "priority": 2,
    },
    "KITCHEN_FAUCET_REPLACE": {
        "keywords": ["kitchen faucet", "kitchen sink faucet", "kitchen tap", "kitchen sink"],
        "actions": ["replace", "install", "swap"],
        "assembly": "KITCHEN_FAUCET_KIT",
        "default_access": "first_floor",
        "priority": 2,
    },
    "GARBAGE_DISPOSAL_INSTALL": {
        "keywords": ["disposal", "garbage disposal", "insinkerator", "food disposal", "garburator", "garbage grinder"],
        "actions": ["install", "replace", "swap"],
        "assembly": "DISPOSAL_KIT",
        "default_access": "first_floor",
        "priority": 2,
    },
    "LAV_FAUCET_REPLACE": {
        "keywords": ["bathroom faucet", "lavatory faucet", "lav faucet", "sink faucet", "bath faucet", "vanity faucet"],
        "actions": ["replace", "install", "swap"],
        "assembly": "LAV_FAUCET_KIT",
        "default_access": "first_floor",
        "priority": 2,
    },
    "ANGLE_STOP_REPLACE": {
        "keywords": ["angle stop", "shutoff valve", "shut off valve", "stop valve", "angle valve", "supply valve"],
        "actions": ["replace", "install", "fix"],
        "assembly": "ANGLE_STOP_KIT",
        "default_access": "first_floor",
        "priority": 2,
    },
    "PTRAP_REPLACE": {
        "keywords": ["p-trap", "ptrap", "p trap", "drain trap", "s-trap"],
        "actions": ["replace", "install", "fix"],
        "assembly": "PTRAP_KIT",
        "default_access": "first_floor",
        "priority": 2,
    },
    "TOILET_FLAPPER_REPLACE": {
        "keywords": ["flapper", "running toilet", "toilet running", "toilet won't stop", "toilet keeps running",
                     "toilet runs", "phantom flush", "ghost flush", "water wasting toilet", "toilet won't stop"],
        "actions": ["replace", "fix", "repair", "stop"],
        "assembly": "TOILET_FLAPPER_KIT",
        "default_access": "first_floor",
        "priority": 1,
    },
    "TOILET_FILL_VALVE_REPLACE": {
        "keywords": ["fill valve", "toilet fill", "ballcock", "toilet hissing", "hissing toilet",
                     "toilet constantly filling", "toilet tank slow"],
        "actions": ["replace", "fix", "repair"],
        "assembly": "TOILET_FILL_VALVE_KIT",
        "default_access": "first_floor",
        "priority": 1,
    },
    "TOILET_COMFORT_HEIGHT": {
        "keywords": ["comfort height", "ada toilet", "tall toilet", "elongated comfort", "raised toilet",
                     "accessibility toilet", "handicap toilet", "ada compliant toilet"],
        "actions": ["replace", "install", "swap"],
        "assembly": "TOILET_COMFORT_HEIGHT_KIT",
        "default_access": "first_floor",
        "priority": 1,
    },
    "TUB_SPOUT_REPLACE": {
        "keywords": ["tub spout", "bathtub spout", "tub faucet spout", "spout replace", "tub dripping spout"],
        "actions": ["replace", "install", "fix"],
        "assembly": "TUB_SPOUT_KIT",
        "default_access": "first_floor",
        "priority": 2,
    },
    "SHOWER_HEAD_REPLACE": {
        "keywords": ["shower head", "showerhead", "shower nozzle", "rain head", "handheld shower", "rain shower"],
        "actions": ["replace", "install", "upgrade", "swap"],
        "assembly": "SHOWER_HEAD_KIT",
        "default_access": "first_floor",
        "priority": 2,
    },
    "LAV_SINK_REPLACE": {
        "keywords": ["bathroom sink", "lav sink", "vanity sink", "lavatory sink", "sink replace",
                     "pedestal sink", "undermount sink"],
        "actions": ["replace", "install", "swap"],
        "assembly": "LAV_SINK_KIT",
        "default_access": "first_floor",
        "priority": 2,
    },
    "GAS_SHUTOFF_REPLACE": {
        "keywords": ["gas shutoff", "gas shut off", "gas valve", "appliance shutoff", "gas cock", "gas ball valve"],
        "actions": ["replace", "install", "fix"],
        "assembly": "GAS_SHUTOFF_KIT",
        "default_access": "first_floor",
        "priority": 2,
    },
    "CLEAN_OUT_INSTALL": {
        "keywords": ["clean out install", "add clean out", "cleanout install", "need a clean out",
                     "no clean out", "add cleanout", "install cleanout"],
        "actions": ["install", "add", "cut in"],
        "assembly": "CLEAN_OUT_KIT",
        "default_access": "first_floor",
        "priority": 2,
    },
    "CAMERA_INSPECTION": {
        "keywords": ["camera inspection", "camera line", "video inspection", "scope the line", "sewer camera",
                     "drain camera", "scope drain", "pipe inspection", "line inspection"],
        "actions": ["inspect", "scope", "camera"],
        "assembly": None,
        "default_access": "first_floor",
        "priority": 1,
    },
    "HYDROJETTING": {
        "keywords": ["hydro jet", "hydrojet", "hydrojetting", "jetting", "high pressure clean", "water jet drain",
                     "high pressure drain", "hydro jetting"],
        "actions": ["jet", "clean", "clear"],
        "assembly": None,
        "default_access": "first_floor",
        "priority": 1,
    },
    "MAIN_LINE_CLEAN": {
        "keywords": ["main line", "main drain", "sewer line clean", "main sewer", "rooter", "root intrusion"],
        "actions": ["clean", "clear", "snake", "rooter"],
        "assembly": None,
        "default_access": "first_floor",
        "priority": 2,
    },
    "DRAIN_CLEAN_STANDARD": {
        "keywords": ["drain clean", "clogged drain", "slow drain", "drain snake", "sink clog", "tub clog",
                     "shower drain clog", "blocked drain", "drain backup", "clogged sink", "clogged tub",
                     "clogged shower", "drain backup"],
        "actions": ["clean", "unclog", "clear", "snake", "flush"],
        "assembly": None,
        "default_access": "first_floor",
        "priority": 3,
    },
    "SLAB_LEAK_REPAIR": {
        "keywords": ["slab leak", "under slab", "foundation leak", "concrete leak", "slab pipe", "under foundation"],
        "actions": ["repair", "fix", "locate", "reroute"],
        "assembly": None,
        "default_access": "slab",
        "priority": 1,
    },
    "LEAK_DETECTION": {
        "keywords": ["leak detection", "find the leak", "locate leak", "leak locate", "water leak find",
                     "detect leak", "find my leak", "where is the leak"],
        "actions": ["detect", "find", "locate"],
        "assembly": None,
        "default_access": "first_floor",
        "priority": 1,
    },
    "WATER_SOFTENER_INSTALL": {
        "keywords": ["water softener", "softener", "water conditioner", "salt system", "ion exchange",
                     "water treatment", "hard water system"],
        "actions": ["install", "replace", "add"],
        "assembly": "WATER_SOFTENER_KIT",
        "default_access": "first_floor",
        "priority": 2,
    },
    "TUB_SHOWER_COMBO_REPLACE": {
        "keywords": ["tub faucet", "tub valve", "bathtub faucet", "tub shower valve", "bath valve",
                     "tub diverter", "roman tub", "bathtub valve"],
        "actions": ["replace", "install", "fix", "repair"],
        "assembly": "TUB_SHOWER_VALVE_KIT",
        "default_access": "first_floor",
        "priority": 2,
    },
    "EXPANSION_TANK_ONLY": {
        "keywords": ["expansion tank", "thermal expansion", "expansion vessel", "thermal expansion tank"],
        "actions": ["add", "install", "replace"],
        "assembly": "EXPANSION_TANK_KIT",
        "default_access": "first_floor",
        "priority": 2,
    },
    "GAS_LINE_REPAIR_MINOR": {
        "keywords": ["gas line repair", "gas leak", "gas fitting", "gas valve repair", "gas line fix"],
        "actions": ["repair", "fix", "replace"],
        "assembly": None,
        "default_access": "first_floor",
        "priority": 2,
    },
    "GAS_LINE_NEW_RUN": {
        "keywords": ["new gas line", "gas line run", "gas line install", "add gas line", "gas connection",
                     "run gas", "extend gas"],
        "actions": ["install", "run", "add"],
        "assembly": None,
        "default_access": "first_floor",
        "priority": 1,
    },
    "WHOLE_HOUSE_REPIPE_PEX": {
        "keywords": [
            "repipe", "whole house repipe", "re-pipe", "reline", "galvanized pipe",
            "galvanized repipe", "polybutylene", "poly-b", "pex repipe",
            "replumb", "whole house replumb", "replace all pipes", "repipe the house",
        ],
        "actions": ["repipe", "replace", "replumb", "install", "reline"],
        "assembly": "WHOLE_HOUSE_REPIPE_PEX_KIT",
        "default_access": "first_floor",
        "priority": 1,
    },
    "SEWER_SPOT_REPAIR": {
        "keywords": [
            "sewer repair", "sewer line repair", "sewer spot repair", "broken sewer",
            "cracked sewer", "sewer cave in", "belly in sewer", "bellied pipe",
            "sewer roots", "sewer collapse", "collapsed sewer",
            "sewer line replacement", "excavate sewer", "dig sewer",
        ],
        "actions": ["repair", "replace", "dig", "excavate", "fix"],
        "assembly": "SEWER_SPOT_KIT",
        "default_access": "first_floor",
        "priority": 1,
    },
    "RECIRC_PUMP_INSTALL": {
        "keywords": [
            "recirculation pump", "recirc pump", "recirculating pump",
            "instant hot water pump", "hot water recirculation", "hot water pump",
            "recirculating hot water", "comfort pump", "grundfos pump",
        ],
        "actions": ["install", "add", "replace", "hook up"],
        "assembly": "RECIRC_PUMP_KIT",
        "default_access": "first_floor",
        "priority": 2,
    },
    "DISHWASHER_HOOKUP": {
        "keywords": [
            "dishwasher", "dish washer", "dishwasher hookup", "dishwasher install",
            "dishwasher connection", "dishwasher supply", "dishwasher drain",
            "appliance hookup", "appliance install",
        ],
        "actions": ["install", "hook up", "connect", "hookup", "replace"],
        "assembly": "DISHWASHER_KIT",
        "default_access": "first_floor",
        "priority": 2,
    },
    "WATER_MAIN_REPAIR": {
        "keywords": [
            "main shutoff", "main valve", "main water shutoff", "water main",
            "main line shutoff", "whole house shutoff",
            "main water valve", "water main repair", "main line repair",
            "meter shutoff", "angle stop main",
            "burst pipe", "pipe burst", "broken pipe", "pipe break",
        ],
        "actions": ["repair", "replace", "fix", "install"],
        "assembly": "WATER_MAIN_KIT",
        "default_access": "first_floor",
        "priority": 1,
    },
    "BACKFLOW_PREVENTER_INSTALL": {
        "keywords": [
            "backflow preventer", "backflow prevention", "backflow device",
            "backflow", "check valve install", "rp backflow", "double check valve",
            "backflow test", "backflow certification",
        ],
        "actions": ["install", "replace", "test", "certify"],
        "assembly": None,
        "default_access": "first_floor",
        "priority": 1,
    },
    "WATER_FILTER_WHOLE_HOUSE": {
        "keywords": [
            "whole house filter", "whole home filter", "water filter system",
            "water filtration", "carbon filter", "sediment filter", "iron filter",
            "whole house water filter", "inline filter", "under sink filter",
        ],
        "actions": ["install", "replace", "add"],
        "assembly": None,
        "default_access": "first_floor",
        "priority": 2,
    },

    # ─── Water Heater Repair (not replacement) ────────────────────────────────
    "WH_REPAIR_GAS": {
        "keywords": [
            "water heater not heating", "no hot water", "hot water out",
            "pilot light out", "pilot won't light", "pilot light",
            "thermocouple", "gas valve on water heater", "water heater making noise",
            "water heater rumbling", "water heater leaking around base",
            "tp valve dripping", "t&p valve", "temperature pressure relief",
        ],
        "actions": ["repair", "fix", "replace", "relight", "check"],
        "assembly": "WH_REPAIR_GAS_KIT",
        "default_access": "first_floor",
        "priority": 0,  # must match before generic WH replace keywords
    },
    "WH_ELEMENT_REPLACE": {
        "keywords": [
            "electric water heater not working", "electric water heater cold",
            "heating element", "wh element", "water heater element",
            "electric hot water not working",
        ],
        "actions": ["replace", "fix", "repair"],
        "assembly": "WH_ELEMENT_KIT",
        "default_access": "first_floor",
        "priority": 0,
    },
    "WH_FLUSH_MAINTENANCE": {
        "keywords": [
            "flush water heater", "flush the tank", "drain water heater",
            "descale water heater", "water heater maintenance", "annual flush",
            "sediment flush",
        ],
        "actions": ["flush", "drain", "descale", "service", "maintain"],
        "assembly": None,
        "default_access": "first_floor",
        "priority": 1,
    },
    "WH_ANODE_REPLACE": {
        "keywords": [
            "anode rod", "anode rod water heater", "replace anode",
            "anode replacement", "magnesium anode", "sacrificial anode",
        ],
        "actions": ["replace", "change", "install"],
        "assembly": "ANODE_ROD_KIT",
        "default_access": "first_floor",
        "priority": 0,
    },

    # ─── Toilet Repairs (not replacement) ─────────────────────────────────────
    "TOILET_TANK_REBUILD": {
        "keywords": [
            "toilet running", "toilet keeps running", "phantom flush",
            "toilet won't stop running", "toilet runs constantly",
            "toilet tank rebuild", "rebuild toilet tank",
            "fill valve", "flapper replacement", "toilet flapper",
        ],
        "actions": ["fix", "repair", "rebuild", "replace"],
        "assembly": "TOILET_REBUILD_KIT",
        "default_access": "first_floor",
        "priority": 0,  # before TOILET_REPLACE_STANDARD
    },
    "TOILET_SEAT_REPLACE": {
        "keywords": [
            "toilet seat", "broken toilet seat", "cracked toilet seat",
            "new toilet seat", "replace toilet seat", "toilet seat broken",
        ],
        "actions": ["replace", "install", "change", "fix"],
        "assembly": "TOILET_SEAT_KIT",
        "default_access": "first_floor",
        "priority": 0,
    },
    "TOILET_WAX_RING_ONLY": {
        "keywords": [
            "wax ring", "toilet seal", "toilet leaking at base", "toilet rocking",
            "toilet leaking floor", "toilet base leaking", "toilet wobbly",
            "toilet wax seal", "toilet leaking at the base",
            "water around toilet", "water at base of toilet",
            "toilet leaking around base",
        ],
        "actions": ["replace", "fix", "repair", "reseat", "reset"],
        "assembly": "WAX_RING_RESET_KIT",
        "default_access": "first_floor",
        "priority": 0,
    },

    # ─── Faucet Cartridge ──────────────────────────────────────────────────────
    "FAUCET_CARTRIDGE_REPAIR": {
        "keywords": [
            "faucet cartridge", "cartridge replacement", "faucet dripping",
            "leaking faucet", "dripping faucet", "faucet leaks when off",
            "faucet not shutting off", "hard to turn faucet", "stiff faucet",
            # normalized forms (_normalize turns "dripping" → "leaking repair"):
            "faucet leaking repair", "faucet leaking",
        ],
        "actions": ["replace", "fix", "repair", "change"],
        "assembly": "CARTRIDGE_KIT",
        "default_access": "first_floor",
        "priority": 0,  # before FAUCET_REPLACE_KITCHEN
    },

    # ─── Slab Leak Reroute ─────────────────────────────────────────────────────
    "SLAB_LEAK_REROUTE": {
        "keywords": [
            "slab leak reroute", "reroute slab", "bypass slab leak",
            "attic reroute", "run new line attic", "pipe in attic bypass",
            "reroute through attic", "reroute plumbing",
        ],
        "actions": ["reroute", "bypass", "run", "install", "fix"],
        "assembly": "SLAB_REROUTE_KIT",
        "default_access": "slab",
        "priority": 0,
    },

    # ─── Backflow Test ─────────────────────────────────────────────────────────
    "BACKFLOW_TEST_ANNUAL": {
        "keywords": [
            "backflow test", "backflow certification", "annual backflow",
            "backflow tester", "rpt certification", "backflow preventer test",
            "backflow inspection",
        ],
        "actions": ["test", "certify", "inspect", "check"],
        "assembly": None,
        "default_access": "first_floor",
        "priority": 0,
    },

    # ─── Gas Pressure Test ─────────────────────────────────────────────────────
    "GAS_PRESSURE_TEST": {
        "keywords": [
            "gas pressure test", "gas line test", "pressure test gas",
            "gas test for permit", "gas hold test", "gas leak test",
        ],
        "actions": ["test", "pressure", "check", "inspect"],
        "assembly": None,
        "default_access": "first_floor",
        "priority": 0,
    },

    # ─── Water Supply Line Repair ──────────────────────────────────────────────
    "WATER_LINE_REPAIR_MINOR": {
        "keywords": [
            "pinhole leak", "pin hole leak", "small leak supply line",
            "supply line leak", "water line leak", "pipe joint leak",
            "compression fitting leak", "copper pipe leak",
        ],
        "actions": ["repair", "fix", "patch", "replace"],
        "assembly": "WATER_LINE_REPAIR_KIT",
        "default_access": "first_floor",
        "priority": 0,
    },

    # ─── Outdoor Drain ─────────────────────────────────────────────────────────
    "OUTDOOR_DRAIN_INSTALL": {
        "keywords": [
            "french drain", "yard drain", "outdoor drain", "landscape drain",
            "drainage problem", "standing water yard", "soggy yard",
            "yard flooding", "surface drainage", "downspout drain",
        ],
        "actions": ["install", "add", "fix", "solve", "create"],
        "assembly": "OUTDOOR_DRAIN_KIT",
        "default_access": "first_floor",
        "priority": 1,
    },

    "DRAIN_CLEAN_KITCHEN": {
        "keywords": [
            "kitchen drain", "kitchen sink clogged", "kitchen sink backed up",
            "grease clog", "kitchen grease drain", "kitchen drain slow",
            "garbage disposal drain", "kitchen drain backed",
        ],
        "actions": ["clean", "unclog", "clear", "fix"],
        "assembly": None,
        "default_access": "first_floor",
        "priority": 0,
    },
    "DRAIN_CLEAN_BATHTUB": {
        "keywords": [
            "bathtub drain", "tub drain clogged", "tub won't drain",
            "bathtub slow drain", "tub clogged", "bath drain",
            "tub drains slow",
        ],
        "actions": ["clean", "unclog", "clear", "fix"],
        "assembly": None,
        "default_access": "first_floor",
        "priority": 0,
    },
    "DRAIN_CLEAN_SHOWER": {
        "keywords": [
            "shower drain", "shower clogged", "shower won't drain",
            "shower drain slow", "shower backup", "shower drain backed",
        ],
        "actions": ["clean", "unclog", "clear", "fix"],
        "assembly": None,
        "default_access": "first_floor",
        "priority": 0,
    },
    "TOILET_AUGER_SERVICE": {
        "keywords": [
            "toilet clogged", "toilet won't flush", "toilet backup",
            "toilet auger", "closet snake", "toilet not flushing",
            "toilet stopped up", "toilet overflow",
        ],
        "actions": ["unclog", "clear", "fix", "snake", "auger"],
        "assembly": None,
        "default_access": "first_floor",
        "priority": 0,
    },
    "TANKLESS_WH_DESCALE": {
        "keywords": [
            "tankless water heater descale", "descale tankless",
            "flush tankless water heater", "tankless maintenance",
            "tankless annual service", "tankless scale",
        ],
        "actions": ["descale", "flush", "service", "clean", "maintain"],
        "assembly": "TANKLESS_DESCALE_KIT",
        "default_access": "first_floor",
        "priority": 0,
    },
    "EXPANSION_TANK_INSTALL": {
        "keywords": [
            "expansion tank", "thermal expansion", "expansion tank water heater",
            "closed system expansion", "wh expansion tank",
        ],
        "actions": ["install", "add", "replace"],
        "assembly": "EXPANSION_TANK_KIT",
        "default_access": "first_floor",
        "priority": 1,
    },
    "WATER_HAMMER_ARRESTER": {
        "keywords": [
            "water hammer", "banging pipes", "pipes banging", "pipes knocking",
            "loud pipes", "hammer arrester", "water hammer arrester",
            "pipes make noise",
        ],
        "actions": ["fix", "install", "repair", "stop"],
        "assembly": "HAMMER_ARRESTER_KIT",
        "default_access": "first_floor",
        "priority": 1,
    },
    "LAUNDRY_BOX_REPLACE": {
        "keywords": [
            "laundry box", "washer box", "washing machine box",
            "laundry outlet box", "washer outlet", "washing machine valves",
            "laundry valves", "washer hookup valves",
        ],
        "actions": ["replace", "install", "fix", "repair"],
        "assembly": "LAUNDRY_BOX_KIT",
        "default_access": "first_floor",
        "priority": 1,
    },
    "ICE_MAKER_LINE_INSTALL": {
        "keywords": [
            "ice maker line", "refrigerator water line", "fridge water line",
            "ice maker hookup", "ice maker install", "refrigerator ice maker",
        ],
        "actions": ["install", "run", "hookup", "connect"],
        "assembly": "ICE_MAKER_KIT",
        "default_access": "first_floor",
        "priority": 1,
    },
    "MIXING_VALVE_REPLACE": {
        "keywords": [
            "mixing valve", "thermostatic mixing valve", "tempering valve",
            "anti-scald valve", "water too hot", "scald prevention",
        ],
        "actions": ["replace", "install", "fix", "adjust"],
        "assembly": "MIXING_VALVE_KIT",
        "default_access": "first_floor",
        "priority": 1,
    },
    "SHOWER_VALVE_CARTRIDGE": {
        "keywords": [
            "shower valve cartridge", "shower cartridge", "tub valve cartridge",
            "shower dripping", "shower leaking", "tub faucet dripping",
            "shower won't turn off", "shower hard to turn",
            "moen cartridge", "delta monitor cartridge",
        ],
        "actions": ["replace", "fix", "repair"],
        "assembly": "SHOWER_CARTRIDGE_KIT",
        "default_access": "first_floor",
        "priority": 0,
    },
    "BATHTUB_DRAIN_REPAIR": {
        "keywords": [
            "bathtub drain repair", "tub drain broken", "trip lever broken",
            "tub stopper broken", "bathtub won't hold water",
            "tub drain assembly", "overflow plate",
        ],
        "actions": ["repair", "replace", "fix"],
        "assembly": "TUB_DRAIN_KIT",
        "default_access": "first_floor",
        "priority": 0,
    },
    "SINK_REPLACE_KITCHEN": {
        "keywords": [
            "kitchen sink replacement", "replace kitchen sink",
            "new kitchen sink", "install kitchen sink",
            "kitchen sink cracked", "kitchen sink leaking",
        ],
        "actions": ["replace", "install", "new"],
        "assembly": "KITCHEN_SINK_KIT",
        "default_access": "first_floor",
        "priority": 0,
    },
    "SINK_REPLACE_BATH": {
        "keywords": [
            "bathroom sink replacement", "replace bathroom sink",
            "vanity sink", "pedestal sink", "new bathroom sink",
            "lavatory replacement",
        ],
        "actions": ["replace", "install", "new"],
        "assembly": "BATH_SINK_KIT",
        "default_access": "first_floor",
        "priority": 0,
    },
    "GARBAGE_DISPOSAL_REPAIR": {
        "keywords": [
            "garbage disposal not working", "disposal jammed",
            "disposal humming", "disposal won't turn on",
            "reset disposal", "disposal repair",
        ],
        "actions": ["fix", "repair", "reset", "clear"],
        "assembly": None,
        "default_access": "first_floor",
        "priority": 0,
    },
    "HOSE_BIB_FREEZE_REPAIR": {
        "keywords": [
            "frozen hose bib", "burst hose bib", "hose bib frozen",
            "sillcock frozen", "outdoor faucet frozen",
            "hose bib burst", "freeze damage outside faucet",
        ],
        "actions": ["repair", "replace", "fix"],
        "assembly": "HOSE_BIB_FREEZE_KIT",
        "default_access": "first_floor",
        "priority": 0,
    },
    "PRESSURE_TEST_SYSTEM": {
        "keywords": [
            "pressure test", "pressure test plumbing",
            "whole house pressure test", "system pressure test",
            "plumbing pressure check",
        ],
        "actions": ["test", "check", "inspect"],
        "assembly": None,
        "default_access": "first_floor",
        "priority": 1,
    },
    "LAUNDRY_DRAIN_INSTALL": {
        "keywords": [
            "laundry drain", "standpipe install", "washer drain",
            "laundry room drain", "washing machine drain install",
            "laundry standpipe",
        ],
        "actions": ["install", "add", "run"],
        "assembly": None,
        "default_access": "first_floor",
        "priority": 1,
    },
    "SUMP_PUMP_INSTALL": {
        "keywords": [
            "sump pump", "sump pit", "submersible pump",
            "basement pump", "crawl space pump",
            "install sump pump", "sump pump replace",
        ],
        "actions": ["install", "replace", "add"],
        "assembly": "SUMP_PUMP_KIT",
        "default_access": "crawlspace",
        "priority": 1,
    },
    "SHOWER_PAN_REPLACE": {
        "keywords": [
            "shower pan", "shower base", "shower floor cracked",
            "shower pan leaking", "replace shower pan",
            "shower base cracked", "shower floor leaking",
        ],
        "actions": ["replace", "install", "fix"],
        "assembly": None,
        "default_access": "first_floor",
        "priority": 1,
    },

}

ACCESS_KEYWORDS = {
    "attic":        ["attic", "in the attic", "attic install", "attic unit"],
    "second_floor": ["second floor", "2nd floor", "upstairs", "second story", "2nd story", "upper floor"],
    "crawlspace":   ["crawl space", "crawlspace", "under the house", "crawl", "under house"],
    "slab":         ["slab", "slab foundation", "in the slab", "under slab", "under concrete", "concrete slab"],
    "basement":     ["basement", "below grade"],
    "first_floor":  ["first floor", "1st floor", "ground floor", "downstairs", "main floor"],
}

URGENCY_KEYWORDS = {
    "emergency": [
        "emergency", "urgent", "asap", "right now", "immediately", "tonight",
        "flooding", "flood", "burst pipe", "burst", "gushing", "water everywhere",
        "pipe burst", "major leak", "water pouring", "no water", "water off",
        "can't use", "cant use", "off right now", "after hours",
    ],
    "same_day": ["same day", "today", "this afternoon", "this morning", "this evening", "few hours"],
    "standard": [],
}

COUNTY_KEYWORDS: dict[str, list[str]] = {
    "dallas": [
        "dallas", "highland park", "university park", "desoto", "duncanville",
        "garland", "mesquite", "richardson", "rowlett", "balch springs",
        "cedar hill", "grand prairie", "irving", "lancaster", "seagoville",
        "farmers branch", "addison", "coppell", "glenn heights", "hutchins",
        "wilmer", "sunnyvale", "sachse", "cockrell hill", "highland hills",
    ],
    "tarrant": [
        "fort worth", "arlington", "mansfield", "burleson", "hurst",
        "bedford", "euless", "grapevine", "north richland hills",
        "southlake", "westlake", "colleyville", "keller", "trophy club",
        "watauga", "richland hills", "saginaw", "white settlement",
        "benbrook", "crowley", "lake worth", "river oaks", "sansom park",
        "haltom city", "forest hill", "everman", "kennedale", "pantego",
        "dalworthington", "rendon", "edgecliff",
    ],
    "collin": [
        "plano", "mckinney", "frisco", "allen", "prosper", "celina",
        "wylie", "murphy", "fairview", "anna", "blue ridge", "nevada",
        "parker", "lucas", "new hope", "melissa", "van alstyne", "Princeton",
        "lavon", "lowry crossing", "weston", "Westminster",
    ],
    "denton": [
        "denton", "lewisville", "flower mound", "carrollton",
        "the colony", "little elm", "corinth", "lake dallas", "highland village",
        "argyle", "aubrey", "northlake", "justin", "roanoke", "haslet",
        "bartonville", "double oak", "lantana", "hickory creek", "shady shores",
        "krugerville", "ponder", "pilot point",
    ],
    "rockwall": ["rockwall", "heath", "fate", "mclendon-chisholm", "royse city"],
    "parker":   ["weatherford", "aledo", "willow park", "azle", "springtown", "mineral wells"],
    "kaufman":  ["kaufman", "forney", "terrell", "seagoville", "balch springs", "combine"],
    "ellis":    [
        "waxahachie", "midlothian", "red oak", "ennis", "italy", "milford",
        "palmer", "glen heights", "glenn heights", "ovilla",
    ],
    "johnson":  [
        "cleburne", "burleson", "joshua", "alvarado", "keene",
        "venus", "grandview", "godley", "crowley",
    ],
}


def _default_assembly_for_task(task_code: Optional[str]) -> Optional[str]:
    if not task_code:
        return None

    keyword_cfg = TASK_KEYWORDS.get(task_code)
    if keyword_cfg and keyword_cfg.get("assembly"):
        return keyword_cfg["assembly"]

    template = LABOR_MAP.get(task_code)
    if template and template.applicable_assemblies:
        return template.applicable_assemblies[0]

    return None


def _classify_from_template_catalog(msg_lower: str) -> Optional[tuple[str, Optional[str], float]]:
    msg_tokens = _tokenize_template_match(msg_lower)
    if not msg_tokens:
        return None

    best_task: Optional[str] = None
    best_assembly: Optional[str] = None
    best_score = 0.0

    for code, search in _TEMPLATE_SEARCH_INDEX.items():
        core_tokens = search.core_tokens
        note_tokens = search.note_tokens
        if not core_tokens:
            continue

        core_overlap = msg_tokens & core_tokens
        if not core_overlap:
            continue

        score = len(core_overlap) * 2.0
        score += len(msg_tokens & note_tokens) * 0.25

        code_phrase = search.code_phrase
        if code_phrase in msg_lower:
            score += 3.0

        if len(core_overlap) >= min(2, len(core_tokens)):
            score += 1.0

        if score > best_score:
            best_score = score
            best_task = code
            best_assembly = _default_assembly_for_task(code)

    if not best_task or best_score < 4.0:
        return None

    confidence = min(0.74 + max(0.0, best_score - 4.0) * 0.03, 0.88)
    return best_task, best_assembly, confidence


def classify_request(message: str) -> dict:
    """
    Rule-based classification of plumbing service request.

    Pipeline:
      1. Normalize input (abbreviations, common phrases)
      2. Detect urgency, access type
      3. Detect county via city/keyword lookup (city infers county)
      4. Disambiguation: clog+toilet → drain, not toilet replace
      5. Priority-ordered task matching (lower number = higher priority)
      6. Confidence scoring with keyword specificity + action match

    Returns: {task_code, assembly_code, access_type, urgency, county, city,
              preferred_supplier, confidence, quantity, raw_message}
    """
    raw_message = message
    msg_norm  = _normalize(message)
    msg_lower = msg_norm.lower()

    # ── 1. Urgency ────────────────────────────────────────────────────────────
    urgency = "standard"
    for urg, keywords in URGENCY_KEYWORDS.items():
        if any(kw in msg_lower for kw in keywords):
            urgency = urg
            break

    # ── 2. Access type ────────────────────────────────────────────────────────
    access_type = "first_floor"
    for access, keywords in ACCESS_KEYWORDS.items():
        if any(kw in msg_lower for kw in keywords):
            access_type = access
            break

    # ── 3. County + City ──────────────────────────────────────────────────────
    # City detected from CITY_ZONE_MULTIPLIERS first (more specific)
    from app.services.pricing_defaults import CITY_ZONE_MULTIPLIERS
    city: Optional[str] = None
    county = "Dallas"   # default

    for city_name in CITY_ZONE_MULTIPLIERS.keys():
        # Use word boundary to avoid "plano" matching "explanatory"
        if re.search(rf'\b{re.escape(city_name)}\b', msg_lower):
            city = city_name
            break

    # Infer county from city match first, then fall back to county keyword scan
    if city:
        for county_name, city_list in COUNTY_KEYWORDS.items():
            if city in city_list:
                county = county_name.capitalize()
                break
    else:
        for county_name, keywords in COUNTY_KEYWORDS.items():
            for kw in keywords:
                if re.search(rf'\b{re.escape(kw)}\b', msg_lower):
                    county = county_name.capitalize()
                    city = kw if kw in CITY_ZONE_MULTIPLIERS else city
                    break
            if county != "Dallas":
                break

    # ── 4. Disambiguation rules ───────────────────────────────────────────────
    # "toilet" + drain/clog signal → DRAIN_CLEAN, not TOILET_REPLACE
    _toilet_clog_signals = re.compile(
        r'\b(clogged|clog|back(ed)?\s*up|won\'?t\s+flush|not\s+flush|slow\s+flush|backup)\b'
    )
    _is_toilet_msg   = "toilet" in msg_lower or "commode" in msg_lower
    _is_clog_context = bool(_toilet_clog_signals.search(msg_lower))

    # "sink" + drain/clog signal → DRAIN_CLEAN_*, not faucet/sink replacement
    _sink_clog_signals = re.compile(
        r'\b(clogged|clog|back(ed)?\s*up|won\'?t\s+drain|not\s+drain|slow\s+drain|drain(ing)?\s+slow|backup|stopped\s+up)\b'
    )
    _is_sink_msg     = re.search(r'\b(sink|basin|lavatory|lav)\b', msg_lower) is not None
    _is_sink_clog    = _is_sink_msg and bool(_sink_clog_signals.search(msg_lower))

    # angle-stop / shutoff-valve mention → ANGLE_STOP_REPLACE family,
    # never LAV_SINK_REPLACE / KITCHEN_FAUCET_REPLACE just because a sink is referenced.
    _angle_stop_signals = re.compile(
        r'\b(angle\s*stop|angle\s*valve|shut[\s-]?off\s*valve|stop\s*valve|supply\s*valve)s?\b'
    )
    _is_angle_stop = bool(_angle_stop_signals.search(msg_lower))

    # Pre-extract quantity so disambiguation branches that need it (angle-stop
    # pair detection, etc.) can read it before the final assignment below.
    quantity = _extract_quantity(msg_lower)

    # "sewer" + repair/excavate signal → SEWER_SPOT_REPAIR, not MAIN_LINE_CLEAN
    _sewer_repair_signals = re.compile(r'\b(repair|broken|cracked|collapse|excavat|dig|spot)\b')
    _is_sewer_repair = bool(_sewer_repair_signals.search(msg_lower)) and \
                       ("sewer" in msg_lower or "sewer line" in msg_lower)

    # ── 5. Task detection ─────────────────────────────────────────────────────
    task_code    = None
    assembly_code = None
    confidence   = 0.7

    # ── Water heater special-case (must come before generic scan) ─────────────
    if "water heater" in msg_lower or "hot water heater" in msg_lower:
        _wh_repair_signals = re.compile(
            r'\b(pilot|thermocouple|gas\s+valve|element|tp\s+valve|t&p|temperature.pressure|'
            r'not\s+heat|repair|fix|leaking\s+around|rumbl|noise|whistl)\b'
        )
        _wh_flush_signals = re.compile(r'\b(flush|drain|descale|sediment|maintenance|annual)\b')
        _wh_anode_signals  = re.compile(r'\b(anode|sacrificial)\b')
        _wh_element_signals = re.compile(r'\b(element|electric.*not\s+work|element.*replac)\b')
        if _wh_anode_signals.search(msg_lower):
            task_code, assembly_code, confidence = "WH_ANODE_REPLACE", "ANODE_ROD_KIT", 0.92
        elif _wh_element_signals.search(msg_lower) and "electric" in msg_lower:
            task_code, assembly_code, confidence = "WH_ELEMENT_REPLACE", "WH_ELEMENT_KIT", 0.90
        elif _wh_flush_signals.search(msg_lower):
            task_code, assembly_code, confidence = "WH_FLUSH_MAINTENANCE", None, 0.90
        elif _wh_repair_signals.search(msg_lower):
            task_code, assembly_code, confidence = "WH_REPAIR_GAS", "WH_REPAIR_GAS_KIT", 0.90
        elif access_type == "attic" or "attic" in msg_lower:
            task_code, assembly_code, confidence = "WH_50G_GAS_ATTIC", "WH_50G_GAS_ATTIC_KIT", 0.90
        elif "tankless" in msg_lower or "on demand" in msg_lower or "instantaneous" in msg_lower:
            task_code, assembly_code, confidence = "WH_TANKLESS_GAS", "WH_TANKLESS_GAS_KIT", 0.92
        elif "electric" in msg_lower:
            task_code, assembly_code, confidence = "WH_50G_ELECTRIC_STANDARD", "WH_50G_ELECTRIC_KIT", 0.90
        elif re.search(r'\b40\b', msg_lower):
            task_code, assembly_code, confidence = "WH_40G_GAS_STANDARD", "WH_40G_GAS_KIT", 0.88
        else:
            task_code, assembly_code, confidence = "WH_50G_GAS_STANDARD", "WH_50G_GAS_KIT", 0.82

    # ── Disambiguation overrides ──────────────────────────────────────────────
    elif _is_angle_stop:
        # Angle stops always win over sink/faucet replacement.
        # "both" / "pair" / "two" / explicit qty>1 → pair variant if available.
        _is_pair = bool(re.search(r'\b(both|pair|two|2)\b', msg_lower)) or quantity >= 2
        pair_code = "ANGLE_STOP_REPLACE_PAIR"
        if _is_pair and pair_code in TASK_KEYWORDS:
            task_code     = pair_code
            assembly_code = TASK_KEYWORDS[pair_code].get("assembly")
            confidence    = 0.85
        else:
            task_code     = "ANGLE_STOP_REPLACE"
            assembly_code = TASK_KEYWORDS["ANGLE_STOP_REPLACE"].get("assembly")
            confidence    = 0.85

    elif _is_sink_clog:
        # Kitchen vs generic
        if "kitchen" in msg_lower and "DRAIN_CLEAN_KITCHEN" in TASK_KEYWORDS:
            task_code     = "DRAIN_CLEAN_KITCHEN"
        else:
            task_code     = "DRAIN_CLEAN_STANDARD"
        assembly_code = None
        confidence    = 0.82

    elif _is_toilet_msg and _is_clog_context:
        task_code     = "DRAIN_CLEAN_STANDARD"
        assembly_code = None
        confidence    = 0.80

    elif _is_sewer_repair:
        task_code     = "SEWER_SPOT_REPAIR"
        assembly_code = TASK_KEYWORDS["SEWER_SPOT_REPAIR"].get("assembly")
        confidence    = 0.82

    else:
        # ── Priority-ordered generic scan ─────────────────────────────────────
        # Sort by priority (1=highest), then by keyword specificity (longer = more specific)
        sorted_tasks = sorted(
            TASK_KEYWORDS.items(),
            key=lambda x: (x[1].get("priority", 2), -max(len(k) for k in x[1].get("keywords", [""]))),
        )

        for code, cfg in sorted_tasks:
            kws        = cfg.get("keywords", [])
            kws_exact  = cfg.get("keywords_exact", [])   # require word boundary

            # Standard substring match for multi-word phrases
            phrase_match = any(kw in msg_lower for kw in kws if len(kw) > 3)
            # Word-boundary match for short / ambiguous keywords
            exact_match  = any(re.search(rf'\b{re.escape(kw)}\b', msg_lower) for kw in kws_exact)
            # Short keywords (≤3 chars) always need word boundary
            short_match  = any(
                re.search(rf'\b{re.escape(kw)}\b', msg_lower)
                for kw in kws if len(kw) <= 3
            )

            if phrase_match or exact_match or short_match:
                task_code     = code
                assembly_code = cfg.get("assembly")

                # Confidence: base by keyword type + bonus for action word
                action_kws = cfg.get("actions", [])
                has_action = action_kws and any(a in msg_lower for a in action_kws)

                # Multi-word exact phrase gives higher base confidence
                best_kw_len = max((len(kw) for kw in kws if kw in msg_lower), default=0)
                if best_kw_len >= 10:
                    confidence = 0.92
                elif best_kw_len >= 6:
                    confidence = 0.85
                else:
                    confidence = 0.75

                if has_action:
                    confidence = min(confidence + 0.05, 0.95)

                break   # first priority-sorted match wins

        if not task_code:
            template_match = _classify_from_template_catalog(msg_lower)
            if template_match:
                task_code, assembly_code, confidence = template_match

    # ── 6. Preferred supplier ─────────────────────────────────────────────────
    preferred_supplier = None
    for sup in ["ferguson", "moore supply", "moore_supply", "apex"]:
        if sup.replace("_", " ") in msg_lower:
            preferred_supplier = sup.replace(" ", "_")
            break

    # quantity already extracted above (before disambiguation branches).

    return {
        "task_code":          task_code,
        "assembly_code":      assembly_code,
        "access_type":        access_type,
        "urgency":            urgency,
        "county":             county,
        "city":               city,
        "preferred_supplier": preferred_supplier,
        "confidence":         confidence,
        "quantity":           quantity,
        "raw_message":        raw_message,
    }


def _format_breakdown(result: EstimateResult, quantity: int) -> str:
    """Build the structured cost breakdown section (always shown)."""
    lines = []
    if quantity > 1:
        lines.append(f"**Total: ${result.grand_total:,.0f}** _(×{quantity} units — ${result.grand_total / quantity:,.0f} each)_")
    else:
        lines.append(f"**Total: ${result.grand_total:,.0f}**")
    lines.append("")
    lines.append(f"• Labor: **${result.labor_total:,.0f}**")
    lines.append(f"• Materials: **${result.materials_total:,.0f}**")
    if result.markup_total > 0:
        lines.append(f"• Materials markup: ${result.markup_total:,.0f}")
    if result.misc_total > 0:
        lines.append(f"• Misc/Disposal: ${result.misc_total:,.0f}")
    # Trip charge line
    trip = next((li for li in result.line_items if li.line_type == "trip"), None)
    if trip:
        lines.append(f"• Service call: ${trip.total_cost:,.0f}")
    # Permit line
    permit = next((li for li in result.line_items if li.line_type == "permit"), None)
    if permit:
        lines.append(f"• Permit fee: ${permit.total_cost:,.0f}")
    # City zone premium
    zone = next((li for li in result.line_items if li.line_type == "misc" and "Market Zone" in li.description), None)
    if zone:
        lines.append(f"• Market zone: +${zone.total_cost:,.0f}")
    lines.append(f"• Tax ({result.county} County): ${result.tax_total:,.2f}")
    lines.append("")
    lines.append(f"**Confidence: {result.confidence_label}** ({int(result.confidence_score * 100)}%)")
    if result.assumptions:
        lines.append("")
        lines.append("_Assumptions:_")
        for a in result.assumptions[:4]:
            lines.append(f"• {a}")
    return "\n".join(lines)


def format_estimate_response(
    result: EstimateResult,
    classification: dict,
    message: str,
    llm_opener: Optional[str] = None,
) -> dict:
    """Format EstimateResult into a user-friendly chat response.

    If llm_opener is provided (Hermes-generated text), it is prepended to the
    structured breakdown. Otherwise the breakdown leads with the price headline.
    """
    template = get_template(result.template_code or "")
    template_name = template.name if template else result.template_code
    quantity = classification.get("quantity", 1)

    breakdown = _format_breakdown(result, quantity)

    if llm_opener:
        # Hermes wrote the opener — put it first, then the numbers
        answer = f"{llm_opener}\n\n{breakdown}"
    else:
        # Fallback: lead with the template name then the breakdown
        header = f"_{template_name}_\n\n" if template_name else ""
        answer = header + breakdown

    return {
        "answer": answer,
        "estimate": {
            "labor_total": result.labor_total,
            "materials_total": result.materials_total,
            "tax_total": result.tax_total,
            "markup_total": result.markup_total,
            "misc_total": result.misc_total,
            "subtotal": result.subtotal,
            "grand_total": result.grand_total,
            "line_items": [
                {
                    "line_type": li.line_type,
                    "description": li.description,
                    "quantity": li.quantity,
                    "unit": li.unit,
                    "unit_cost": li.unit_cost,
                    "total_cost": li.total_cost,
                    "supplier": li.supplier,
                    "sku": li.sku,
                }
                for li in result.line_items
            ],
        },
        "confidence": result.confidence_score,
        "confidence_label": result.confidence_label,
        "assumptions": result.assumptions,
        "sources": result.sources,
        "job_type_detected": result.job_type,
        "template_used": result.template_code,
        "classification": classification,
    }


async def process_chat_message(
    message: str,
    county: Optional[str] = None,
    preferred_supplier: Optional[str] = None,
    job_type: Optional[str] = None,
    history: list[dict] | None = None,
    db=None,
    skip_llm_response: bool = False,
    user_id: Optional[int] = None,
) -> dict:
    """
    Main entry point for chat pricing requests.

    Pipeline:
      1. Keyword classify  (fast, always runs)
      2. LLM classify      (Hermes 3 via Ollama — runs when keyword confidence
                            is below threshold or no task matched)
      3. Deterministic price (PricingEngine — never bypassed)
      4. LLM response      (natural language opener — skipped when
                            skip_llm_response=True, e.g. for streaming endpoint
                            which calls generate_response_stream separately)
    """

    # ── Step 1: Keyword classification (fast path) ───────────────────────────
    classification = classify_request(message)

    # Caller-supplied overrides take precedence
    if county:
        classification["county"] = county
    if preferred_supplier:
        classification["preferred_supplier"] = preferred_supplier

    keyword_task_code  = classification.get("task_code")
    keyword_confidence = classification.get("confidence", 0.0)
    threshold          = settings.llm_classify_threshold

    # ── Step 2: LLM classification (escalation path) ─────────────────────────
    # Escalate when: no keyword match OR confidence below threshold
    classified_by = "keyword"
    if not keyword_task_code or keyword_confidence < threshold:
        llm_result = await llm_service.classify(message, history=history)
        if llm_result and llm_result.get("task_code"):
            # LLM resolved the intent — merge into classification
            for key in ("task_code", "access_type", "urgency", "quantity"):
                if llm_result.get(key) is not None:
                    classification[key] = llm_result[key]

            # Override county only when keyword didn't detect one and caller didn't supply one
            if not county and llm_result.get("county"):
                classification["county"] = llm_result["county"]

            # Override city from LLM if keyword didn't already detect one
            if not classification.get("city") and llm_result.get("city"):
                classification["city"] = llm_result["city"]

            if not preferred_supplier and llm_result.get("preferred_supplier"):
                classification["preferred_supplier"] = llm_result["preferred_supplier"]

            # Inject assembly when the resolved task_code maps to a known kit.
            new_task = classification["task_code"]
            if not classification.get("assembly_code"):
                classification["assembly_code"] = _default_assembly_for_task(new_task)

            classification["confidence"] = llm_result.get("confidence", 0.85)
            classified_by = "llm"

            logger.info(
                "LLM classification upgraded keyword result",
                keyword_task=keyword_task_code,
                llm_task=new_task,
                confidence=classification["confidence"],
            )

    classification["classified_by"] = classified_by

    # ── County normalization ─────────────────────────────────────────────────
    # LLMs frequently default county to Dallas while correctly identifying the
    # city. Re-derive county from the detected city when a caller hasn't pinned
    # it explicitly so e.g. "Plano" → Collin, "Fort Worth" → Tarrant, etc.
    if not county:
        detected_city = (classification.get("city") or "").strip().lower()
        if detected_city:
            for county_name, city_list in COUNTY_KEYWORDS.items():
                if detected_city in city_list:
                    derived = county_name.capitalize()
                    if classification.get("county") != derived:
                        logger.info(
                            "county.derived_from_city",
                            city=detected_city,
                            previous=classification.get("county"),
                            derived=derived,
                        )
                    classification["county"] = derived
                    break

    # ── Task-code normalization (catch common LLM misclassifications) ────────
    # The LLM sometimes returns a fixture-replacement code when the customer
    # is clearly describing a drain or angle-stop issue.  Re-apply the same
    # disambiguation rules used by the keyword classifier as a safety net.
    msg_lower_norm = (message or "").lower()
    current_task   = (classification.get("task_code") or "").upper()

    _angle_stop_re = re.compile(
        r'\b(angle\s*stop|angle\s*valve|shut[\s-]?off\s*valve|stop\s*valve|supply\s*valve)s?\b'
    )
    _sink_clog_re = re.compile(
        r'\b(clogged|clog|back(ed)?\s*up|won\'?t\s+drain|not\s+drain|slow\s+drain|drain(ing)?\s+slow|backup|stopped\s+up)\b'
    )
    _sink_re      = re.compile(r'\b(sink|basin|lavatory|lav)\b')
    _pair_re      = re.compile(r'\b(both|pair|two|2)\b')

    _fixture_codes = {
        "KITCHEN_FAUCET_REPLACE", "LAV_FAUCET_REPLACE", "LAV_SINK_REPLACE",
        "TOILET_REPLACE", "TOILET_COMFORT_HEIGHT",
    }

    # Angle-stop wins over fixture replacement
    if _angle_stop_re.search(msg_lower_norm) and current_task in _fixture_codes:
        is_pair = bool(_pair_re.search(msg_lower_norm)) or (classification.get("quantity") or 1) >= 2
        new_code = "ANGLE_STOP_REPLACE_PAIR" if is_pair and "ANGLE_STOP_REPLACE_PAIR" in TASK_KEYWORDS \
                                              else "ANGLE_STOP_REPLACE"
        logger.info(
            "task_code.normalized",
            reason="angle_stop_over_fixture",
            previous=current_task,
            corrected=new_code,
        )
        classification["task_code"]      = new_code
        classification["assembly_code"]  = TASK_KEYWORDS.get(new_code, {}).get("assembly")
        classification["classified_by"]  = "post_llm_rule"
        # Force qty=2 when "both/pair" present and we landed on the singleton variant
        if is_pair and new_code == "ANGLE_STOP_REPLACE":
            classification["quantity"] = max(2, int(classification.get("quantity") or 1))
        current_task = new_code

    # Sink/faucet replacement when description is actually a clog → drain clean
    elif (
        current_task in {"KITCHEN_FAUCET_REPLACE", "LAV_FAUCET_REPLACE", "LAV_SINK_REPLACE"}
        and _sink_re.search(msg_lower_norm)
        and _sink_clog_re.search(msg_lower_norm)
    ):
        new_code = "DRAIN_CLEAN_KITCHEN" if (
            "kitchen" in msg_lower_norm and "DRAIN_CLEAN_KITCHEN" in TASK_KEYWORDS
        ) else "DRAIN_CLEAN_STANDARD"
        logger.info(
            "task_code.normalized",
            reason="sink_clog_over_replacement",
            previous=current_task,
            corrected=new_code,
        )
        classification["task_code"]      = new_code
        classification["assembly_code"]  = None
        classification["classified_by"]  = "post_llm_rule"
        current_task = new_code

    # ── Unclassifiable ────────────────────────────────────────────────────────
    task_code    = classification.get("task_code")
    assembly_code = classification.get("assembly_code")

    if not task_code:
        return {
            "answer": (
                "I can help price plumbing, construction, and commercial plumbing work. Try asking something like:\n"
                "• _How much to replace a water heater in the attic?_\n"
                "• _Price to rough in a master bath in Plano_\n"
                "• _Cost to install a commercial mop sink in Dallas_"
            ),
            "estimate": None,
            "confidence": 0.0,
            "confidence_label": "LOW",
            "assumptions": ["Could not classify job type from message"],
            "sources": [],
        }

    quantity = classification.get("quantity", 1)
    preferred_supplier = classification.get("preferred_supplier")

    # ── Steps 3+4: Material costs + Deterministic pricing ────────────────────
    # Fast path: no DB → use pure in-memory canonical map (zero DB round-trips)
    # Standard path: DB session present → single batched query for all assembly items
    if not db:
        result = pricing_engine.quick_estimate(
            task_code=task_code,
            assembly_code=assembly_code,
            access=classification["access_type"],
            urgency=classification["urgency"],
            county=classification["county"],
            city=classification.get("city"),
            preferred_supplier=preferred_supplier,
            quantity=quantity,
        )
    else:
        materials: list[MaterialItem] = []
        if assembly_code:
            materials = await supplier_service.get_assembly_costs(
                assembly_code,
                preferred_supplier=preferred_supplier,
                db=db,
            )
        result = pricing_engine.calculate_service_estimate(
            task_code=task_code,
            materials=materials,
            assembly_code=assembly_code,
            access=classification["access_type"],
            urgency=classification["urgency"],
            county=classification["county"],
            city=classification.get("city"),
            preferred_supplier=preferred_supplier,
        )
        if quantity > 1:
            result = pricing_engine.scale_estimate(result, quantity)

    # ── Step 5: LLM response generation (optional) ───────────────────────────
    template      = get_template(result.template_code or "")
    template_name = template.name if template else (result.template_code or "")

    # Retrieve RAG context if DB session is available
    rag_context = ""
    rag_sources: list[dict] = []
    memory_context = ""
    memory_hits: list[dict] = []
    outcome_context = ""
    outcome_hits: list[dict] = []
    if db:
        try:
            chunks = await rag_service.retrieve(db, message, top_k=3)
            if chunks:
                rag_context = "\n".join([f"Source: {c['source']}\n{c['content']}" for c in chunks])
                rag_sources = [
                    {
                        "doc_id": c["document_id"],
                        "doc_name": c.get("document_name", "Unknown"),
                        "score": c["score"],
                        "chunk_idx": c["chunk_index"],
                    }
                    for c in chunks[:3]
                ]
                # Attach source attribution to every line item's trace_json
                for li in result.line_items:
                    li.trace_json = {**(li.trace_json or {}), "rag_sources": rag_sources}
                logger.info("rag.context_retrieved", chunks=len(chunks))
        except Exception as e:
            logger.warning("rag.retrieve_failed", error=str(e))

        # Long-term memory retrieval (Phase 1)
        if user_id is not None:
            try:
                from app.services.memory_service import memory_service
                memory_hits = await memory_service.retrieve(
                    db, user_id=user_id, query=message, top_k=5
                )
                if memory_hits:
                    memory_context = "Known facts about this user:\n" + "\n".join(
                        f"- ({m['kind']}) {m['content']}" for m in memory_hits
                    )
                    for li in result.line_items:
                        li.trace_json = {
                            **(li.trace_json or {}),
                            "memory_hits": [
                                {"id": m["id"], "kind": m["kind"], "score": m["score"]}
                                for m in memory_hits
                            ],
                        }
                    logger.info("memory.context_retrieved", count=len(memory_hits))
            except Exception as e:
                logger.warning("memory.retrieve_failed", error=str(e))

        # Similar past job outcomes (Phase 1 — outcomes context)
        if user_id is not None:
            try:
                from app.services.outcomes_context import get_similar_outcomes_context
                from app.models.users import User
                org_id = None
                user_row = await db.get(User, user_id)
                if user_row is not None:
                    org_id = getattr(user_row, "organization_id", None)
                outcome_context, outcome_hits = await get_similar_outcomes_context(
                    db,
                    user_id=user_id,
                    organization_id=org_id,
                    message=message,
                    job_type=job_type,
                    task_code=classification.get("task_code"),
                    limit=5,
                )
                if outcome_hits:
                    for li in result.line_items:
                        li.trace_json = {
                            **(li.trace_json or {}),
                            "similar_outcomes": [
                                {
                                    "estimate_id": h["estimate_id"],
                                    "outcome": h["outcome"],
                                    "price": h["final_price"] or h["grand_total"],
                                }
                                for h in outcome_hits[:3]
                            ],
                        }
                    logger.info("outcomes.context_retrieved", count=len(outcome_hits))
            except Exception as e:
                logger.warning("outcomes.retrieve_failed", error=str(e))

    llm_opener = None
    if not skip_llm_response:
        combined_context = "\n\n".join(
            c for c in [memory_context, outcome_context, rag_context] if c
        )
        llm_opener = await llm_service.generate_response(
            message=message,
            grand_total=result.grand_total,
            labor_total=result.labor_total,
            materials_total=result.materials_total,
            tax_total=result.tax_total,
            template_name=template_name,
            county=result.county,
            quantity=quantity,
            history=history,
            context=combined_context
        )

    # ── Step 6: Format final response ────────────────────────────────────────
    response = format_estimate_response(result, classification, message, llm_opener=llm_opener)
    response["_estimate_result"] = result   # raw, for callers (not serialised)
    response["_template_name"]   = template_name  # for stream endpoint
    response["_rag_context"]     = rag_context  # for stream endpoint
    response["_memory_context"]  = memory_context
    response["_memory_hits"]     = memory_hits
    response["_outcome_context"] = outcome_context
    response["_outcome_hits"]    = outcome_hits
    return response
