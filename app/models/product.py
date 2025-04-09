from sqlalchemy import Column, Integer, String, Float, Boolean, ForeignKey, JSON
from sqlalchemy.orm import relationship
from app.core.database import Base

class Product(Base):
    __tablename__ = "products"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    description = Column(String, nullable=True)
    price = Column(Float, nullable=False)
    in_stock = Column(Boolean, default=True)
    characteristics = Column(JSON, nullable=True)

    catalog_id = Column(Integer, ForeignKey("catalogs.id"), nullable=False)
    catalog = relationship("Catalog")
    images = relationship("ProductImage", back_populates="product", cascade="all, delete-orphan")