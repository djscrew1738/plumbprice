from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import structlog

from app.database import get_db
from app.models.labor import LaborTemplate, MarkupRule
from app.services.labor_engine import LABOR_TEMPLATES, list_template_codes, get_template

logger = structlog.get_logger()
router = APIRouter()


@router.get("/labor-templates")
async def list_labor_templates(db: AsyncSession = Depends(get_db)):
    """List all labor templates (in-memory + DB overrides)."""
    templates = []
    for code, tmpl in LABOR_TEMPLATES.items():
        templates.append({
            "code": code,
            "name": tmpl.name,
            "category": tmpl.category,
            "base_hours": tmpl.base_hours,
            "lead_rate": tmpl.lead_rate,
            "helper_required": tmpl.helper_required,
            "helper_rate": tmpl.helper_rate,
            "disposal_hours": tmpl.disposal_hours,
            "notes": tmpl.notes,
            "applicable_assemblies": tmpl.applicable_assemblies,
            "access_multipliers": tmpl.access_multipliers,
            "urgency_multipliers": tmpl.urgency_multipliers,
        })
    return {"count": len(templates), "templates": templates}


@router.get("/labor-templates/{code}")
async def get_labor_template(code: str):
    """Get a specific labor template."""
    tmpl = get_template(code)
    if not tmpl:
        raise HTTPException(status_code=404, detail=f"Template '{code}' not found")
    return {
        "code": tmpl.code,
        "name": tmpl.name,
        "category": tmpl.category,
        "base_hours": tmpl.base_hours,
        "lead_rate": tmpl.lead_rate,
        "helper_required": tmpl.helper_required,
        "helper_rate": tmpl.helper_rate,
        "helper_hours": tmpl.helper_hours,
        "disposal_hours": tmpl.disposal_hours,
        "access_multipliers": tmpl.access_multipliers,
        "urgency_multipliers": tmpl.urgency_multipliers,
        "notes": tmpl.notes,
        "applicable_assemblies": tmpl.applicable_assemblies,
    }


@router.get("/markup-rules")
async def get_markup_rules(db: AsyncSession = Depends(get_db)):
    """Get markup rules."""
    from app.services.pricing_engine import MARKUP_RULES
    result = await db.execute(select(MarkupRule).where(MarkupRule.is_active == True))
    db_rules = result.scalars().all()

    if db_rules:
        return [
            {
                "id": r.id,
                "name": r.name,
                "job_type": r.job_type,
                "materials_markup_pct": r.materials_markup_pct,
                "labor_markup_pct": r.labor_markup_pct,
                "misc_flat": r.misc_flat,
            }
            for r in db_rules
        ]

    # Return in-memory defaults
    return [
        {"id": None, "name": f"{jt.capitalize()} Default", "job_type": jt, **rules}
        for jt, rules in MARKUP_RULES.items()
    ]


@router.put("/markup-rules/{job_type}")
async def update_markup_rules(
    job_type: str,
    materials_markup_pct: float,
    misc_flat: float = 45.0,
    db: AsyncSession = Depends(get_db),
):
    """Update markup rules for a job type."""
    if job_type not in ("service", "construction", "commercial"):
        raise HTTPException(status_code=400, detail="Invalid job type")

    result = await db.execute(
        select(MarkupRule).where(MarkupRule.job_type == job_type, MarkupRule.is_active == True)
    )
    rule = result.scalar_one_or_none()

    if rule:
        rule.materials_markup_pct = materials_markup_pct
        rule.misc_flat = misc_flat
    else:
        rule = MarkupRule(
            name=f"{job_type.capitalize()} Default",
            job_type=job_type,
            materials_markup_pct=materials_markup_pct,
            misc_flat=misc_flat,
        )
        db.add(rule)

    return {"job_type": job_type, "materials_markup_pct": materials_markup_pct, "misc_flat": misc_flat}


@router.get("/assemblies")
async def list_assemblies():
    """List all material assemblies."""
    from app.services.supplier_service import MATERIAL_ASSEMBLIES
    return {
        "count": len(MATERIAL_ASSEMBLIES),
        "assemblies": {
            code: {
                "name": asm["name"],
                "labor_template": asm.get("labor_template"),
                "items": asm["items"],
            }
            for code, asm in MATERIAL_ASSEMBLIES.items()
        },
    }


@router.get("/stats")
async def get_stats(db: AsyncSession = Depends(get_db)):
    """Get system stats."""
    from sqlalchemy import func
    from app.models.estimates import Estimate

    total_estimates = await db.execute(select(func.count(Estimate.id)))
    total_count = total_estimates.scalar()

    avg_total = await db.execute(select(func.avg(Estimate.grand_total)))
    avg_value = avg_total.scalar()

    return {
        "total_estimates": total_count or 0,
        "avg_estimate_value": round(avg_value or 0, 2),
        "labor_templates": len(LABOR_TEMPLATES),
        "canonical_items": len(__import__("app.services.supplier_service", fromlist=["CANONICAL_MAP"]).CANONICAL_MAP),
    }
