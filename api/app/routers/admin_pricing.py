from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from app.database import get_db
from app.core.auth import get_current_admin
from app.models.pricing_rules import PermitCostRule, CityZoneMultiplier, TripChargeRule
from app.models.tax import TaxRate
from app.models.labor import MarkupRule
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
    result = await db.execute(select(TaxRate).order_by(TaxRate.county))
    return result.scalars().all()


@router.post("/tax-rates", response_model=tax_schemas.TaxRate)
async def create_tax_rate(body: tax_schemas.TaxRateCreate, db: AsyncSession = Depends(get_db), _=Depends(get_current_admin)):
    db_obj = TaxRate(**body.model_dump())
    db.add(db_obj)
    await db.commit()
    await db.refresh(db_obj)
    await pricing_config_service.refresh_cache()
    return db_obj


@router.delete("/tax-rates/{tax_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_tax_rate(tax_id: int, db: AsyncSession = Depends(get_db), _=Depends(get_current_admin)):
    await db.execute(delete(TaxRate).where(TaxRate.id == tax_id))
    await db.commit()
    await pricing_config_service.refresh_cache()
    return None


# --- Permit Costs ---
@router.get("/permit-costs", response_model=list[schemas.PermitCostRule])
async def list_permit_costs(db: AsyncSession = Depends(get_db), _=Depends(get_current_admin)):
    result = await db.execute(select(PermitCostRule).order_by(PermitCostRule.county, PermitCostRule.job_category))
    return result.scalars().all()


@router.post("/permit-costs", response_model=schemas.PermitCostRule)
async def create_permit_cost(body: schemas.PermitCostRuleCreate, db: AsyncSession = Depends(get_db), _=Depends(get_current_admin)):
    db_obj = PermitCostRule(**body.model_dump())
    db.add(db_obj)
    await db.commit()
    await db.refresh(db_obj)
    await pricing_config_service.refresh_cache()
    return db_obj


@router.delete("/permit-costs/{permit_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_permit_cost(permit_id: int, db: AsyncSession = Depends(get_db), _=Depends(get_current_admin)):
    await db.execute(delete(PermitCostRule).where(PermitCostRule.id == permit_id))
    await db.commit()
    await pricing_config_service.refresh_cache()
    return None


# --- City Multipliers ---
@router.get("/city-multipliers", response_model=list[schemas.CityZoneMultiplier])
async def list_city_multipliers(db: AsyncSession = Depends(get_db), _=Depends(get_current_admin)):
    result = await db.execute(select(CityZoneMultiplier).order_by(CityZoneMultiplier.city))
    return result.scalars().all()


@router.post("/city-multipliers", response_model=schemas.CityZoneMultiplier)
async def create_city_multiplier(body: schemas.CityZoneMultiplierCreate, db: AsyncSession = Depends(get_db), _=Depends(get_current_admin)):
    db_obj = CityZoneMultiplier(**body.model_dump())
    db.add(db_obj)
    await db.commit()
    await db.refresh(db_obj)
    await pricing_config_service.refresh_cache()
    return db_obj


@router.delete("/city-multipliers/{multiplier_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_city_multiplier(multiplier_id: int, db: AsyncSession = Depends(get_db), _=Depends(get_current_admin)):
    await db.execute(delete(CityZoneMultiplier).where(CityZoneMultiplier.id == multiplier_id))
    await db.commit()
    await pricing_config_service.refresh_cache()
    return None


# --- Trip Charges ---
@router.get("/trip-charges", response_model=list[schemas.TripChargeRule])
async def list_trip_charges(db: AsyncSession = Depends(get_db), _=Depends(get_current_admin)):
    result = await db.execute(select(TripChargeRule).order_by(TripChargeRule.county))
    return result.scalars().all()


@router.post("/trip-charges", response_model=schemas.TripChargeRule)
async def create_trip_charge(body: schemas.TripChargeRuleCreate, db: AsyncSession = Depends(get_db), _=Depends(get_current_admin)):
    db_obj = TripChargeRule(**body.model_dump())
    db.add(db_obj)
    await db.commit()
    await db.refresh(db_obj)
    await pricing_config_service.refresh_cache()
    return db_obj


@router.delete("/trip-charges/{charge_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_trip_charge(charge_id: int, db: AsyncSession = Depends(get_db), _=Depends(get_current_admin)):
    await db.execute(delete(TripChargeRule).where(TripChargeRule.id == charge_id))
    await db.commit()
    await pricing_config_service.refresh_cache()
    return None
