from sqlalchemy import Column, Integer, String, Float, DateTime, Text, JSON
from sqlalchemy.sql import func
from app.database import Base


class PricingTemplate(Base):
    __tablename__ = "pricing_templates"

    id = Column(Integer, primary_key=True, index=True)
    template_id = Column(String(100), nullable=False, unique=True)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    sku = Column(String(100), nullable=True)
    base_price = Column(Float, nullable=True)
    parts_cost = Column(Float, nullable=True)
    labor_cost = Column(Float, nullable=True)
    tax_rate = Column(Float, nullable=True)
    region = Column(String(100), nullable=True)
    tags = Column(JSON, nullable=True)
    source_file = Column(String(255), nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
