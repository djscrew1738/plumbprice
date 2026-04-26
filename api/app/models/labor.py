from sqlalchemy import Column, Integer, String, Float, DateTime, Text, JSON, Boolean
from sqlalchemy.sql import func
from app.database import Base


class LaborTemplate(Base):
    __tablename__ = "labor_templates"

    id = Column(Integer, primary_key=True, index=True)
    code = Column(String(100), nullable=False, unique=True)  # e.g. TOILET_REPLACE_STANDARD
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    category = Column(String(100), nullable=False)  # service, construction, commercial

    # Time
    base_hours = Column(Float, nullable=False)
    min_hours = Column(Float, nullable=True)
    max_hours = Column(Float, nullable=True)

    # Rates (DFW 2025-2026)
    lead_rate = Column(Float, default=185.0)   # Master plumber $/hr
    helper_required = Column(Boolean, default=False)
    helper_rate = Column(Float, default=50.0)
    helper_hours = Column(Float, nullable=True)

    # Disposal
    disposal_hours = Column(Float, default=0.0)

    # Access multipliers and other config stored as JSON
    config_json = Column(JSON, nullable=True)
    # Example:
    # {
    #   "access_multipliers": {"first_floor": 1.0, "second_floor": 1.25, "attic": 1.5, "crawlspace": 1.3},
    #   "urgency_multipliers": {"standard": 1.0, "same_day": 1.35, "emergency": 1.75},
    #   "applicable_assemblies": ["TOILET_INSTALL_KIT"],
    #   "notes": "Includes wax ring, bolts, supply line"
    # }

    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


class MaterialAssembly(Base):
    __tablename__ = "material_assemblies"

    id = Column(Integer, primary_key=True, index=True)
    code = Column(String(100), nullable=False, unique=True)  # e.g. TOILET_INSTALL_KIT
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    labor_template_code = Column(String(100), nullable=True)

    # List of canonical items in this assembly
    canonical_items = Column(JSON, nullable=False)  # ["toilet.elongated.standard", "wax_ring.standard", ...]
    item_quantities = Column(JSON, nullable=True)  # {"toilet.elongated.standard": 1, "wax_ring.standard": 1}

    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


class MarkupRule(Base):
    __tablename__ = "markup_rules"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    job_type = Column(String(50), nullable=False)  # service, construction, commercial
    markup_type = Column(String(50), default="percentage")  # percentage, flat
    labor_markup_pct = Column(Float, default=0.0)
    materials_markup_pct = Column(Float, default=0.30)  # 30% default materials markup
    misc_flat = Column(Float, default=45.0)  # misc/disposal flat fee
    is_active = Column(Boolean, default=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
