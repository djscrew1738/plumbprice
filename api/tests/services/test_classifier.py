"""
Unit tests for the keyword classifier (classify_request).
No database or LLM required — pure function tests.
"""

import os
os.environ.setdefault("ENVIRONMENT", "test")
os.environ.setdefault("SECRET_KEY", "test-secret-key")

import pytest

from app.services.agent import classify_request, _extract_quantity


# ─── _extract_quantity ────────────────────────────────────────────────────────

def test_extract_quantity_single_digit():
    assert _extract_quantity("replace 3 toilets") == 3


def test_extract_quantity_word_number():
    assert _extract_quantity("two water heaters") == 2


def test_extract_quantity_defaults_to_one():
    assert _extract_quantity("replace the toilet") == 1


def test_extract_quantity_ignores_one():
    # "1" should NOT be matched (regex requires 2-20), single items default to 1
    assert _extract_quantity("1 toilet") == 1


def test_extract_quantity_large():
    assert _extract_quantity("install 10 angle stops") == 10


# ─── Task classification ──────────────────────────────────────────────────────

def test_classify_toilet():
    result = classify_request("how much to replace a toilet")
    assert result["task_code"] == "TOILET_REPLACE_STANDARD"
    assert result["assembly_code"] == "TOILET_INSTALL_KIT"
    assert result["confidence"] >= 0.75


def test_classify_water_heater_gas_default():
    result = classify_request("replace my water heater")
    assert result["task_code"] == "WH_50G_GAS_STANDARD"
    assert result["assembly_code"] == "WH_50G_GAS_KIT"


def test_classify_water_heater_attic():
    result = classify_request("water heater is in the attic, needs replacing")
    assert result["task_code"] == "WH_50G_GAS_ATTIC"
    assert result["access_type"] == "attic"


def test_classify_water_heater_tankless():
    result = classify_request("install a tankless water heater")
    assert result["task_code"] == "WH_TANKLESS_GAS"


def test_classify_water_heater_electric():
    result = classify_request("replace electric water heater")
    assert result["task_code"] == "WH_50G_ELECTRIC_STANDARD"


def test_classify_water_heater_40g():
    result = classify_request("replace 40 gallon water heater")
    assert result["task_code"] == "WH_40G_GAS_STANDARD"


def test_classify_kitchen_faucet():
    result = classify_request("swap out the kitchen faucet")
    assert result["task_code"] == "KITCHEN_FAUCET_REPLACE"


def test_classify_garbage_disposal():
    result = classify_request("install a new garbage disposal")
    assert result["task_code"] == "GARBAGE_DISPOSAL_INSTALL"


def test_classify_drain_clean():
    result = classify_request("I have a clogged drain in the bathroom")
    assert result["task_code"] == "DRAIN_CLEAN_STANDARD"


def test_classify_slab_leak():
    result = classify_request("I have a slab leak under the foundation")
    assert result["task_code"] == "SLAB_LEAK_REPAIR"
    assert result["access_type"] == "slab"


def test_classify_prv():
    result = classify_request("replace the pressure reducing valve")
    assert result["task_code"] == "PRV_REPLACE"


def test_classify_construction_master_bath_rough_in():
    result = classify_request("price to rough in a master bath in Plano")
    assert result["task_code"] == "ROUGH_IN_MASTER_BATH"
    assert result["county"] == "Collin"
    assert result["assembly_code"] is None
    assert result["confidence"] >= 0.74


def test_classify_commercial_urinal_install():
    result = classify_request("install a commercial urinal in an office restroom")
    assert result["task_code"] == "COMMERCIAL_URINAL_INSTALL"
    assert result["assembly_code"] == "URINAL_INSTALL_KIT"
    assert result["confidence"] >= 0.74


def test_classify_unknown_returns_none_task():
    result = classify_request("I need a plumber to help me")
    assert result["task_code"] is None
    assert result["confidence"] == 0.7


# ─── Access type detection ────────────────────────────────────────────────────

def test_classify_second_floor_access():
    result = classify_request("replace toilet on second floor")
    assert result["access_type"] == "second_floor"


def test_classify_crawlspace_access():
    result = classify_request("there's a pipe leak under the crawlspace")
    assert result["access_type"] == "crawlspace"


def test_classify_default_access_is_first_floor():
    result = classify_request("replace bathroom faucet")
    assert result["access_type"] == "first_floor"


# ─── Urgency detection ────────────────────────────────────────────────────────

def test_classify_emergency_urgency():
    result = classify_request("emergency! toilet is flooding the bathroom")
    assert result["urgency"] == "emergency"


def test_classify_same_day_urgency():
    result = classify_request("need the water heater replaced today")
    assert result["urgency"] == "same_day"


def test_classify_standard_urgency_by_default():
    result = classify_request("replace toilet next week")
    assert result["urgency"] == "standard"


# ─── County detection ─────────────────────────────────────────────────────────

def test_classify_tarrant_county():
    result = classify_request("replace faucet in fort worth")
    assert result["county"] == "Tarrant"


def test_classify_collin_county():
    result = classify_request("install water heater in Plano")
    assert result["county"] == "Collin"


def test_classify_denton_county():
    result = classify_request("need a plumber in Lewisville")
    assert result["county"] == "Denton"


def test_classify_defaults_to_dallas():
    result = classify_request("replace toilet")
    assert result["county"] == "Dallas"


# ─── Supplier preference ──────────────────────────────────────────────────────

def test_classify_preferred_supplier_ferguson():
    result = classify_request("replace toilet using ferguson parts")
    assert result["preferred_supplier"] == "ferguson"


def test_classify_preferred_supplier_moore_supply():
    result = classify_request("water heater install with moore supply")
    assert result["preferred_supplier"] == "moore_supply"


def test_classify_no_preferred_supplier():
    result = classify_request("replace toilet")
    assert result["preferred_supplier"] is None


# ─── Quantity ─────────────────────────────────────────────────────────────────

def test_classify_multiple_toilets():
    result = classify_request("replace 3 toilets in the building")
    assert result["quantity"] == 3
    assert result["task_code"] == "TOILET_REPLACE_STANDARD"


def test_classify_quantity_word():
    result = classify_request("install five angle stops")
    assert result["quantity"] == 5
