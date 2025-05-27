# Модель Category с полями из обоих приложений
from sqlalchemy import Column, Integer, String, ForeignKey, Boolean, DateTime, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base

class Category(Base):
    __tablename__ = "categories"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    slug = Column(String(255), nullable=False, unique=True, index=True)
    brand_id = Column(Integer, ForeignKey("brands.id"), nullable=False)  # Изменено с manufacturer_id на brand_id
    image_url = Column(String(255), nullable=True)
    description = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True)
    meta_title = Column(String(255), nullable=True)
    meta_description = Column(String(500), nullable=True)
    meta_keywords = Column(String(255), nullable=True)
    parent_id = Column(Integer, ForeignKey('categories.id', ondelete='SET NULL'), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    product_count = Column(Integer, default=0)
    
    # Связи
    brand = relationship("Brand", back_populates="categories")  # Изменено с manufacturer на brand
    products = relationship("Product", secondary="product_category", back_populates="categories")
    children = relationship("Category", backref="parent", remote_side=[id])

    def __repr__(self):
        return f"<Category {self.name}>"