import pytest

from app.services.intake_agent import infer_intake, _heuristic_intake


class TestHeuristicIntake:
    def test_extracts_fixture_counts(self):
        result = _heuristic_intake("I need 3 toilets and 2 sinks replaced in Plano")
        assert result.fixture_counts.get("toilet") == 3
        assert result.fixture_counts.get("sink") == 2
        assert result.location == "Plano"

    def test_extracts_word_numbers(self):
        result = _heuristic_intake("two water heaters in Dallas")
        assert result.fixture_counts.get("water_heater") == 2
        assert result.location == "Dallas"

    def test_extracts_urgency_emergency(self):
        result = _heuristic_intake("emergency burst pipe in Fort Worth")
        assert result.urgency == "emergency"

    def test_extracts_tier_budget(self):
        result = _heuristic_intake("cheap toilet replacement in Garland")
        assert result.preferred_tier == "budget"

    def test_extracts_tier_premium(self):
        result = _heuristic_intake("premium tankless water heater in Frisco")
        assert result.preferred_tier == "premium"

    def test_no_signals_returns_low_confidence(self):
        result = _heuristic_intake("hello")
        assert result.confidence < 0.5
        assert result.fixture_counts == {}


class TestInferIntake:
    @pytest.mark.asyncio
    async def test_returns_intake_for_rich_message(self):
        result = await infer_intake("3 bath remodel in Plano, same day")
        assert result.confidence > 0.0
        assert result.location == "Plano"
        assert result.urgency == "same_day"

    @pytest.mark.asyncio
    async def test_uses_county_when_no_location(self):
        result = await infer_intake("replace toilet", county="collin")
        assert result.location == "Collin"
        assert result.confidence > 0.0

    @pytest.mark.asyncio
    async def test_returns_empty_for_greeting(self):
        result = await infer_intake("hi there")
        assert result.confidence == 0.0
