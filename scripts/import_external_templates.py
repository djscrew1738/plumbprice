#!/usr/bin/env python3
"""
Import external JSON pricing templates (web/templates/pricing) into the pricing_templates DB table.
This script mirrors the admin import endpoint but runs standalone.
"""
import asyncio
import sys
from sqlalchemy import select

from app.database import AsyncSessionLocal, init_db
from app.services.external_templates import list_pricing_templates, get_pricing_template
from app.models.pricing_template import PricingTemplate

async def main():
    try:
        await init_db()
    except Exception as e:
        print('init_db failed:', e, file=sys.stderr)

    processed = 0
    async with AsyncSessionLocal() as db:
        templates = list_pricing_templates()
        for t in templates:
            full = get_pricing_template(t.get('id'))
            if not full:
                continue
            result = await db.execute(select(PricingTemplate).where(PricingTemplate.template_id == full.get('id')))
            existing = result.scalar_one_or_none()
            if existing:
                existing.name = full.get('name')
                existing.description = full.get('description')
                existing.sku = full.get('sku')
                existing.base_price = full.get('base_price')
                existing.parts_cost = full.get('parts_cost')
                existing.labor_cost = full.get('labor_cost')
                existing.tax_rate = full.get('tax_rate')
                existing.region = full.get('region')
                existing.tags = full.get('tags')
                existing.source_file = full.get('_source_file')
            else:
                pt = PricingTemplate(
                    template_id=full.get('id'),
                    name=full.get('name') or full.get('id'),
                    description=full.get('description'),
                    sku=full.get('sku'),
                    base_price=full.get('base_price'),
                    parts_cost=full.get('parts_cost'),
                    labor_cost=full.get('labor_cost'),
                    tax_rate=full.get('tax_rate'),
                    region=full.get('region'),
                    tags=full.get('tags'),
                    source_file=full.get('_source_file'),
                )
                db.add(pt)
            processed += 1
        try:
            await db.commit()
        except Exception as e:
            print('commit failed:', e, file=sys.stderr)
    print('imported', processed)

if __name__ == '__main__':
    asyncio.run(main())
