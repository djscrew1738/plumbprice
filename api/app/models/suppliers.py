from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Text, JSON, Boolean, Index
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base


class Supplier(Base):
    __tablename__ = "suppliers"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False, unique=True)
    slug = Column(String(100), nullable=False, unique=True)
    type = Column(String(50), default="wholesale")
    website = Column(String(500), nullable=True)
    phone = Column(String(20), nullable=True)
    address = Column(Text, nullable=True)
    city = Column(String(100), nullable=True)
    notes = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    products = relationship("SupplierProduct", back_populates="supplier")


class SupplierProduct(Base):
    __tablename__ = "supplier_products"

    id = Column(Integer, primary_key=True, index=True)
    supplier_id = Column(Integer, ForeignKey("suppliers.id"), nullable=False, index=True)
    canonical_item = Column(String(200), nullable=False, index=True)
    sku = Column(String(100), nullable=True)
    name = Column(String(500), nullable=False)
    description = Column(Text, nullable=True)
    brand = Column(String(100), nullable=True)
    unit = Column(String(50), default="ea")

    cost = Column(Float, nullable=False)
    list_price = Column(Float, nullable=True)
    last_verified = Column(DateTime(timezone=True), nullable=True)
    confidence_score = Column(Float, default=1.0)

    is_active = Column(Boolean, default=True)
    is_preferred = Column(Boolean, default=False)
    notes = Column(Text, nullable=True)
    metadata_json = Column(JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    supplier = relationship("Supplier", back_populates="products")
    price_history = relationship("SupplierPriceHistory", back_populates="product")

    __table_args__ = (
        # Most common lookup: find cheapest active product for a canonical item
        Index("ix_supplier_products_canonical_active", "canonical_item", "is_active"),
        Index("ix_supplier_products_supplier_canonical", "supplier_id", "canonical_item"),
    )


class SupplierPriceHistory(Base):
    __tablename__ = "supplier_price_history"

    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey("supplier_products.id"), nullable=False, index=True)
    cost = Column(Float, nullable=False)
    recorded_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    source = Column(String(100), default="manual")

    product = relationship("SupplierProduct", back_populates="price_history")
