# app/models/__init__.py

"""
Импорт всех моделей для правильной работы SQLAlchemy и Alembic
"""

# Импорт моделей без внешних зависимостей

from .banner import Banner
from .promotion import Promotion
from .tip import Tip
from .import_log import ImportLog

# Добавляем новые базовые модели
from .brand import Brand
from .color import Color
from .material import Material

# Импорт моделей с внешними зависимостями
from .category import Category
from .catalog import Catalog
from .product import Product
from .product_image import ProductImage
from .product_video import ProductVideo
from .review import Review
from .catalog_image import CatalogImage
from .video import Video
from .product_ranking import ProductRanking

# Импорт связующих таблиц
from .attributes import product_category, product_color, product_material

__all__ = [
    "Category",
    "Catalog",
    "Product",
    "ProductImage",
    "CatalogImage",
    "ImportLog",
    "Banner",
    "Promotion",
    "Tip",
    "ProductVideo",
    "Brand",   # Добавлено
    "Color",   # Добавлено
    "Material", # Добавлено
    "Review",  # Добавлено
    "product_category",
    "product_color",
    "product_material",
    "Video",
    "ProductRanking"
]