from sqlalchemy import String, Float, Boolean
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base


class PermitCostRule(Base):
    __tablename__ = "permit_cost_rules"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    county: Mapped[str] = mapped_column(String, index=True, nullable=False)
    job_category: Mapped[str] = mapped_column(String, index=True, nullable=False)  # e.g., water_heater, gas, etc.
    cost: Mapped[float] = mapped_column(Float, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)


class CityZoneMultiplier(Base):
    __tablename__ = "city_zone_multipliers"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    city: Mapped[str] = mapped_column(String, unique=True, index=True, nullable=False)
    multiplier: Mapped[float] = mapped_column(Float, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)


class TripChargeRule(Base):
    __tablename__ = "trip_charge_rules"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    county: Mapped[str] = mapped_column(String, unique=True, index=True, nullable=False)
    charge: Mapped[float] = mapped_column(Float, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
