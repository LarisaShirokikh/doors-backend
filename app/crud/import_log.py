import io
import pandas as pd
from typing import List, Dict, Optional, BinaryIO
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime

from app.models.import_log import ImportLog
from app.models.product import Product
from app.models.catalog import Catalog
from app.models.product_image import ProductImage
from app.schemas.import_log import ImportLogCreate

class ImportLogCRUD:
    async def create_import_log(self, db: AsyncSession, import_log: ImportLogCreate) -> ImportLog:
        """
        Создать запись лога импорта
        """
        db_import_log = ImportLog(
            filename=import_log.filename,
            rows=import_log.rows,
            status=import_log.status,
            message=import_log.message,
            created_at=datetime.utcnow()
        )
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

    async def import_products_from_excel(self, db: AsyncSession, file_content: bytes, filename: str) -> Dict:
        """
        Импорт товаров из Excel-файла
        """
        try:
            # Чтение Excel-файла
            file_io = io.BytesIO(file_content)
            df = pd.read_excel(file_io)
            
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
                    # Проверяем наличие обязательных полей
                    if 'name' not in row or 'price' not in row or 'catalog_id' not in row:
                        raise ValueError(f"Строка {index+2}: Отсутствуют обязательные поля (name, price, catalog_id)")
                    
                    # Проверка существования каталога
                    catalog_id = int(row['catalog_id'])
                    stmt = select(Catalog).where(Catalog.id == catalog_id)
                    result = await db.execute(stmt)
                    catalog = result.scalar_one_or_none()
                    
                    if not catalog:
                        raise ValueError(f"Строка {index+2}: Каталог с ID {catalog_id} не найден")
                    
                    # Подготовка характеристик товара из дополнительных колонок
                    characteristics = {}
                    for col in df.columns:
                        if col.startswith('char_') and not pd.isna(row[col]):
                            char_name = col[5:]  # Убираем префикс "char_"
                            characteristics[char_name] = row[col]
                    
                    # Поиск существующего товара по имени (или другому идентификатору)
                    product_name = row['name']
                    stmt = select(Product).where(
                        (Product.name == product_name) & 
                        (Product.catalog_id == catalog_id)
                    )
                    result = await db.execute(stmt)
                    existing_product = result.scalar_one_or_none()
                    
                    if existing_product:
                        # Обновление существующего товара
                        existing_product.description = row.get('description', existing_product.description)
                        existing_product.price = float(row['price'])
                        existing_product.in_stock = bool(row.get('in_stock', True))
                        
                        # Обновляем характеристики, если они есть
                        if characteristics:
                            existing_product.characteristics = characteristics
                        
                        await db.commit()
                        stats["updated"] += 1
                    else:
                        # Создание нового товара
                        new_product = Product(
                            name=product_name,
                            description=row.get('description'),
                            price=float(row['price']),
                            in_stock=bool(row.get('in_stock', True)),
                            catalog_id=catalog_id,
                            characteristics=characteristics
                        )
                        db.add(new_product)
                        await db.commit()
                        await db.refresh(new_product)
                        
                        # Добавление изображений, если они есть
                        if 'image_url' in row and not pd.isna(row['image_url']):
                            product_image = ProductImage(
                                product_id=new_product.id,
                                url=row['image_url'],
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

import_log = ImportLogCRUD()