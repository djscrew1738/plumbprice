from pydantic import BaseModel


class TaxRateBase(BaseModel):
    county: str
    rate: float
    is_active: bool = True


class TaxRateCreate(TaxRateBase):
    pass


class TaxRate(TaxRateBase):
    id: int

    class Config:
        orm_mode = True
