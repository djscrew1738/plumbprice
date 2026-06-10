"""Bulk CSV import service for canonical items, labor templates, and material assemblies.

Supports dry-run mode for previewing changes without writing to the database.
"""
from __future__ import annotations

import csv
import io
from dataclasses import dataclass, field
from typing import Any

import structlog
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.suppliers import Supplier, SupplierProduct, SupplierPriceHistory
from app.models.labor import LaborTemplate

logger = structlog.get_logger()


# ---------------------------------------------------------------------------
# Row-level result
# ---------------------------------------------------------------------------

@dataclass
class ImportRowResult:
    row_number: int
    status: str = ""  # "created", "updated", "skipped", "error"
    canonical_item: str | None = None
    code: str | None = None
    message: str = ""
    details: dict[str, Any] = field(default_factory=dict)


@dataclass
class ImportResult:
    total_rows: int = 0
    created: int = 0
    updated: int = 0
    skipped: int = 0
    errors: int = 0
    rows: list[ImportRowResult] = field(default_factory=list)
    dry_run: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "dry_run": self.dry_run,
            "total_rows": self.total_rows,
            "created": self.created,
            "updated": self.updated,
            "skipped": self.skipped,
            "errors": self.errors,
            "rows": [
                {
                    "row_number": r.row_number,
                    "status": r.status,
                    "canonical_item": r.canonical_item,
                    "code": r.code,
                    "message": r.message,
                    "details": r.details,
                }
                for r in self.rows
            ],
        }


# ---------------------------------------------------------------------------
# Validators
# ---------------------------------------------------------------------------

def _clean_bool(val: str | None, default: bool = True) -> bool:
    if val is None or str(val).strip() == "":
        return default
    return str(val).strip().lower() in {"true", "1", "yes", "y"}


def _clean_float(val: str | None, field_name: str, min_val: float | None = None, max_val: float | None = None) -> float:
    if val is None or str(val).strip() == "":
        raise ValueError(f"{field_name} is required")
    try:
        f = float(str(val).strip())
    except ValueError:
        raise ValueError(f"{field_name} must be a number, got '{val}'")
    if min_val is not None and f < min_val:
        raise ValueError(f"{field_name} must be >= {min_val}, got {f}")
    if max_val is not None and f > max_val:
        raise ValueError(f"{field_name} must be <= {max_val}, got {f}")
    return f


def _clean_int(val: str | None, field_name: str, min_val: int | None = None, max_val: int | None = None) -> int | None:
    if val is None or str(val).strip() == "":
        return None
    try:
        i = int(str(val).strip())
    except ValueError:
        raise ValueError(f"{field_name} must be an integer, got '{val}'")
    if min_val is not None and i < min_val:
        raise ValueError(f"{field_name} must be >= {min_val}, got {i}")
    if max_val is not None and i > max_val:
        raise ValueError(f"{field_name} must be <= {max_val}, got {i}")
    return i


def _clean_str(val: str | None, field_name: str, required: bool = True) -> str:
    if val is None or str(val).strip() == "":
        if required:
            raise ValueError(f"{field_name} is required")
        return ""
    return str(val).strip()


def _clean_list(val: str | None) -> list[str] | None:
    if val is None or str(val).strip() == "":
        return None
    return [v.strip() for v in str(val).split(",") if v.strip()]


# ---------------------------------------------------------------------------
# Supplier product import
# ---------------------------------------------------------------------------

REQUIRED_PRODUCT_COLS = {"canonical_item", "supplier_slug", "name", "cost"}
OPTIONAL_PRODUCT_COLS = {
    "sku", "unit", "manufacturer", "category", "sub_category",
    "tags", "in_stock", "lead_time", "msrp", "list_price",
}
ALL_PRODUCT_COLS = REQUIRED_PRODUCT_COLS | OPTIONAL_PRODUCT_COLS


