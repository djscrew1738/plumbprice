"""Tests for catalog_importer service."""

import pytest
import pytest_asyncio
from io import BytesIO
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.suppliers import Supplier
from app.services.catalog_importer import (
    import_supplier_products,
    import_labor_templates,
    generate_product_csv_template,
    generate_labor_csv_template,
    _clean_float,
    _clean_int,
    _clean_str,
    _clean_bool,
    _clean_list,
)


@pytest_asyncio.fixture
async def seeded_suppliers(db_session: AsyncSession):
    """Seed 3 DFW suppliers for import tests (idempotent)."""
    from sqlalchemy import select
    existing = await db_session.execute(select(Supplier.slug))
    existing_slugs = {r[0] for r in existing.all()}

    suppliers = []
    for slug, name, city in [
        ("ferguson", "Ferguson Enterprises", "Dallas"),
        ("moore_supply", "Moore Supply Co.", "Dallas"),
        ("apex", "Apex Supply", "Fort Worth"),
    ]:
        if slug not in existing_slugs:
            s = Supplier(name=name, slug=slug, type="wholesale", city=city)
            db_session.add(s)
            suppliers.append(s)

    if suppliers:
        await db_session.commit()
    return suppliers


# ─── Validators ─────────────────────────────────────────────────────────────

class TestValidators:
    def test_clean_bool_defaults(self):
        assert _clean_bool(None) is True
        assert _clean_bool("") is True
        assert _clean_bool("true") is True
        assert _clean_bool("1") is True
        assert _clean_bool("yes") is True
        assert _clean_bool("false") is False
        assert _clean_bool("0") is False
        assert _clean_bool("no") is False

    def test_clean_float_required(self):
        assert _clean_float("12.50", "cost", min_val=0) == 12.5
        with pytest.raises(ValueError):
            _clean_float(None, "cost")
        with pytest.raises(ValueError):
            _clean_float("abc", "cost")
        with pytest.raises(ValueError):
            _clean_float("-1", "cost", min_val=0)

    def test_clean_int_optional(self):
        assert _clean_int("3", "rating", min_val=1, max_val=5) == 3
        assert _clean_int(None, "rating") is None
        assert _clean_int("", "rating") is None
        with pytest.raises(ValueError):
            _clean_int("abc", "rating")
        with pytest.raises(ValueError):
            _clean_int("0", "rating", min_val=1)
        with pytest.raises(ValueError):
            _clean_int("6", "rating", max_val=5)

    def test_clean_str_required(self):
        assert _clean_str("hello", "name") == "hello"
        with pytest.raises(ValueError):
            _clean_str(None, "name")
        with pytest.raises(ValueError):
            _clean_str("", "name")

    def test_clean_str_optional(self):
        assert _clean_str("", "name", required=False) == ""
        assert _clean_str(None, "name", required=False) == ""

    def test_clean_list(self):
        assert _clean_list("a,b,c") == ["a", "b", "c"]
        assert _clean_list("  a  ,  b  ") == ["a", "b"]
        assert _clean_list(None) is None
        assert _clean_list("") is None


# ─── Product import ─────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_import_products_dry_run(db_session, seeded_suppliers):
    csv = (
        "canonical_item,supplier_slug,name,cost,unit,category,sub_category,tags\n"
        "toilet.test,ferguson,Test Toilet,299.99,ea,fixture,residential,\"smart,ada\"\n"
    )
    result = await import_supplier_products(db_session, csv, dry_run=True)

    assert result.dry_run is True
    assert result.total_rows == 1
    assert result.created == 1
    assert result.updated == 0
    assert result.errors == 0
    assert result.rows[0].status == "created"
    assert result.rows[0].canonical_item == "toilet.test"


@pytest.mark.asyncio
async def test_import_products_missing_required_column(db_session):
    csv = "name,cost\nTest,10\n"
    result = await import_supplier_products(db_session, csv, dry_run=True)
    assert result.errors == 1
    assert "Missing required columns" in result.rows[0].message


@pytest.mark.asyncio
async def test_import_products_unknown_supplier(db_session, seeded_suppliers):
    csv = "canonical_item,supplier_slug,name,cost\nitem.1,unknown_supplier,Test,10\n"
    result = await import_supplier_products(db_session, csv, dry_run=True)
    assert result.errors == 1
    assert "Unknown supplier slug" in result.rows[0].message


