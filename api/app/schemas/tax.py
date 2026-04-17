from pydantic import BaseModel, ConfigDict


class TaxRateBase(BaseModel):
    county: str
    rate: float
    is_active: bool = True


class TaxRateCreate(TaxRateBase):
    pass


class TaxRate(TaxRateBase):
    id: int
    model_config = ConfigDict(from_attributes=True)
