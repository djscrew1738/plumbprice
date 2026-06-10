#!/usr/bin/env python3
"""Seed script for expanded catalog (v5.8.0).

Loads expanded_catalog.json and expanded_labor.json into the database.
Uses upsert logic to avoid duplicates.
"""

import asyncio
import json
import os
import sys
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy import select

from app.config import settings
from app.database import Base
from app.models.suppliers import Supplier, SupplierProduct, SupplierPriceHistory
from app.models.labor import LaborTemplate


DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "app", "services", "data_sources")


def load_json(filename: str) -> dict:
    path = os.path.join(DATA_DIR, filename)
    with open(path, "r") as f:
        return json.load(f)


async def seed():
    print(f"Connecting to database at {settings.database_url}...")
    engine = create_async_engine(settings.database_url, echo=False)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as session:
        # -- Load suppliers ----------------------------------------------------
        sup_result = await session.execute(select(Supplier))
        suppliers = {s.slug: s for s in sup_result.scalars().all()}
        if len(suppliers) < 3:
            print("WARNING: Expected 3 suppliers (ferguson, moore_supply, apex). Run seed_db.py first.")

        # -- Seed expanded catalog items ---------------------------------------
        catalog_data = load_json("expanded_catalog.json")
        items = catalog_data.get("items", [])
        print(f"\nSeeding/Updating {len(items)} expanded catalog items...")

        created_count = 0
        updated_count = 0
        skipped_count = 0

        for item in items:
            canonical_item = item["canonical_item"]
            category = item.get("category")
            sub_category = item.get("sub_category")
            manufacturer = item.get("manufacturer")
            tags = item.get("tags")

            for slug in ["ferguson", "moore_supply", "apex"]:
                if slug not in suppliers:
                    skipped_count += 1
                    continue

                # Apply a small cost variance per supplier (+/- 5-15%)
                base_cost = item["cost"]
                variance = {"ferguson": 1.0, "moore_supply": 1.08, "apex": 0.95}
                cost = round(base_cost * variance[slug], 2)

                result = await session.execute(
                    select(SupplierProduct).where(
                        SupplierProduct.supplier_id == suppliers[slug].id,
                        SupplierProduct.canonical_item == canonical_item,
                    )
                )
                existing = result.scalar_one_or_none()

                if existing:
                    existing.name = item["name"]
                    existing.cost = cost
                    existing.manufacturer = manufacturer
                    existing.category = category
                    existing.sub_category = sub_category
                    existing.tags = tags
                    existing.in_stock = True
                    existing.confidence_score = 1.0
                    updated_count += 1
                else:
                    product = SupplierProduct(
                        supplier_id=suppliers[slug].id,
                        canonical_item=canonical_item,
                        name=item["name"],
                        cost=cost,
                        manufacturer=manufacturer,
                        category=category,
                        sub_category=sub_category,
                        tags=tags,
                        unit="ea",
                        in_stock=True,
                        confidence_score=1.0,
                        is_active=True,
                    )
                    session.add(product)
                    await session.flush()
                    session.add(SupplierPriceHistory(
                        product_id=product.id,
                        cost=cost,
                        source="seed_v5_8_0",
                    ))
                    created_count += 1

        print(f"  + Created: {created_count}, Updated: {updated_count}, Skipped: {skipped_count}")

        # -- Seed expanded labor templates -------------------------------------
        labor_data = load_json("expanded_labor.json")
        templates = labor_data.get("templates", [])
        print(f"\nSeeding/Updating {len(templates)} expanded labor templates...")

        labor_created = 0
        labor_updated = 0

        for tmpl in templates:
            code = tmpl["code"]
            result = await session.execute(select(LaborTemplate).where(LaborTemplate.code == code))
            existing = result.scalar_one_or_none()

            config_json = {
                "access_multipliers": {
                    "first_floor": 1.0, "second_floor": 1.2, "attic": 1.5,
                    "crawlspace": 1.3, "slab": 1.4, "basement": 1.1,
                },
                "urgency_multipliers": {
                    "standard": 1.0, "same_day": 1.35, "emergency": 2.0,
                },
                "applicable_assemblies": [],
                "notes": tmpl.get("notes", ""),
            }

            data = {
                "name": tmpl["name"],
                "category": tmpl["category"],
                "base_hours": tmpl["base_hours"],
                "lead_rate": tmpl.get("lead_rate", 185.0),
                "helper_required": tmpl.get("helper_required", False),
                "helper_rate": tmpl.get("helper_rate", 55.0),
                "helper_hours": tmpl.get("helper_hours"),
                "disposal_hours": tmpl.get("disposal_hours", 0.25),
                "tags": tmpl.get("tags"),
                "difficulty_rating": tmpl.get("difficulty_rating", 2),
                "required_certifications": tmpl.get("required_certifications"),
                "min_hours": tmpl.get("min_hours"),
                "max_hours": tmpl.get("max_hours"),
                "is_active": True,
                "config_json": config_json,
            }

            if existing:
                for k, v in data.items():
                    setattr(existing, k, v)
                labor_updated += 1
            else:
                lt = LaborTemplate(code=code, **data)
                session.add(lt)
                labor_created += 1

        print(f"  + Created: {labor_created}, Updated: {labor_updated}")

        await session.commit()
        print("\nExpanded catalog seed complete!")

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(seed())
