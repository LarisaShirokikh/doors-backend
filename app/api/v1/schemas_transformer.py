from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import joinedload
from app.models import Product

async def transform_product_async(product_db, db: Optional[AsyncSession] = None) -> Dict[str, Any]:
    """
    Асинхронно преобразует объект продукта из базы данных в формат для фронтенда
    с правильной загрузкой связанных данных
    """
    # Обрабатываем изображения, если они есть
    images = []
    main_image = ""
    if hasattr(product_db, 'images') and product_db.images:
        images = [img.url for img in product_db.images]
        # Находим главное изображение
        main_images = [img for img in product_db.images if getattr(img, 'is_main', False)]
        main_image = main_images[0].url if main_images else (images[0] if images else "")
    
    # Получаем информацию о категории
    category_name = ""
    catalog_name = ""
    
    # Безопасное получение связанных данных без lazy loading
    if db and hasattr(product_db, 'catalog_id'):
        from app.models.catalog import Catalog
        from app.models.categories import Category
        
        # Получаем каталог с присоединенной категорией
        stmt = select(Catalog).options(
            joinedload(Catalog.category)
        ).where(Catalog.id == product_db.catalog_id)
        
        result = await db.execute(stmt)
        catalog = result.unique().scalar_one_or_none()
        
        if catalog:
            catalog_name = catalog.name
            if catalog.category:
                category_name = catalog.category.name
    
    # Вычисляем скидку, если есть старая цена
    discount = None
    old_price = None
    has_discount = False
    if hasattr(product_db, 'old_price') and product_db.old_price:
        old_price = product_db.old_price
        if product_db.old_price > product_db.price:
            discount = round(100 - (product_db.price / product_db.old_price * 100))
            has_discount = True
    
    # Определяем, новый ли товар
    is_new = False
    if hasattr(product_db, 'created_at') and product_db.created_at:
        is_new = (datetime.now() - product_db.created_at) < timedelta(days=30)
    
    return {
        "id": str(product_db.id),
        "name": product_db.name,
        "description": product_db.description if hasattr(product_db, 'description') else "",
        "price": float(product_db.price),
        "oldPrice": float(old_price) if old_price else None,
        "discount": discount,
        "image": main_image,
        "images": images,
        "videoUrl": getattr(product_db, 'video_url', None),
        "rating": getattr(product_db, 'rating', 5),
        "reviewCount": getattr(product_db, 'review_count', 0),
        "inStock": getattr(product_db, 'in_stock', True),
        "catalogName": catalog_name,
        "category": category_name,
        "tags": getattr(product_db, 'tags', []),
        "features": getattr(product_db, 'characteristics', {}),
        "recommended": getattr(product_db, 'is_recommended', False),
        "isNew": is_new,
        "hasDiscount": has_discount
    }

async def transform_products_async(products_db: List[Product], db: AsyncSession) -> List[Dict[str, Any]]:
    """
    Асинхронно преобразует список продуктов из базы данных в формат для фронтенда
    """
    return [await transform_product_async(p, db) for p in products_db]

# Для обратной совместимости оставляем синхронные функции с предупреждением
def transform_product(product_db):
    """
    Преобразует объект продукта из базы данных в формат для фронтенда
    ВНИМАНИЕ: Используйте transform_product_async для асинхронных операций!
    """
    import warnings
    warnings.warn(
        "Используется устаревшая синхронная функция transform_product. Используйте transform_product_async.",
        DeprecationWarning,
        stacklevel=2
    )
    
    # Только базовые поля без отношений
    return {
        "id": str(product_db.id),
        "name": product_db.name,
        "description": product_db.description if hasattr(product_db, 'description') else "",
        "price": float(product_db.price),
        "inStock": getattr(product_db, 'in_stock', True),
        "features": getattr(product_db, 'characteristics', {})
    }

def transform_products(products_db):
    """
    Преобразует список продуктов из базы данных в формат для фронтенда
    ВНИМАНИЕ: Используйте transform_products_async для асинхронных операций!
    """
    import warnings
    warnings.warn(
        "Используется устаревшая синхронная функция transform_products. Используйте transform_products_async.",
        DeprecationWarning,
        stacklevel=2
    )
    
    return [transform_product(p) for p in products_db]