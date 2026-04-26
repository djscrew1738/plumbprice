"""Tests for the proactive add-on suggestion engine (Track D2)."""
from app.services.addon_suggestions import suggest_addons, ADJACENCY_RULES


def test_toilet_replace_suggests_wax_ring_and_stops():
    out = suggest_addons(["TOILET_REPLACE_STANDARD"])
    codes = {s.task_code for s in out}
    assert "TOILET_WAX_RING_ONLY" in codes
    assert "ANGLE_STOP_REPLACE" in codes
    assert "SUPPLY_LINE_REPLACE" in codes


def test_existing_codes_are_filtered():
    out = suggest_addons(["TOILET_REPLACE_STANDARD", "TOILET_WAX_RING_ONLY"])
    codes = {s.task_code for s in out}
    assert "TOILET_WAX_RING_ONLY" not in codes  # already on the estimate
    assert "ANGLE_STOP_REPLACE" in codes


def test_severity_sort_puts_code_required_first():
    out = suggest_addons(["WH_TANKLESS_GAS"])
    severities = [s.severity for s in out]
    # All code_required items come before any best_practice items.
    last_required = max((i for i, s in enumerate(severities) if s == "code_required"), default=-1)
    first_best = next((i for i, s in enumerate(severities) if s == "best_practice"), len(severities))
    assert last_required < first_best


def test_prv_triggers_expansion_control_code_required():
    out = suggest_addons(["PRV_REPLACE"])
    sug = {s.task_code: s for s in out}
    assert "EXPANSION_TANK_INSTALL" in sug
    assert sug["EXPANSION_TANK_INSTALL"].severity == "code_required"


def test_no_triggers_returns_empty():
    out = suggest_addons(["NOT_A_REAL_CODE", "ALSO_FAKE"])
    assert out == []


def test_empty_input_returns_empty():
    assert suggest_addons([]) == []


def test_max_suggestions_clamps_output():
    out = suggest_addons(list(ADJACENCY_RULES.keys()), max_suggestions=3)
    assert len(out) == 3


def test_first_rationale_wins_on_dup_suggestion():
    # Both TOILET_REPLACE_STANDARD and TOILET_INSTALL_NEW suggest ANGLE_STOP_REPLACE.
    out = suggest_addons(["TOILET_REPLACE_STANDARD", "TOILET_INSTALL_NEW"])
    angle = [s for s in out if s.task_code == "ANGLE_STOP_REPLACE"]
    assert len(angle) == 1


def test_case_insensitive_existing_filter():
    out = suggest_addons(["toilet_replace_standard", "toilet_wax_ring_only"])
    codes = {s.task_code for s in out}
    assert "TOILET_WAX_RING_ONLY" not in codes


def test_sewer_replace_includes_hydrostatic_test():
    out = suggest_addons(["SEWER_LINE_REPLACE_FULL"])
    codes = {s.task_code for s in out}
    assert "HYDROSTATIC_TEST_SEWER" in codes


def test_repipe_includes_pressure_test_code_required():
    out = suggest_addons(["WHOLE_HOUSE_REPIPE_PEX"])
    sug = {s.task_code: s for s in out}
    assert "PRESSURE_TEST_SYSTEM" in sug
    assert sug["PRESSURE_TEST_SYSTEM"].severity == "code_required"