async def import_supplier_products(
    db: AsyncSession,
    csv_content: str | bytes,
    dry_run: bool = False,
) -> ImportResult:
    """Import or update supplier products from a CSV.

    Expected columns: canonical_item, supplier_slug, sku, name, cost, unit,
    manufacturer, category, sub_category, tags, in_stock, lead_time, msrp, list_price
    """
    result = ImportResult(dry_run=dry_run)

    if isinstance(csv_content, bytes):
        csv_content = csv_content.decode("utf-8-sig")

    reader = csv.DictReader(io.StringIO(csv_content))
    if reader.fieldnames is None:
        result.errors += 1
        result.rows.append(ImportRowResult(
            row_number=0, status="error",
            message="Could not read CSV headers",
        ))
        return result

    # Validate headers
    headers = set(reader.fieldnames)
    missing_required = REQUIRED_PRODUCT_COLS - headers
    if missing_required:
        result.errors += 1
        result.rows.append(ImportRowResult(
            row_number=0, status="error",
            message=f"Missing required columns: {sorted(missing_required)}",
        ))
        return result

    # Pre-load suppliers into memory
    sup_result = await db.execute(select(Supplier))
    suppliers = {s.slug: s for s in sup_result.scalars().all()}

    # Pre-load existing products for duplicate detection
    prod_result = await db.execute(
        select(SupplierProduct, Supplier.slug)
        .join(Supplier, SupplierProduct.supplier_id == Supplier.id)
    )
    existing_products: dict[tuple[str, str], SupplierProduct] = {}
    for prod, slug in prod_result.all():
        existing_products[(slug, prod.canonical_item)] = prod

    for row_num, row in enumerate(reader, start=2):  # start at 2 because header is row 1
        result.total_rows += 1
        row_result = ImportRowResult(row_number=row_num)

        try:
            canonical_item = _clean_str(row.get("canonical_item"), "canonical_item")
            supplier_slug = _clean_str(row.get("supplier_slug"), "supplier_slug")
            row_result.canonical_item = canonical_item

            if supplier_slug not in suppliers:
                raise ValueError(f"Unknown supplier slug: '{supplier_slug}'")

            name = _clean_str(row.get("name"), "name")
            cost = _clean_float(row.get("cost"), "cost", min_val=0.01)
            sku = _clean_str(row.get("sku"), "sku", required=False) or None
            unit = _clean_str(row.get("unit"), "unit", required=False) or "ea"
            manufacturer = _clean_str(row.get("manufacturer"), "manufacturer", required=False) or None
            category = _clean_str(row.get("category"), "category", required=False) or None
            sub_category = _clean_str(row.get("sub_category"), "sub_category", required=False) or None
            tags = _clean_list(row.get("tags"))
            in_stock = _clean_bool(row.get("in_stock"), default=True)
            lead_time = _clean_str(row.get("lead_time"), "lead_time", required=False) or None
            msrp = _clean_float(row.get("msrp"), "msrp", min_val=0) if row.get("msrp") else None
            list_price = _clean_float(row.get("list_price"), "list_price", min_val=0) if row.get("list_price") else None

            key = (supplier_slug, canonical_item)
            existing = existing_products.get(key)

            if existing:
                row_result.status = "updated"
                row_result.message = f"Updated {supplier_slug}/{canonical_item}"
                if not dry_run:
                    old_cost = existing.cost
                    existing.name = name
                    existing.cost = cost
                    existing.sku = sku
                    existing.unit = unit
                    existing.manufacturer = manufacturer
                    existing.category = category
                    existing.sub_category = sub_category
                    existing.tags = tags
                    existing.in_stock = in_stock
                    existing.lead_time = lead_time
                    existing.msrp = msrp
                    existing.list_price = list_price
                    existing.confidence_score = 1.0
                    if abs(old_cost - cost) > 0.001:
                        db.add(SupplierPriceHistory(
                            product_id=existing.id,
                            cost=cost,
                            source="bulk_import",
                        ))
                result.updated += 1
            else:
                row_result.status = "created"
                row_result.message = f"Created {supplier_slug}/{canonical_item}"
                if not dry_run:
                    supplier = suppliers[supplier_slug]
                    product = SupplierProduct(
                        supplier_id=supplier.id,
                        canonical_item=canonical_item,
                        sku=sku,
                        name=name,
                        cost=cost,
                        unit=unit,
                        manufacturer=manufacturer,
                        category=category,
                        sub_category=sub_category,
                        tags=tags,
                        in_stock=in_stock,
                        lead_time=lead_time,
                        msrp=msrp,
                        list_price=list_price,
                        confidence_score=1.0,
                        is_active=True,
                    )
                    db.add(product)
                    await db.flush()
                    db.add(SupplierPriceHistory(
                        product_id=product.id,
                        cost=cost,
                        source="bulk_import",
                    ))
                result.created += 1

            row_result.details = {
                "supplier": supplier_slug,
                "name": name,
                "cost": cost,
                "sku": sku,
                "category": category,
                "sub_category": sub_category,
            }

        except ValueError as exc:
            row_result.status = "error"
            row_result.message = str(exc)
            result.errors += 1
        except Exception as exc:
            row_result.status = "error"
            row_result.message = f"Unexpected error: {exc}"
            result.errors += 1
            logger.error("catalog_import.product_row_error", row=row_num, error=str(exc))

        result.rows.append(row_result)

    if not dry_run:
        await db.commit()
        logger.info(
            "catalog_import.products_complete",
            total=result.total_rows,
            created=result.created,
            updated=result.updated,
            errors=result.errors,
        )

    return result


# ---------------------------------------------------------------------------
# Labor template import
# ---------------------------------------------------------------------------

REQUIRED_LABOR_COLS = {"code", "name", "category", "base_hours"}
OPTIONAL_LABOR_COLS = {
    "lead_rate", "helper_required", "helper_rate", "helper_hours",
    "disposal_hours", "tags", "difficulty_rating", "required_certifications",
    "min_hours", "max_hours",
}
ALL_LABOR_COLS = REQUIRED_LABOR_COLS | OPTIONAL_LABOR_COLS


