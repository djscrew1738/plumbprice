"""Tests for v4.1 new services and routes."""
from __future__ import annotations

import pytest


# ── Geo service ───────────────────────────────────────────────────────────────

def test_geo_county_dallas():
    from app.services.geo_service import county_from_coordinates
    # Downtown Dallas: 32.7767° N, 96.7970° W
    assert county_from_coordinates(32.7767, -96.7970) == "Dallas"


def test_geo_county_tarrant():
    from app.services.geo_service import county_from_coordinates
    # Fort Worth: 32.7555° N, 97.3308° W
    assert county_from_coordinates(32.7555, -97.3308) == "Tarrant"


def test_geo_county_outside_dfw():
    from app.services.geo_service import county_from_coordinates
    # Austin, TX (not DFW)
    assert county_from_coordinates(30.2672, -97.7431) is None


def test_geo_county_collin():
    from app.services.geo_service import county_from_coordinates
    # Plano: 33.0198° N, 96.6989° W
    assert county_from_coordinates(33.0198, -96.6989) == "Collin"


# ── Price forecast slope ──────────────────────────────────────────────────────

def test_linear_slope_rising():
    from worker.tasks.price_forecast import _linear_slope
    xs = [0.0, 1.0, 2.0, 3.0]
    ys = [10.0, 11.0, 12.0, 13.0]
    slope = _linear_slope(xs, ys)
    assert abs(slope - 1.0) < 0.001


def test_linear_slope_flat():
    from worker.tasks.price_forecast import _linear_slope
    xs = [0.0, 1.0, 2.0, 3.0]
    ys = [10.0, 10.0, 10.0, 10.0]
    slope = _linear_slope(xs, ys)
    assert abs(slope) < 0.001


def test_linear_slope_falling():
    from worker.tasks.price_forecast import _linear_slope
    xs = [0.0, 1.0, 2.0, 3.0]
    ys = [13.0, 12.0, 11.0, 10.0]
    slope = _linear_slope(xs, ys)
    assert slope < 0


def test_linear_slope_single_point():
    from worker.tasks.price_forecast import _linear_slope
    assert _linear_slope([0.0], [10.0]) == 0.0


# ── Pricing corrections ───────────────────────────────────────────────────────

def test_compute_adjustment_underpriced():
    from app.services.pricing_corrections import _compute_adjustment
    # 10% over means actual > estimated → we're underpriced → suggest 1.10
    adj = _compute_adjustment(10.0)
    assert abs(adj - 1.10) < 0.001


def test_compute_adjustment_overpriced():
    from app.services.pricing_corrections import _compute_adjustment
    # -15% means actual < estimated → we're overpriced → suggest 0.85
    adj = _compute_adjustment(-15.0)
    assert abs(adj - 0.85) < 0.001


def test_compute_adjustment_capped():
    from app.services.pricing_corrections import _compute_adjustment
    # +50% should be capped at 1.30
    assert _compute_adjustment(50.0) == 1.30
    # -50% should be capped at 0.70
    assert _compute_adjustment(-50.0) == 0.70


def test_classify_variance_positive():
    from app.services.pricing_corrections import _classify_variance
    rec_type, rationale = _classify_variance(12.5)
    assert rec_type == "adjust_labor_hours"
    assert "higher than estimates" in rationale


def test_classify_variance_negative():
    from app.services.pricing_corrections import _classify_variance
    rec_type, rationale = _classify_variance(-8.0)
    assert rec_type == "adjust_material_markup"
    assert "lower than estimates" in rationale


# ── Model A/B results match ───────────────────────────────────────────────────

def test_model_ab_results_match_same():
    from app.services.model_ab import _results_match

    class FakeResult:
        def __init__(self, job_type, fixtures):
            self.job_type = job_type
            self.fixtures = fixtures

    a = FakeResult("service", [{"canonical_item": "toilet_elongated_standard"}])
    b = FakeResult("service", [{"canonical_item": "toilet_elongated_standard"}])
    assert _results_match(a, b) is True


def test_model_ab_results_match_different():
    from app.services.model_ab import _results_match

    class FakeResult:
        def __init__(self, job_type, fixtures):
            self.job_type = job_type
            self.fixtures = fixtures

    a = FakeResult("service", [{"canonical_item": "toilet_elongated_standard"}])
    b = FakeResult("service", [{"canonical_item": "kitchen_faucet_standard"}])
    assert _results_match(a, b) is False


# ── Geo API endpoint ──────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_geo_county_endpoint_dallas(test_client):
    resp = await test_client.get("/api/v3/geo/county?lat=32.7767&lng=-96.7970")
    assert resp.status_code == 200
    data = resp.json()
    assert data["county"] == "Dallas"
    assert data["in_dfw"] is True


@pytest.mark.asyncio
async def test_geo_county_endpoint_outside(test_client):
    resp = await test_client.get("/api/v3/geo/county?lat=30.2672&lng=-97.7431")
    assert resp.status_code == 200
    data = resp.json()
    assert data["county"] is None
    assert data["in_dfw"] is False


@pytest.mark.asyncio
async def test_geo_county_invalid_coords(test_client):
    resp = await test_client.get("/api/v3/geo/county?lat=999&lng=999")
    assert resp.status_code == 422
