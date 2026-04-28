from pydantic import BaseModel, ConfigDict
from typing import Optional


class PermitCostRuleBase(BaseModel):
    county: str
    job_category: str
    cost: float
    is_active: bool = True


class PermitCostRuleCreate(PermitCostRuleBase):
    pass


class PermitCostRule(PermitCostRuleBase):
    id: int
    model_config = ConfigDict(from_attributes=True)


class CityZoneMultiplierBase(BaseModel):
    city: str
    multiplier: float
    is_active: bool = True


class CityZoneMultiplierCreate(CityZoneMultiplierBase):
    pass


class CityZoneMultiplier(CityZoneMultiplierBase):
    id: int
    model_config = ConfigDict(from_attributes=True)


class TripChargeRuleBase(BaseModel):
    county: str
    charge: float
    is_active: bool = True


class TripChargeRuleCreate(TripChargeRuleBase):
    pass


class TripChargeRule(TripChargeRuleBase):
    id: int
    model_config = ConfigDict(from_attributes=True)