async def import_labor_templates(
    db: AsyncSession,
    csv_content: str | bytes,
    dry_run: bool = False,
) -> ImportResult:
    """Import or update labor templates from a CSV.

    Expected columns: code, name, category, base_hours, lead_rate,
    helper_required, helper_rate, helper_hours, disposal_hours,
    tags, difficulty_rating, required_certifications, min_hours, max_hours
    """
    result = ImportResult(dry_run=dry_run)

    if isinstance(csv_content, bytes):
        csv_content = csv_content.decode("utf-8-sig")

    reader = csv.DictReader(io.StringIO(csv_content))
    if reader.fieldnames is None:
        result.errors += 1
        result.rows.append(ImportRowResult(
            row_number=0, status="error",
            message="Could not read CSV headers",
        ))
        return result

    headers = set(reader.fieldnames)
    missing_required = REQUIRED_LABOR_COLS - headers
    if missing_required:
        result.errors += 1
        result.rows.append(ImportRowResult(
            row_number=0, status="error",
            message=f"Missing required columns: {sorted(missing_required)}",
        ))
        return result

    # Pre-load existing templates
    tmpl_result = await db.execute(select(LaborTemplate))
    existing_templates: dict[str, LaborTemplate] = {t.code: t for t in tmpl_result.scalars().all()}

    for row_num, row in enumerate(reader, start=2):
        result.total_rows += 1
        row_result = ImportRowResult(row_number=row_num)

        try:
            code = _clean_str(row.get("code"), "code")
            row_result.code = code

            name = _clean_str(row.get("name"), "name")
            category = _clean_str(row.get("category"), "category")
            base_hours = _clean_float(row.get("base_hours"), "base_hours", min_val=0.01)
            lead_rate = _clean_float(row.get("lead_rate"), "lead_rate", min_val=1) if row.get("lead_rate") else 185.0
            helper_required = _clean_bool(row.get("helper_required"), default=False)
            helper_rate = _clean_float(row.get("helper_rate"), "helper_rate", min_val=1) if row.get("helper_rate") else 55.0
            helper_hours = _clean_float(row.get("helper_hours"), "helper_hours", min_val=0) if row.get("helper_hours") else None
            disposal_hours = _clean_float(row.get("disposal_hours"), "disposal_hours", min_val=0) if row.get("disposal_hours") else 0.25
            tags = _clean_list(row.get("tags"))
            difficulty_rating = _clean_int(row.get("difficulty_rating"), "difficulty_rating", min_val=1, max_val=5)
            required_certifications = _clean_list(row.get("required_certifications"))
            min_hours = _clean_float(row.get("min_hours"), "min_hours", min_val=0) if row.get("min_hours") else None
            max_hours = _clean_float(row.get("max_hours"), "max_hours", min_val=0) if row.get("max_hours") else None

            existing = existing_templates.get(code)

            # Default config_json preserves existing access/urgency multipliers if updating
            config_json = existing.config_json if existing else {
                "access_multipliers": {
                    "first_floor": 1.0, "second_floor": 1.2, "attic": 1.5,
                    "crawlspace": 1.3, "slab": 1.4, "basement": 1.1,
                },
                "urgency_multipliers": {
                    "standard": 1.0, "same_day": 1.35, "emergency": 2.0,
                },
                "applicable_assemblies": [],
                "notes": "",
            }

            data = {
                "name": name,
                "category": category,
                "base_hours": base_hours,
                "lead_rate": lead_rate,
                "helper_required": helper_required,
                "helper_rate": helper_rate,
                "helper_hours": helper_hours,
                "disposal_hours": disposal_hours,
                "tags": tags,
                "difficulty_rating": difficulty_rating,
                "required_certifications": required_certifications,
                "min_hours": min_hours,
                "max_hours": max_hours,
                "is_active": True,
                "config_json": config_json,
            }

            if existing:
                row_result.status = "updated"
                row_result.message = f"Updated labor template '{code}'"
                if not dry_run:
                    for k, v in data.items():
                        setattr(existing, k, v)
                result.updated += 1
            else:
                row_result.status = "created"
                row_result.message = f"Created labor template '{code}'"
                if not dry_run:
                    lt = LaborTemplate(code=code, **data)
                    db.add(lt)
                result.created += 1

            row_result.details = {
                "code": code,
                "name": name,
                "category": category,
                "base_hours": base_hours,
                "difficulty_rating": difficulty_rating,
            }

        except ValueError as exc:
            row_result.status = "error"
            row_result.message = str(exc)
            result.errors += 1
        except Exception as exc:
            row_result.status = "error"
            row_result.message = f"Unexpected error: {exc}"
            result.errors += 1
            logger.error("catalog_import.labor_row_error", row=row_num, error=str(exc))

        result.rows.append(row_result)

    if not dry_run:
        await db.commit()
        logger.info(
            "catalog_import.labor_complete",
            total=result.total_rows,
            created=result.created,
            updated=result.updated,
            errors=result.errors,
        )

    return result


# ---------------------------------------------------------------------------
# CSV template generation
# ---------------------------------------------------------------------------

def generate_product_csv_template() -> str:
    """Return a CSV header row for supplier product imports."""
    return ",".join(sorted(ALL_PRODUCT_COLS)) + "\n"


def generate_labor_csv_template() -> str:
    """Return a CSV header row for labor template imports."""
    return ",".join(sorted(ALL_LABOR_COLS)) + "\n"