@pytest.mark.asyncio
async def test_import_products_invalid_cost(db_session, seeded_suppliers):
    csv = "canonical_item,supplier_slug,name,cost\nitem.1,ferguson,Test,abc\n"
    result = await import_supplier_products(db_session, csv, dry_run=True)
    assert result.errors == 1
    assert "cost must be a number" in result.rows[0].message


@pytest.mark.asyncio
async def test_import_products_commits_to_db(db_session, seeded_suppliers):
    csv = (
        "canonical_item,supplier_slug,name,cost\n"
        "toilet.commit,ferguson,Commit Toilet,399.00\n"
    )
    result = await import_supplier_products(db_session, csv, dry_run=False)

    assert result.dry_run is False
    assert result.created == 1

    from app.models.suppliers import SupplierProduct
    from sqlalchemy import select
    row = await db_session.execute(
        select(SupplierProduct).where(SupplierProduct.canonical_item == "toilet.commit")
    )
    product = row.scalar_one()
    assert product.name == "Commit Toilet"
    assert product.cost == 399.0


@pytest.mark.asyncio
async def test_import_products_updates_existing(db_session, seeded_suppliers):
    csv1 = "canonical_item,supplier_slug,name,cost\nitem.up,ferguson,Original,100\n"
    await import_supplier_products(db_session, csv1, dry_run=False)

    csv2 = "canonical_item,supplier_slug,name,cost\nitem.up,ferguson,Updated,150\n"
    result = await import_supplier_products(db_session, csv2, dry_run=False)

    assert result.updated == 1

    from app.models.suppliers import SupplierProduct
    from sqlalchemy import select
    row = await db_session.execute(
        select(SupplierProduct).where(SupplierProduct.canonical_item == "item.up")
    )
    product = row.scalar_one()
    assert product.name == "Updated"
    assert product.cost == 150.0


# ─── Labor import ───────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_import_labor_dry_run(db_session):
    csv = (
        "code,name,category,base_hours\n"
        "TEST_SMART_TOILET,Smart Toilet Install,service,2.5\n"
    )
    result = await import_labor_templates(db_session, csv, dry_run=True)

    assert result.dry_run is True
    assert result.total_rows == 1
    assert result.created == 1
    assert result.errors == 0
    assert result.rows[0].status == "created"
    assert result.rows[0].code == "TEST_SMART_TOILET"


@pytest.mark.asyncio
async def test_import_labor_with_all_fields(db_session):
    csv = (
        "code,name,category,base_hours,lead_rate,helper_required,helper_rate,"
        "helper_hours,disposal_hours,tags,difficulty_rating,required_certifications\n"
        "TEST_FULL,Full Template,commercial,3.0,200,true,60,1.5,0.5,\"smart,commercial\",3,\"backflow,medical_gas\"\n"
    )
    result = await import_labor_templates(db_session, csv, dry_run=False)

    assert result.created == 1

    from app.models.labor import LaborTemplate
    from sqlalchemy import select
    row = await db_session.execute(
        select(LaborTemplate).where(LaborTemplate.code == "TEST_FULL")
    )
    tmpl = row.scalar_one()
    assert tmpl.name == "Full Template"
    assert tmpl.category == "commercial"
    assert tmpl.base_hours == 3.0
    assert tmpl.lead_rate == 200.0
    assert tmpl.helper_required is True
    assert tmpl.helper_rate == 60.0
    assert tmpl.helper_hours == 1.5
    assert tmpl.disposal_hours == 0.5
    assert tmpl.tags == ["smart", "commercial"]
    assert tmpl.difficulty_rating == 3
    assert tmpl.required_certifications == ["backflow", "medical_gas"]


@pytest.mark.asyncio
async def test_import_labor_invalid_difficulty(db_session):
    csv = "code,name,category,base_hours,difficulty_rating\nTEST_BAD,Bad,service,1,6\n"
    result = await import_labor_templates(db_session, csv, dry_run=True)
    assert result.errors == 1
    assert "difficulty_rating must be <= 5" in result.rows[0].message


# ─── Template generation ────────────────────────────────────────────────────

def test_generate_product_csv_template():
    template = generate_product_csv_template()
    assert "canonical_item" in template
    assert "supplier_slug" in template
    assert "name" in template
    assert "cost" in template


def test_generate_labor_csv_template():
    template = generate_labor_csv_template()
    assert "code" in template
    assert "name" in template
    assert "category" in template
    assert "base_hours" in template
