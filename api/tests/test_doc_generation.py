"""Tests for doc_generation service.

LLM is monkey-patched per test so we cover both the LLM-success and the
static-fallback paths without hitting Ollama / cloud.
"""
from __future__ import annotations

import pytest

from app.models.estimates import Estimate, EstimateLineItem
from app.services import doc_generation


def _make_est(**overrides) -> Estimate:
    est = Estimate(
        title=overrides.get("title", "Toilet replace"),
        job_type=overrides.get("job_type", "service"),
        labor_total=overrides.get("labor_total", 350.0),
        materials_total=overrides.get("materials_total", 250.0),
        tax_total=overrides.get("tax_total", 21.0),
        grand_total=overrides.get("grand_total", 750.0),
        county=overrides.get("county", "Tarrant"),
    )
    est.line_items = overrides.get("line_items", [
        EstimateLineItem(line_type="labor", description="Remove and replace toilet",
                         quantity=1, unit_cost=350, total_cost=350, sort_order=1),
        EstimateLineItem(line_type="material", description="Toilet (2-piece, std height)",
                         quantity=1, unit_cost=250, total_cost=250, sort_order=2),
    ])
    return est


@pytest.mark.asyncio
async def test_cover_letter_llm_success(monkeypatch):
    async def fake_complete(self, system, user, **kw):  # noqa: ARG001
        return "Hi Sue, here's your fixed-price proposal..."
    monkeypatch.setattr(doc_generation.llm_service.__class__, "complete", fake_complete)
    est = _make_est()
    out = await doc_generation.generate_cover_letter(est, customer_name="Sue")
    assert out["source"] == "llm"
    assert "Sue" in out["text"]


@pytest.mark.asyncio
async def test_cover_letter_static_fallback(monkeypatch):
    async def fake_complete(self, system, user, **kw):  # noqa: ARG001
        return None
    monkeypatch.setattr(doc_generation.llm_service.__class__, "complete", fake_complete)
    est = _make_est()
    out = await doc_generation.generate_cover_letter(est, customer_name="Mike")
    assert out["source"] == "static"
    assert "Mike" in out["text"]
    assert "CTL Plumbing" in out["text"]
    assert "$750" in out["text"]


@pytest.mark.asyncio
async def test_scope_of_work_static_has_required_sections(monkeypatch):
    async def fake_complete(self, system, user, **kw):  # noqa: ARG001
        return None
    monkeypatch.setattr(doc_generation.llm_service.__class__, "complete", fake_complete)
    est = _make_est()
    out = await doc_generation.generate_scope_of_work(est)
    assert out["source"] == "static"
    for header in ("Work to be performed", "Materials", "Code & inspection", "Exclusions"):
        assert header in out["text"]


@pytest.mark.asyncio
async def test_change_order_delta_and_static(monkeypatch):
    async def fake_complete(self, system, user, **kw):  # noqa: ARG001
        return None
    monkeypatch.setattr(doc_generation.llm_service.__class__, "complete", fake_complete)
    original = _make_est(grand_total=750.0)
    revised = _make_est(grand_total=950.0)
    out = await doc_generation.generate_change_order(original, revised, reason="extra cleanout")
    assert out["source"] == "static"
    assert out["delta"] == 200.0
    assert "increase" in out["text"]
    assert "$200.00" in out["text"]


@pytest.mark.asyncio
async def test_change_order_decrease_direction():
    original = _make_est(grand_total=900.0)
    revised = _make_est(grand_total=800.0)
    out = await doc_generation.generate_change_order(original, revised)
    assert out["delta"] == -100.0
    if out["source"] == "static":
        assert "decrease" in out["text"]


def test_facts_includes_line_items():
    est = _make_est()
    f = doc_generation._facts(est)
    assert "Tarrant" in f
    assert "Toilet (2-piece, std height)" in f
    assert "$750.00" in f
