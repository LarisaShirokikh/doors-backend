import io
import pandas as pd
from typing import Dict, List
from sqlalchemy.orm import Session
from app.core.database import SessionLocal
from app.tasks.worker import celery_app
from app.services import import_service
from app.cashe.redis_cashe import flush_pattern

@celery_app.task(name="import_products_from_excel_task")
def import_products_from_excel_task(file_content: bytes, filename: str) -> Dict:
    """
    Асинхронная задача для импорта товаров из Excel-файла
    
    Args:
        file_content: Содержимое файла в виде байтов
        filename: Имя файла
    
    Returns:
        Dict: Результат импорта
    """
    db = SessionLocal()
    try:
        file_io = io.BytesIO(file_content)
        result = import_service.import_products_from_excel(db, file_io, filename)
        
        # Очистка кэша товаров после импорта
        flush_pattern("products:*")
        
        return result
    finally:
        db.close()

@celery_app.task(name="update_product_prices_task")
def update_product_prices_task(product_ids: List[int], price_factor: float) -> Dict:
    """
    Асинхронная задача для обновления цен на товары
    
    Args:
        product_ids: Список ID товаров для обновления
        price_factor: Коэффициент изменения цены (например, 1.05 для увеличения на 5%)
    
    Returns:
        Dict: Результат обновления
    """
    db = SessionLocal()
    try:
        from app.models.product import Product
        
        # Счетчики для статистики
        updated = 0
        errors = 0
        error_details = []
        
        for product_id in product_ids:
            try:
                product = db.query(Product).filter(Product.id == product_id).first()
                if not product:
                    raise ValueError(f"Товар с ID {product_id} не найден")
                
                # Обновление цены
                product.price = round(product.price * price_factor, 2)
                db.commit()
                
                updated += 1
                
                # Очистка кэша для этого товара
                flush_pattern(f"products:{product_id}")
                
            except Exception as e:
                errors += 1
                error_details.append(f"Ошибка при обновлении товара {product_id}: {str(e)}")
                db.rollback()
        
        # Очистка общего кэша товаров
        flush_pattern("products:list:*")
        
        return {
            "status": "success" if errors == 0 else "partial",
            "stats": {
                "total": len(product_ids),
                "updated": updated,
                "errors": errors,
                "error_details": error_details
            }
        }
    finally:
        db.close()

@celery_app.task(name="recalculate_product_stats_task")
def recalculate_product_stats_task() -> Dict:
    """
    Асинхронная задача для пересчета статистики товаров
    
    Returns:
        Dict: Результат пересчета
    """
    db = SessionLocal()
    try:
        # Здесь может быть логика для пересчета статистики товаров
        # Например, обновление рейтингов, популярности и т.д.
        
        # Очистка кэша после обновления статистики
        flush_pattern("products:*")
        flush_pattern("categories:*")
        
        return {
            "status": "success",
            "message": "Статистика товаров успешно обновлена"
        }
    finally:
        db.close()