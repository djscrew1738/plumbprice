"""Tests for scoped (per-customer / per-address) memory (Track D4)."""
import pytest

from app.models.agent_memory import AgentMemory
from app.services.scoped_memory import (
    normalize_address_key,
    normalize_customer_key,
    recall_for_address,
    recall_for_customer,
)


def test_customer_key_email_normalization():
    assert normalize_customer_key(email="  Foo@BAR.com ") == "foo@bar.com"
    assert normalize_customer_key(email="not-an-email") is None


def test_customer_key_phone_normalization():
    assert normalize_customer_key(phone="(214) 555-0173") == "2145550173"
    assert normalize_customer_key(phone="+1 214 555 0173") == "2145550173"
    assert normalize_customer_key(phone="123") is None


def test_customer_key_email_takes_precedence():
    k = normalize_customer_key(email="alice@example.com", phone="2145550173")
    assert k == "alice@example.com"


def test_address_key_stable_across_punctuation():
    a = normalize_address_key(street="123 Main St.", zip_code="75201")
    b = normalize_address_key(street="123  main  st", zip_code="75201")
    assert a == b
    assert a is not None
    assert len(a) == 24


def test_address_key_zip_changes_key():
    a = normalize_address_key(street="123 Main St", zip_code="75201")
    b = normalize_address_key(street="123 Main St", zip_code="75202")
    assert a != b


def test_address_key_empty_returns_none():
    assert normalize_address_key(street="") is None
    assert normalize_address_key(street=None) is None
    assert normalize_address_key(street="   ", zip_code="75201") is None


@pytest.mark.asyncio
async def test_recall_for_customer_filters_by_key(db_session):
    db_session.add(AgentMemory(
        user_id=42, kind="customer", content="prefers tankless WH",
        importance=0.8, metadata_json={"customer_key": "alice@example.com"},
    ))
    db_session.add(AgentMemory(
        user_id=42, kind="customer", content="other person",
        importance=0.9, metadata_json={"customer_key": "bob@example.com"},
    ))
    db_session.add(AgentMemory(
        user_id=99, kind="customer", content="wrong user",
        importance=0.9, metadata_json={"customer_key": "alice@example.com"},
    ))
    await db_session.flush()

    rows = await recall_for_customer(db_session, user_id=42, customer_email="ALICE@example.com")
    assert len(rows) == 1
    assert rows[0].content == "prefers tankless WH"


@pytest.mark.asyncio
async def test_recall_for_customer_empty_when_no_key(db_session):
    rows = await recall_for_customer(db_session, user_id=42)
    assert rows == []


@pytest.mark.asyncio
async def test_recall_for_address_filters_by_key(db_session):
    key = normalize_address_key(street="555 Oak Ave", zip_code="76012")
    db_session.add(AgentMemory(
        user_id=7, kind="job_history",
        content="hose bibb on north side froze in 2024",
        importance=0.7, metadata_json={"address_key": key, "street": "555 Oak Ave"},
    ))
    db_session.add(AgentMemory(
        user_id=7, kind="job_history", content="different house",
        importance=0.7, metadata_json={"address_key": "deadbeef" * 3},
    ))
    await db_session.flush()

    rows = await recall_for_address(db_session, user_id=7, street="555 oak ave.", zip_code="76012")
    assert len(rows) == 1
    assert "froze" in rows[0].content


@pytest.mark.asyncio
async def test_recall_orders_by_importance(db_session):
    key = normalize_address_key(street="1 Pine", zip_code="75001")
    for content, imp in [("low", 0.3), ("high", 0.9), ("mid", 0.6)]:
        db_session.add(AgentMemory(
            user_id=1, kind="job_history", content=content,
            importance=imp, metadata_json={"address_key": key},
        ))
    await db_session.flush()
    rows = await recall_for_address(db_session, user_id=1, street="1 Pine", zip_code="75001")
    assert [r.content for r in rows] == ["high", "mid", "low"]
