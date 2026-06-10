from sqlalchemy import String, Float, Boolean, Integer, Text, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func
from app.database import Base


class MaterialCategory(Base):
    """Hierarchical taxonomy for canonical items (fixtures, fittings, smart plumbing, etc.)."""

    __tablename__ = "material_categories"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    slug: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    parent_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("material_categories.id", ondelete="SET NULL"), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    sort_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), onupdate=func.now())

    parent = relationship("MaterialCategory", remote_side=[id], back_populates="children")
    children = relationship("MaterialCategory", back_populates="parent")


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
