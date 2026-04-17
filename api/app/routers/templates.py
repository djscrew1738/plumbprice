from fastapi import APIRouter, Depends, HTTPException
from typing import List
from app.core.auth import get_current_user
from app.services.external_templates import list_pricing_templates, get_pricing_template, refresh_templates

router = APIRouter()


@router.get("/pricing", response_model=List[dict])
async def pricing_templates():
    """Return available pricing templates discovered from web/templates/pricing."""
    return list_pricing_templates()


@router.get("/pricing/{template_id}")
async def pricing_template(template_id: str):
    tpl = get_pricing_template(template_id)
    if not tpl:
        raise HTTPException(status_code=404, detail="Template not found")
    return tpl


@router.post("/pricing/refresh")
async def pricing_templates_refresh(current_user=Depends(get_current_user)):
    """Force a refresh/rescan of the templates directory. Requires authentication."""
    refresh_templates()
    return {"status": "ok"}
