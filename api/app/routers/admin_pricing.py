from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from app.database import get_db
from app.core.auth import get_current_admin
from app.core.cache import cache_get, cache_set, cache_invalidate
from app.models.pricing_rules import PermitCostRule, CityZoneMultiplier, TripChargeRule
from app.models.tax import TaxRate
from app.schemas import pricing_rules as schemas
from app.schemas import tax as tax_schemas
from app.services.pricing_config_service import pricing_config_service
import structlog

logger = structlog.get_logger()
router = APIRouter()


@router.post("/refresh", status_code=status.HTTP_200_OK)
async def refresh_pricing_cache(_=Depends(get_current_admin)):
    """Manually refresh the in-memory pricing cache from DB."""
    await pricing_config_service.refresh_cache()
    return {"status": "success", "message": "Pricing cache refreshed"}


# --- Tax Rates ---
@router.get("/tax-rates", response_model=list[tax_schemas.TaxRate])
async def list_tax_rates(db: AsyncSession = Depends(get_db), _=Depends(get_current_admin)):
    cached = await cache_get("admin:tax-rates")
    if cached is not None:
        return cached
    result = await db.execute(select(TaxRate).order_by(TaxRate.county))
    rows = result.scalars().all()
    data = [tax_schemas.TaxRate.model_validate(r).model_dump() for r in rows]
    await cache_set("admin:tax-rates", data, ttl=600)
    return rows


@router.post("/tax-rates", response_model=tax_schemas.TaxRate)
async def create_tax_rate(body: tax_schemas.TaxRateCreate, db: AsyncSession = Depends(get_db), _=Depends(get_current_admin)):
    db_obj = TaxRate(**body.model_dump())
    db.add(db_obj)
    await db.commit()
    await db.refresh(db_obj)
    await cache_invalidate("admin:tax-rates")
    await pricing_config_service.refresh_cache()
    return db_obj


@router.delete("/tax-rates/{tax_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_tax_rate(tax_id: int, db: AsyncSession = Depends(get_db), _=Depends(get_current_admin)):
    await db.execute(delete(TaxRate).where(TaxRate.id == tax_id))
    await db.commit()
    await cache_invalidate("admin:tax-rates")
    await pricing_config_service.refresh_cache()
    return None


# --- Permit Costs ---
@router.get("/permit-costs", response_model=list[schemas.PermitCostRule])
async def list_permit_costs(db: AsyncSession = Depends(get_db), _=Depends(get_current_admin)):
    cached = await cache_get("admin:permit-costs")
    if cached is not None:
        return cached
    result = await db.execute(select(PermitCostRule).order_by(PermitCostRule.county, PermitCostRule.job_category))
    rows = result.scalars().all()
    data = [schemas.PermitCostRule.model_validate(r).model_dump() for r in rows]
    await cache_set("admin:permit-costs", data, ttl=600)
    return rows


@router.post("/permit-costs", response_model=schemas.PermitCostRule)
async def create_permit_cost(body: schemas.PermitCostRuleCreate, db: AsyncSession = Depends(get_db), _=Depends(get_current_admin)):
    db_obj = PermitCostRule(**body.model_dump())
    db.add(db_obj)
    await db.commit()
    await db.refresh(db_obj)
    await cache_invalidate("admin:permit-costs")
    await pricing_config_service.refresh_cache()
    return db_obj


@router.delete("/permit-costs/{permit_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_permit_cost(permit_id: int, db: AsyncSession = Depends(get_db), _=Depends(get_current_admin)):
    await db.execute(delete(PermitCostRule).where(PermitCostRule.id == permit_id))
    await db.commit()
    await cache_invalidate("admin:permit-costs")
    await pricing_config_service.refresh_cache()
    return None


# --- City Multipliers ---
@router.get("/city-multipliers", response_model=list[schemas.CityZoneMultiplier])
async def list_city_multipliers(db: AsyncSession = Depends(get_db), _=Depends(get_current_admin)):
    cached = await cache_get("admin:city-multipliers")
    if cached is not None:
        return cached
    result = await db.execute(select(CityZoneMultiplier).order_by(CityZoneMultiplier.city))
    rows = result.scalars().all()
    data = [schemas.CityZoneMultiplier.model_validate(r).model_dump() for r in rows]
    await cache_set("admin:city-multipliers", data, ttl=600)
    return rows


@router.post("/city-multipliers", response_model=schemas.CityZoneMultiplier)
async def create_city_multiplier(body: schemas.CityZoneMultiplierCreate, db: AsyncSession = Depends(get_db), _=Depends(get_current_admin)):
    db_obj = CityZoneMultiplier(**body.model_dump())
    db.add(db_obj)
    await db.commit()
    await db.refresh(db_obj)
    await cache_invalidate("admin:city-multipliers")
    await pricing_config_service.refresh_cache()
    return db_obj


@router.delete("/city-multipliers/{multiplier_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_city_multiplier(multiplier_id: int, db: AsyncSession = Depends(get_db), _=Depends(get_current_admin)):
    await db.execute(delete(CityZoneMultiplier).where(CityZoneMultiplier.id == multiplier_id))
    await db.commit()
    await cache_invalidate("admin:city-multipliers")
    await pricing_config_service.refresh_cache()
    return None


# --- Trip Charges ---
@router.get("/trip-charges", response_model=list[schemas.TripChargeRule])
async def list_trip_charges(db: AsyncSession = Depends(get_db), _=Depends(get_current_admin)):
    cached = await cache_get("admin:trip-charges")
    if cached is not None:
        return cached
    result = await db.execute(select(TripChargeRule).order_by(TripChargeRule.county))
    rows = result.scalars().all()
    data = [schemas.TripChargeRule.model_validate(r).model_dump() for r in rows]
    await cache_set("admin:trip-charges", data, ttl=600)
    return rows


@router.post("/trip-charges", response_model=schemas.TripChargeRule)
async def create_trip_charge(body: schemas.TripChargeRuleCreate, db: AsyncSession = Depends(get_db), _=Depends(get_current_admin)):
    db_obj = TripChargeRule(**body.model_dump())
    db.add(db_obj)
    await db.commit()
    await db.refresh(db_obj)
    await cache_invalidate("admin:trip-charges")
    await pricing_config_service.refresh_cache()
    return db_obj


@router.delete("/trip-charges/{charge_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_trip_charge(charge_id: int, db: AsyncSession = Depends(get_db), _=Depends(get_current_admin)):
    await db.execute(delete(TripChargeRule).where(TripChargeRule.id == charge_id))
    await db.commit()
    await cache_invalidate("admin:trip-charges")
    await pricing_config_service.refresh_cache()
    return None
