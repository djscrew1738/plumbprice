from sqlalchemy import Column, String, Float, Boolean
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base


class TaxRate(Base):
    __tablename__ = "tax_rates"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    county: Mapped[str] = mapped_column(String, unique=True, index=True, nullable=False)
    rate: Mapped[float] = mapped_column(Float, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
