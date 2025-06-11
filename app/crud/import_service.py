import os
import pandas as pd
from typing import List, Dict, Optional, BinaryIO
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.import_log import ImportLog
from app.models.product import Product
from app.models.catalog import Catalog
from app.models.product_image import ProductImage
from app.schemas.import_log import ImportLogCreate
from app.crud.catalogs import catalog as catalog_crud

class ImportCRUD:
    async def create_import_log(self, db: AsyncSession, import_log: ImportLogCreate) -> ImportLog:
        """
        Создать запись лога импорта
        """
        db_import_log = ImportLog(**import_log.model_dump())
        db.add(db_import_log)
        await db.commit()
        await db.refresh(db_import_log)
        return db_import_log

    async def update_import_log(self, db: AsyncSession, import_log_id: int, status: str, message: Optional[str] = None) -> Optional[ImportLog]:
        """
        Обновить статус и сообщение лога импорта
        """
        stmt = select(ImportLog).where(ImportLog.id == import_log_id)
        result = await db.execute(stmt)
        db_import_log = result.scalar_one_or_none()
        
        if not db_import_log:
            return None
        
        db_import_log.status = status
        if message:
            db_import_log.message = message
        
        await db.commit()
        await db.refresh(db_import_log)
        return db_import_log

    async def import_products_from_excel(self, db: AsyncSession, file: BinaryIO, filename: str) -> Dict:
        """
        Импорт товаров из Excel-файла
        """
        try:
            # Чтение Excel-файла
            df = pd.read_excel(file)
            
            # Создание лога импорта
            import_log = await self.create_import_log(
                db, 
                ImportLogCreate(
                    filename=filename,
                    rows=len(df),
                    status="in_progress"
                )
            )
            
            # Счетчики для статистики
            stats = {
                "total": len(df),
                "created": 0,
                "updated": 0,
                "errors": 0,
                "error_details": []
            }
            
            # Обработка каждой строки данных
            for index, row in df.iterrows():
                try:
                    # Получение или создание каталога
                    catalog_name = row.get("catalog_name")
                    if not catalog_name:
                        raise ValueError("Отсутствует обязательное поле 'catalog_name'")
                    
                    # Используем catalog_crud вместо catalogs_service
                    catalog = await catalog_crud.get_catalog_by_name(db, catalog_name)
                    if not catalog:
                        raise ValueError(f"Каталог '{catalog_name}' не найден")
                    
                    # Проверка существующего товара по имени
                    product_name = row.get("name")
                    stmt = select(Product).where(
                        (Product.name == product_name) &
                        (Product.catalog_id == catalog.id)
                    )
                    result = await db.execute(stmt)
                    existing_product = result.scalar_one_or_none()
                    
                    # Подготовка данных товара
                    product_data = {
                        "name": product_name,
                        "description": row.get("description"),
                        "price": row.get("price", 0.0),
                        "in_stock": row.get("in_stock", True),
                        "catalog_id": catalog.id
                    }
                    
                    if existing_product:
                        # Обновление существующего товара
                        for key, value in product_data.items():
                            setattr(existing_product, key, value)
                        await db.commit()
                        stats["updated"] += 1
                    else:
                        # Создание нового товара
                        new_product = Product(**product_data)
                        db.add(new_product)
                        await db.commit()
                        await db.refresh(new_product)
                        
                        # Добавление изображений, если они есть
                        image_url = row.get("image_url")
                        if image_url and not pd.isna(image_url):
                            product_image = ProductImage(
                                product_id=new_product.id,
                                url=image_url,
                                is_main=True
                            )
                            db.add(product_image)
                            await db.commit()
                        
                        stats["created"] += 1
                
                except Exception as e:
                    stats["errors"] += 1
                    error_msg = f"Ошибка в строке {index+2}: {str(e)}"
                    stats["error_details"].append(error_msg)
            
            # Обновление статуса импорта
            status = "success" if stats["errors"] == 0 else "partial" if stats["created"] + stats["updated"] > 0 else "failed"
            error_message = "\n".join(stats["error_details"]) if stats["error_details"] else None
            
            await self.update_import_log(
                db, 
                import_log.id, 
                status=status,
                message=error_message
            )
            
            return {
                "import_log_id": import_log.id,
                "status": status,
                "stats": stats
            }
            
        except Exception as e:
            # В случае ошибки при обработке файла
            import_log = await self.create_import_log(
                db, 
                ImportLogCreate(
                    filename=filename,
                    rows=0,
                    status="failed",
                    message=str(e)
                )
            )
            
            return {
                "import_log_id": import_log.id,
                "status": "failed",
                "error": str(e)
            }

    async def get_import_logs(self, db: AsyncSession, skip: int = 0, limit: int = 100) -> List[ImportLog]:
        """
        Получить список логов импорта
        """
        stmt = select(ImportLog).order_by(ImportLog.created_at.desc()).offset(skip).limit(limit)
        result = await db.execute(stmt)
        return result.scalars().all()

    async def get_import_log(self, db: AsyncSession, import_log_id: int) -> Optional[ImportLog]:
        """
        Получить лог импорта по ID
        """
        stmt = select(ImportLog).where(ImportLog.id == import_log_id)
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

import_log = ImportCRUD()