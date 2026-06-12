import pytest

from app.services.revision_suggestions import suggest_revisions
from app.services.pricing_engine import EstimateResult, LineItem


def _make_estimate(line_items: list[LineItem]) -> EstimateResult:
    return EstimateResult(
        template_code="TEST",
        assembly_code=None,
        job_type="service",
        access_type="first_floor",
        urgency_type="standard",
        county="Dallas",
        tax_rate=0.0825,
        labor_total=100.0,
        materials_total=200.0,
        tax_total=25.0,
        markup_total=50.0,
        misc_total=0.0,
        subtotal=350.0,
        grand_total=350.0,
        confidence_score=0.85,
        confidence_label="HIGH",
        line_items=line_items,
        assumptions=[],
        sources=[],
        pricing_trace={},
    )


class TestRevisionSuggestions:
    def test_suggests_tankless_for_water_heater(self):
        estimate = _make_estimate([
            LineItem(
                line_type="labor",
                description="Water heater replacement",
                quantity=1,
                unit="ea",
                unit_cost=100.0,
                total_cost=100.0,
                canonical_item="WH_50G_GAS_STANDARD",
            )
        ])
        suggestions = suggest_revisions(estimate)
        labels = [s.label for s in suggestions]
        assert "Upgrade to tankless water heater" in labels

    def test_suggests_permit_when_missing(self):
        estimate = _make_estimate([
            LineItem(
                line_type="labor",
                description="Toilet replacement",
                quantity=1,
                unit="ea",
                unit_cost=50.0,
                total_cost=50.0,
                canonical_item="TOILET_REPLACE_STANDARD",
            )
        ])
        suggestions = suggest_revisions(estimate)
        labels = [s.label for s in suggestions]
        assert "Add permit & inspection" in labels

    def test_no_permit_suggestion_when_permit_present(self):
        estimate = _make_estimate([
            LineItem(
                line_type="permit",
                description="Permit & inspection",
                quantity=1,
                unit="ea",
                unit_cost=100.0,
                total_cost=100.0,
            ),
            LineItem(
                line_type="labor",
                description="Toilet replacement",
                quantity=1,
                unit="ea",
                unit_cost=50.0,
                total_cost=50.0,
                canonical_item="TOILET_REPLACE_STANDARD",
            )
        ])
        suggestions = suggest_revisions(estimate)
        labels = [s.label for s in suggestions]
        assert "Add permit & inspection" not in labels

    def test_suggests_premium_fixtures(self):
        estimate = _make_estimate([
            LineItem(
                line_type="labor",
                description="Lavatory sink replace",
                quantity=1,
                unit="ea",
                unit_cost=50.0,
                total_cost=50.0,
                canonical_item="LAV_SINK_REPLACE",
            )
        ])
        suggestions = suggest_revisions(estimate)
        labels = [s.label for s in suggestions]
        assert "Upgrade to premium fixtures" in labels

    def test_suggests_repipe_for_multiple_bathrooms(self):
        estimate = _make_estimate([
            LineItem(
                line_type="labor",
                description="Toilet replacement",
                quantity=1,
                unit="ea",
                unit_cost=50.0,
                total_cost=50.0,
                canonical_item="TOILET_REPLACE_STANDARD",
            ),
            LineItem(
                line_type="labor",
                description="Shower valve replace",
                quantity=1,
                unit="ea",
                unit_cost=80.0,
                total_cost=80.0,
                canonical_item="SHOWER_VALVE_REPLACE",
            )
        ])
        suggestions = suggest_revisions(estimate)
        labels = [s.label for s in suggestions]
        assert "Get a whole-house repipe quote" in labels

    def test_combo_fixture_not_double_counted(self):
        estimate = _make_estimate([
            LineItem(
                line_type="labor",
                description="Tub shower combo replace",
                quantity=1,
                unit="ea",
                unit_cost=120.0,
                total_cost=120.0,
                canonical_item="TUB_SHOWER_COMBO_REPLACE",
            )
        ])
        suggestions = suggest_revisions(estimate)
        labels = [s.label for s in suggestions]
        assert "Get a whole-house repipe quote" not in labels

    def test_caps_at_three_suggestions(self):
        estimate = _make_estimate([
            LineItem(
                line_type="labor",
                description="Water heater replacement",
                quantity=1,
                unit="ea",
                unit_cost=100.0,
                total_cost=100.0,
                canonical_item="WH_50G_GAS_STANDARD",
            ),
            LineItem(
                line_type="labor",
                description="Toilet replacement",
                quantity=1,
                unit="ea",
                unit_cost=50.0,
                total_cost=50.0,
                canonical_item="TOILET_REPLACE_STANDARD",
            )
        ])
        suggestions = suggest_revisions(estimate)
        assert len(suggestions) <= 3
