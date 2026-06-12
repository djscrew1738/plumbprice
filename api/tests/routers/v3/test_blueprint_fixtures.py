"""Tests for Phase 11 — Blueprint-to-Estimate auto-seeding."""
import pytest
from app.services.agent_v3 import _seed_quantity_from_blueprint


class TestSeedQuantityFromBlueprint:
    def test_toilet_task_matches_toilet_fixture(self):
        fixtures = {"toilet": 3}
        result = _seed_quantity_from_blueprint("TOILET_REPLACE_STANDARD", fixtures)
        assert result == (3, "toilet")

    def test_water_heater_matches_wh_fixture(self):
        fixtures = {"water_heater": 2}
        result = _seed_quantity_from_blueprint("WH_50G_GAS_STANDARD", fixtures)
        assert result == (2, "water_heater")

    def test_lavatory_matches_lav_fixture(self):
        fixtures = {"lavatory": 4}
        result = _seed_quantity_from_blueprint("LAV_SINK_REPLACE", fixtures)
        assert result == (4, "lavatory")

    def test_kitchen_sink_matches_sink_fixture(self):
        fixtures = {"kitchen_sink": 1}
        result = _seed_quantity_from_blueprint("KITCHEN_FAUCET_REPLACE", fixtures)
        assert result == (1, "kitchen_sink")

    def test_no_match_returns_none(self):
        fixtures = {"toilet": 3}
        result = _seed_quantity_from_blueprint("DRAIN_CLEAN_MAIN", fixtures)
        assert result is None

    def test_empty_fixtures_returns_none(self):
        result = _seed_quantity_from_blueprint("TOILET_REPLACE_STANDARD", {})
        assert result is None

    def test_no_task_code_returns_none(self):
        fixtures = {"toilet": 3}
        result = _seed_quantity_from_blueprint(None, fixtures)  # type: ignore[arg-type]
        assert result is None

    def test_multiple_fixtures_first_match_wins(self):
        fixtures = {"toilet": 3, "water_heater": 2}
        # TOILET task should match toilet fixture
        result = _seed_quantity_from_blueprint("TOILET_REPLACE_STANDARD", fixtures)
        assert result == (3, "toilet")

    def test_fixture_count_zero_ignored(self):
        fixtures = {"toilet": 0}
        result = _seed_quantity_from_blueprint("TOILET_REPLACE_STANDARD", fixtures)
        assert result is None
