"""Proactive add-on suggestions (Track D2).

Given a list of task codes already on an estimate, return a list of plausible
*missing* task codes that DFW plumbing best-practice typically pairs with the
already-selected work. Each suggestion comes with a one-line rationale so the
estimator UI can show "did you forget X?" prompts.

The rules are intentionally hand-curated (not learned) so we can reason about
why a suggestion fired. See `ADJACENCY_RULES` for the source of truth.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable


@dataclass(frozen=True)
class AddOnSuggestion:
    task_code: str
    rationale: str
    severity: str  # "recommended" | "code_required" | "best_practice"


# Map of trigger task code -> tuple of (suggested_code, rationale, severity).
# A trigger can have multiple suggestions; suggestions are de-duplicated when
# more than one trigger fires for the same suggested code (first rationale wins).
ADJACENCY_RULES: dict[str, tuple[tuple[str, str, str], ...]] = {
    # --- Toilets ---
    "TOILET_REPLACE_STANDARD": (
        ("TOILET_WAX_RING_ONLY", "New wax ring is standard with any toilet replace.", "best_practice"),
        ("ANGLE_STOP_REPLACE", "Aging angle stops fail under fresh torque — replace while open.", "recommended"),
        ("SUPPLY_LINE_REPLACE", "Replace braided supply with the toilet to avoid call-backs.", "best_practice"),
    ),
    "TOILET_INSTALL_NEW": (
        ("TOILET_FLANGE_REPAIR", "New rough-in often needs flange height adjustment.", "recommended"),
        ("ANGLE_STOP_REPLACE", "New install — fresh stop on the supply.", "best_practice"),
        ("SUPPLY_LINE_REPLACE", "Pair new supply line with new install.", "best_practice"),
    ),
    # --- Water heaters (TX code-required pairs) ---
    "WH_TANKLESS_GAS": (
        ("EXPANSION_TANK_INSTALL", "TX code requires expansion tank on closed systems.", "code_required"),
        ("GAS_LINE_TANKLESS_WH", "Tankless usually needs upsized gas line.", "code_required"),
        ("TANKLESS_VENT_INSTALL", "Direct-vent kit + termination required.", "code_required"),
        ("TANKLESS_CONDENSATE_DRAIN", "Condensing units require condensate drain.", "code_required"),
        ("TPR_VALVE_REPLACE", "New TPR with new heater.", "best_practice"),
    ),
    "WH_REPAIR_GAS": (
        ("TPR_VALVE_REPLACE", "Inspect/replace TPR while servicing the unit.", "best_practice"),
    ),
    "CONDO_WATER_HEATER_REPLACE": (
        ("EXPANSION_TANK_INSTALL", "TX code: expansion tank required on closed systems.", "code_required"),
        ("WH_DRAIN_PAN_REPLACE", "Drain pan + overflow are required in upper-floor installs.", "code_required"),
        ("TPR_VALVE_REPLACE", "Fresh TPR with replacement.", "best_practice"),
    ),
    # --- Repipes ---
    "WHOLE_HOUSE_REPIPE_PEX": (
        ("MANIFOLD_INSTALL_PEX", "Modern PEX repipe usually adds a manifold.", "best_practice"),
        ("PRESSURE_TEST_SYSTEM", "Always pressure-test post-repipe.", "code_required"),
        ("SHUT_OFF_VALVE_MAIN", "Replace main shutoff while access is open.", "best_practice"),
        ("EXPANSION_TANK_INSTALL", "Closed-system requirement — verify on repipe.", "code_required"),
    ),
    "GALVANIZED_WHOLE_HOUSE_REPIPE": (
        ("MANIFOLD_INSTALL_PEX", "Manifold simplifies the new system.", "best_practice"),
        ("PRESSURE_TEST_SYSTEM", "Required post-repipe.", "code_required"),
        ("SHUT_OFF_VALVE_MAIN", "Replace galv main shutoff with new ball valve.", "best_practice"),
    ),
    # --- Slab leaks ---
    "SLAB_LEAK_REPAIR": (
        ("LEAK_DETECTION_ELECTRONIC", "Confirm location before opening slab.", "best_practice"),
        ("PRESSURE_TEST_SYSTEM", "Verify the repair held.", "code_required"),
    ),
    "SLAB_LEAK_REROUTE": (
        ("ATTIC_PIPE_INSULATION_UPGRADE", "New attic runs need insulation in DFW summer/winter swings.", "code_required"),
        ("PRESSURE_TEST_SYSTEM", "Verify reroute.", "code_required"),
    ),
    # --- Sewer ---
    "SEWER_LINE_REPLACE_FULL": (
        ("HYDROSTATIC_TEST_SEWER", "Required acceptance test.", "code_required"),
        ("CLEAN_OUT_INSTALL", "Add a cleanout if the line doesn't have one.", "best_practice"),
        ("SEWER_TAP_CONNECTION", "City tap connection coordination.", "recommended"),
    ),
    "SEWER_SPOT_REPAIR": (
        ("HYDROSTATIC_TEST_SEWER", "Confirm the system holds before backfill.", "code_required"),
    ),
    # --- Faucets / fixtures ---
    "KITCHEN_FAUCET_REPLACE": (
        ("ANGLE_STOP_REPLACE_PAIR", "Two old stops typically replaced with the faucet.", "best_practice"),
        ("SUPPLY_LINE_REPLACE", "Fresh braided supplies prevent leaks.", "best_practice"),
    ),
    "LAV_FAUCET_REPLACE": (
        ("ANGLE_STOP_REPLACE_PAIR", "Replace both stops with the faucet.", "best_practice"),
        ("PTRAP_REPLACE", "Old chrome P-traps usually crumble during R&R.", "best_practice"),
    ),
    "SHOWER_VALVE_REPLACE": (
        ("FIXTURE_CAULK_RESEAL", "Reseal trim plate after R&R.", "best_practice"),
    ),
    # --- Gas ---
    "GAS_LINE_NEW_RUN": (
        ("GAS_PRESSURE_TEST", "TX requires pressure test on new gas runs.", "code_required"),
        ("GAS_DRIP_LEG_INSTALL", "Drip leg at appliance termination.", "code_required"),
    ),
    "GAS_LINE_RANGE_OVEN": (
        ("GAS_PRESSURE_TEST", "Pressure test new gas drop.", "code_required"),
        ("GAS_RANGE_CONNECTOR_REPLACE", "New flex connector required (no reuse).", "code_required"),
    ),
    "GAS_LINE_DRYER": (
        ("GAS_PRESSURE_TEST", "Pressure test new gas drop.", "code_required"),
    ),
    # --- Remodels ---
    "BATH_REMODEL_PLUMBING_STANDARD": (
        ("FIXTURE_TRIM_OUT_FULL_BATH", "Trim-out is a separate phase from rough-in.", "recommended"),
        ("PRESSURE_TEST_SYSTEM", "Pre-cover pressure test.", "code_required"),
    ),
    "KITCHEN_REMODEL_PLUMBING": (
        ("FIXTURE_TRIM_OUT_FULL_BATH", "Don't forget trim-out hours.", "recommended"),
        ("PRESSURE_TEST_SYSTEM", "Pre-cover pressure test.", "code_required"),
    ),
    # --- New construction rough ---
    "ROUGH_IN_PER_BATH_GROUP": (
        ("PRESSURE_TEST_SYSTEM", "Pressure test required before cover.", "code_required"),
        ("STUB_OUT_CAP_TEST", "Cap & test each stub-out.", "code_required"),
        ("TOP_OUT_PER_FIXTURE", "Top-out is a separate phase.", "recommended"),
    ),
    # --- PRV / pressure ---
    "PRV_REPLACE": (
        ("EXPANSION_TANK_INSTALL", "PRV creates a closed system — TX code requires expansion control.", "code_required"),
        ("THERMAL_EXPANSION_VALVE", "Alternative to expansion tank in tight spaces.", "code_required"),
    ),
    "PRV_INSTALL_NEW": (
        ("EXPANSION_TANK_INSTALL", "PRV creates a closed system — TX code requires expansion control.", "code_required"),
        ("SHUT_OFF_VALVE_MAIN", "Service valve at the PRV.", "best_practice"),
    ),
    # --- Backflow ---
    "BACKFLOW_PREVENTER_INSTALL": (
        ("BACKFLOW_TEST_ANNUAL", "Initial test and annual reminder.", "code_required"),
    ),
    # --- Disposals ---
    "GARBAGE_DISPOSAL_INSTALL": (
        ("ANGLE_STOP_REPLACE", "Often paired with kitchen R&R.", "best_practice"),
        ("DISHWASHER_DRAIN_REPAIR", "Verify dishwasher drain knockout / loop.", "best_practice"),
    ),
}


def suggest_addons(
    existing_codes: Iterable[str],
    *,
    max_suggestions: int = 8,
) -> list[AddOnSuggestion]:
    """Return missing-line-item suggestions for a set of already-selected codes.

    Suggestions for codes already in `existing_codes` are filtered out. The
    first rationale wins when multiple triggers nominate the same suggestion.
    Output is sorted by severity (code_required → recommended → best_practice)
    then by task_code for stability, and capped at `max_suggestions`.
    """
    existing = {c.upper() for c in existing_codes if c}
    seen: dict[str, AddOnSuggestion] = {}

    for trigger in existing:
        for code, rationale, severity in ADJACENCY_RULES.get(trigger, ()):
            if code in existing or code in seen:
                continue
            seen[code] = AddOnSuggestion(
                task_code=code,
                rationale=rationale,
                severity=severity,
            )

    severity_rank = {"code_required": 0, "recommended": 1, "best_practice": 2}
    ordered = sorted(
        seen.values(),
        key=lambda s: (severity_rank.get(s.severity, 99), s.task_code),
    )
    return ordered[:max_suggestions]
