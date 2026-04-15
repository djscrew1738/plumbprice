#!/usr/bin/env python3
"""
Seed script -- populates the database with:
- 3 DFW suppliers (Ferguson, Moore Supply, Apex)
- 80+ canonical items with pricing
- 15+ material assemblies
- 30+ labor templates
- Default markup rules

UPDATED: Now uses upsert logic to avoid duplicates.
"""

import asyncio
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy import select
from app.config import settings
from app.database import Base
from app.models.suppliers import Supplier, SupplierProduct
from app.models.labor import LaborTemplate, MaterialAssembly, MarkupRule
from app.services.supplier_service import CANONICAL_MAP, MATERIAL_ASSEMBLIES
from app.services.labor_engine import LABOR_TEMPLATES


async def seed():
    print(f"Connecting to database at {settings.database_url}...")
    engine = create_async_engine(settings.database_url, echo=False)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as session:
        # -- Suppliers ---------------------------------------------------------
        print("Seeding/Updating suppliers...")
        supplier_data = [
            {"name": "Ferguson Enterprises", "slug": "ferguson", "type": "wholesale",
             "website": "https://www.ferguson.com", "phone": "972-555-0101", "city": "Dallas"},
            {"name": "Moore Supply Co.", "slug": "moore_supply", "type": "wholesale",
             "website": "https://www.mooresupply.com", "phone": "214-555-0102", "city": "Dallas"},
            {"name": "Apex Supply", "slug": "apex", "type": "wholesale",
             "website": "https://www.apexsupply.com", "phone": "817-555-0103", "city": "Fort Worth"},
        ]

        supplier_ids = {}
        for sd in supplier_data:
            result = await session.execute(select(Supplier).where(Supplier.slug == sd["slug"]))
            existing = result.scalar_one_or_none()
            if existing:
                for k, v in sd.items():
                    setattr(existing, k, v)
                s = existing
            else:
                s = Supplier(**sd, is_active=True)
                session.add(s)
            
            await session.flush()
            supplier_ids[sd["slug"]] = s.id
            print(f"  + {sd['name']} (id={s.id})")

        # -- Supplier Products -------------------------------------------------
        print(f"\nSeeding/Updating canonical items x 3 suppliers...")
        count = 0
        for canonical_item, supplier_map in CANONICAL_MAP.items():
            for slug, data in supplier_map.items():
                if slug not in supplier_ids:
                    continue
                
                # Check for existing product
                result = await session.execute(
                    select(SupplierProduct).where(
                        SupplierProduct.supplier_id == supplier_ids[slug],
                        SupplierProduct.canonical_item == canonical_item
                    )
                )
                existing = result.scalar_one_or_none()
                
                if existing:
                    existing.cost = data["cost"]
                    existing.name = data["name"]
                    existing.sku = data.get("sku")
                else:
                    product = SupplierProduct(
                        supplier_id=supplier_ids[slug],
                        canonical_item=canonical_item,
                        sku=data.get("sku"),
                        name=data["name"],
                        cost=data["cost"],
                        unit="ea",
                        is_active=True,
                        confidence_score=1.0,
                    )
                    session.add(product)
                count += 1

        print(f"  + Processed {count} supplier products")

        # -- Labor Templates ---------------------------------------------------
        print(f"\nSeeding/Updating labor templates...")
        for code, tmpl in LABOR_TEMPLATES.items():
            result = await session.execute(select(LaborTemplate).where(LaborTemplate.code == code))
            existing = result.scalar_one_or_none()
            
            data = {
                "name": tmpl.name,
                "category": tmpl.category,
                "base_hours": tmpl.base_hours,
                "lead_rate": tmpl.lead_rate,
                "helper_required": tmpl.helper_required,
                "helper_rate": tmpl.helper_rate,
                "helper_hours": tmpl.helper_hours,
                "disposal_hours": tmpl.disposal_hours,
                "is_active": True,
                "config_json": {
                    "access_multipliers": tmpl.access_multipliers,
                    "urgency_multipliers": tmpl.urgency_multipliers,
                    "applicable_assemblies": tmpl.applicable_assemblies,
                    "notes": tmpl.notes,
                },
            }
            
            if existing:
                for k, v in data.items():
                    setattr(existing, k, v)
            else:
                lt = LaborTemplate(code=code, **data)
                session.add(lt)
        print(f"  + Processed {len(LABOR_TEMPLATES)} templates")

        # -- Material Assemblies -----------------------------------------------
        print(f"\nSeeding/Updating material assemblies...")
        for code, asm in MATERIAL_ASSEMBLIES.items():
            result = await session.execute(select(MaterialAssembly).where(MaterialAssembly.code == code))
            existing = result.scalar_one_or_none()
            
            data = {
                "name": asm["name"],
                "labor_template_code": asm.get("labor_template"),
                "canonical_items": list(asm["items"].keys()),
                "item_quantities": asm["items"],
                "is_active": True,
            }
            
            if existing:
                for k, v in data.items():
                    setattr(existing, k, v)
            else:
                ma = MaterialAssembly(code=code, **data)
                session.add(ma)
        print(f"  + Processed {len(MATERIAL_ASSEMBLIES)} assemblies")

        # -- Markup Rules ------------------------------------------------------
        print("\nSeeding/Updating markup rules...")
        from app.services.pricing_engine import MARKUP_RULES
        for job_type, rules in MARKUP_RULES.items():
            result = await session.execute(select(MarkupRule).where(MarkupRule.job_type == job_type))
            existing = result.scalar_one_or_none()
            
            data = {
                "name": f"{job_type.capitalize()} Default",
                "markup_type": "percentage",
                "labor_markup_pct": rules.get("labor_markup_pct", 0.0),
                "materials_markup_pct": rules.get("materials_markup_pct", 0.30),
                "misc_flat": rules.get("misc_flat", 45.0),
                "is_active": True,
            }
            
            if existing:
                for k, v in data.items():
                    setattr(existing, k, v)
            else:
                mr = MarkupRule(job_type=job_type, **data)
                session.add(mr)
        print(f"  + Processed {len(MARKUP_RULES)} markup rules")

        await session.commit()
        print("\nDatabase update complete!")

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(seed())
