# Вспомогательные таблицы для связей
from sqlalchemy import Column, Integer, ForeignKey, Boolean, DateTime, Table
from sqlalchemy.sql import func
from app.core.database import Base


product_categories = Table(
    "product_categories",
    Base.metadata,
    Column("product_id", Integer, ForeignKey("products.id", ondelete="CASCADE"), primary_key=True),
    Column("category_id", Integer, ForeignKey("categories.id", ondelete="CASCADE"), primary_key=True),
    Column("is_primary", Boolean, default=False),
    Column("created_at", DateTime(timezone=True), server_default=func.now())
)

