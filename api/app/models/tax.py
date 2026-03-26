from sqlalchemy import Column, Float, Integer, String
from app.database import Base


class TaxRate(Base):
    __tablename__ = "tax_rates"

    id = Column(Integer, primary_key=True)
    county = Column(String(100), nullable=False, unique=True)
    rate = Column(Float, nullable=False)
