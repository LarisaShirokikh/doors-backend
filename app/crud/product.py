
import logging
from sqlalchemy import desc, select, inspect, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload
from app.api.v1.schemas_transformer import transform_product_async, transform_products_async
from app.models import Product, ProductImage
from app.models.catalog import Catalog
from app.models.categories import Category
from app.models.manufacturer import Manufacturer
from app.schemas.product import ProductCreate
from app.schemas.product_image import ProductImageCreate

class ProductCRUD:
    def __init__(self):
        self.logger = logging.getLogger("crud_product")

    async def get_all_products(self, db: AsyncSession):
        """
        Получить все продукты
        """
        stmt = select(Product).options(joinedload(Product.images))
        result = await db.execute(stmt)
        products = result.unique().scalars().all()
        
        return await transform_products_async(products, db)

    async def create_product(self, db: AsyncSession, product_data: ProductCreate, auto_commit: bool = False):
        """
        Создать новый продукт или обновить существующий
        """
        try:
            # Ищем или создаём каталог по имени
            result = await db.execute(select(Catalog).where(Catalog.name == product_data.catalog_name))
            catalog = result.scalar_one_or_none()

            if catalog is None:
                catalog = Catalog(name=product_data.catalog_name)
                db.add(catalog)
                await db.flush()  # получаем catalog.id

            # Проверяем, существует ли уже продукт с таким названием
            existing_product_query = select(Product).where(
                Product.name == product_data.name, 
                Product.catalog_id == catalog.id
            )
            result = await db.execute(existing_product_query)
            # Используем first() вместо scalar_one_or_none(), чтобы избежать ошибки
            # с несколькими результатами
            existing_product = result.scalars().first()

            if existing_product:
                self.logger.info(f"Найден существующий продукт с названием '{product_data.name}' (ID: {existing_product.id}), обновляем...")
                
                # Обновляем существующий продукт
                existing_product.description = product_data.description
                existing_product.price = product_data.price
                existing_product.in_stock = product_data.in_stock
                existing_product.characteristics = product_data.characteristics
                
                # Получаем текущие изображения
                current_images_query = select(ProductImage).where(ProductImage.product_id == existing_product.id)
                result = await db.execute(current_images_query)
                current_images = result.scalars().all()
                
                # Если у существующего продукта уже есть изображения, и мы не добавляем новые, пропускаем
                if current_images and not product_data.images:
                    self.logger.info(f"У продукта {existing_product.id} уже есть {len(current_images)} изображений, новые не добавляем")
                    
                    if auto_commit:
                        await db.commit()
                        await db.refresh(existing_product)
                    
                    return await transform_product_async(existing_product, db)
                
                # Если нужно добавить новые изображения
                if product_data.images:
                    # Добавляем новые изображения
                    self.logger.info(f"Добавление {len(product_data.images)} новых изображений для продукта {existing_product.id}")
                    
                    for i, image_data in enumerate(product_data.images):
                        if not hasattr(image_data, 'url') or not image_data.url:
                            continue
                            
                        # Проверяем, нет ли уже такого URL в базе
                        duplicate_check = select(ProductImage).where(
                            ProductImage.product_id == existing_product.id,
                            ProductImage.url == image_data.url
                        )
                        duplicate_result = await db.execute(duplicate_check)
                        if duplicate_result.first():
                            self.logger.info(f"Изображение {image_data.url} уже существует для продукта {existing_product.id}")
                            continue
                        
                        # Добавляем новое изображение
                        self.logger.info(f"Добавление изображения {i+1}/{len(product_data.images)}: {image_data.url} для продукта {existing_product.id}")
                        
                        # Определяем, будет ли изображение основным
                        # Если у продукта еще нет основного изображения и это первое новое, делаем его основным
                        is_main = False
                        if i == 0 and not any(getattr(img, 'is_main', False) for img in current_images):
                            is_main = True
                        
                        try:
                            # Проверяем структуру таблицы product_images
                            inspector = inspect(db.bind)
                            columns = {c['name'] for c in inspector.get_columns('product_images')}
                            
                            # Создаем словарь параметров, включая только существующие колонки
                            params = {'product_id': existing_product.id, 'url': image_data.url}
                            
                            if 'is_main' in columns:
                                params['is_main'] = is_main
                                
                            if 'alt_text' in columns:
                                params['alt_text'] = None  # Или другое значение по умолчанию
                            
                            new_image = ProductImage(**params)
                            db.add(new_image)
                            self.logger.info(f"Изображение {image_data.url} добавлено в БД")
                        except Exception as img_error:
                            self.logger.error(f"Ошибка при добавлении изображения: {img_error}", exc_info=True)
                
                if auto_commit:
                    await db.commit()
                    await db.refresh(existing_product)
                
                return await transform_product_async(existing_product, db)
            
            # Создаем новый продукт, если не найден существующий
            new_product = Product(
                name=product_data.name,
                description=product_data.description,
                price=product_data.price,
                in_stock=product_data.in_stock,
                catalog_id=catalog.id,
                characteristics=product_data.characteristics
            )

            db.add(new_product)
            await db.flush()  # Получаем ID нового продукта

            # Добавляем изображения для нового продукта
            self.logger.info(f"Добавление {len(product_data.images)} изображений для нового продукта {new_product.id}")
            
            for i, image_data in enumerate(product_data.images):
                if not hasattr(image_data, 'url') or not image_data.url:
                    self.logger.warning(f"Пустой URL изображения для продукта {new_product.id}, пропускаем")
                    continue

                self.logger.info(f"Добавление изображения {i+1}/{len(product_data.images)}: {image_data.url} для продукта {new_product.id}")
                
                try:
                    # Проверяем структуру таблицы product_images
                    inspector = inspect(db.bind)
                    columns = {c['name'] for c in inspector.get_columns('product_images')}
                    
                    # Создаем словарь параметров, включая только существующие колонки
                    params = {'product_id': new_product.id, 'url': image_data.url}
                    
                    if 'is_main' in columns:
                        params['is_main'] = (i == 0)  # Первое изображение основное
                        
                    if 'alt_text' in columns:
                        params['alt_text'] = None  # Или другое значение по умолчанию
                    
                    new_image = ProductImage(**params)
                    db.add(new_image)
                    self.logger.info(f"Изображение {image_data.url} добавлено в БД")
                except Exception as img_error:
                    self.logger.error(f"Ошибка при добавлении изображения: {img_error}", exc_info=True)

            if auto_commit:
                await db.commit()
                await db.refresh(new_product)
                self.logger.info(f"Продукт {new_product.id} сохранен в БД с auto_commit")
            else:
                self.logger.info(f"Продукт {new_product.id} подготовлен к сохранению (без auto_commit)")

            return await transform_product_async(new_product, db)
            
        except Exception as e:
            self.logger.error(f"Ошибка при создании продукта: {e}", exc_info=True)
            await db.rollback()
            # Re-raise exception after logging for proper error handling
            raise

    async def get_product_by_id(self, db: AsyncSession, product_id: int):
        """
        Получить продукт по ID с изображениями
        """
        query = select(Product).options(
            joinedload(Product.images),
            joinedload(Product.catalog).joinedload(Catalog.category)
        ).where(Product.id == product_id)
        
        result = await db.execute(query)
        product = result.unique().scalar_one_or_none()
        
        if not product:
            return None
        
        # Преобразуем продукт в нужный формат
        return await transform_product_async(product, db)

    async def get_all_products_filtered(
        self,
        db: AsyncSession,
        skip: int = 0,
        limit: int = 100,
        manufacturer_id: int = None,
        category_id: int = None,
        catalog_id: int = None,
        min_price: float = None,
        max_price: float = None,
        in_stock: bool = None,
        search: str = None,
        sort_by: str = None,
        sort_desc: bool = False,
    ):
        """
        Получить отфильтрованный список продуктов
        """
        query = select(Product).options(
            joinedload(Product.images),
            joinedload(Product.catalog).joinedload(Catalog.category)
        )

        # Применяем фильтры
        if catalog_id:
            query = query.where(Product.catalog_id == catalog_id)
        if category_id:
            query = query.join(Catalog).where(Catalog.category_id == category_id)
        if manufacturer_id:
            query = query.join(Catalog).join(Category).where(Category.manufacturer_id == manufacturer_id)
        if min_price is not None:
            query = query.where(Product.price >= min_price)
        if max_price is not None:
            query = query.where(Product.price <= max_price)
        if in_stock is not None:
            query = query.where(Product.in_stock == in_stock)
        if search:
            query = query.where(or_(
                Product.name.ilike(f"%{search}%"),
                Product.description.ilike(f"%{search}%")
            ))

        # Сортировка
        if sort_by:
            if sort_by == "price":
                query = query.order_by(desc(Product.price) if sort_desc else Product.price)
            elif sort_by == "name":
                query = query.order_by(desc(Product.name) if sort_desc else Product.name)
            elif sort_by == "created_at" and hasattr(Product, 'created_at'):
                query = query.order_by(desc(Product.created_at) if sort_desc else Product.created_at)
            elif sort_by == "id":
                query = query.order_by(desc(Product.id) if sort_desc else Product.id)

        # Пагинация
        query = query.offset(skip).limit(limit)

        result = await db.execute(query)
        products = result.unique().scalars().all()
        
        return await transform_products_async(products, db)

    async def get_recommended_products(self, db: AsyncSession, limit: int = 4):
        """
        Получить рекомендуемые продукты
        """
        query = select(Product).options(
            joinedload(Product.images),
            joinedload(Product.catalog).joinedload(Catalog.category)
        )
        
        # Если есть поле is_recommended, используем его
        if hasattr(Product, 'is_recommended'):
            query = query.where(Product.is_recommended == True)
            
        query = query.limit(limit)
        result = await db.execute(query)
        products = result.unique().scalars().all()
        
        # Преобразуем список продуктов в нужный формат
        return await transform_products_async(products, db)

    async def get_discount_products(self, db: AsyncSession, limit: int = 10):
        """
        Получить продукты со скидкой
        """
        query = select(Product).options(
            joinedload(Product.images),
            joinedload(Product.catalog).joinedload(Catalog.category)
        )
        
        # Если есть поле old_price, ищем товары со скидкой
        if hasattr(Product, 'old_price'):
            query = query.where(Product.old_price > Product.price)
            
        query = query.limit(limit)
        
        result = await db.execute(query)
        products = result.unique().scalars().all()
        
        # Преобразуем список продуктов в нужный формат
        return await transform_products_async(products, db)

    async def get_new_products(self, db: AsyncSession, limit: int = 8):
        """
        Получить новые продукты
        """
        query = select(Product).options(
            joinedload(Product.images),
            joinedload(Product.catalog).joinedload(Catalog.category)
        ).order_by(desc(Product.id))
        
        # Если есть поле created_at, сортируем по нему
        if hasattr(Product, 'created_at'):
            query = query.order_by(desc(Product.created_at))
        else:
            # Иначе сортируем по ID (примерно соответствует порядку добавления)
            query = query.order_by(desc(Product.id))
            
        query = query.limit(limit)
        
        result = await db.execute(query)
        products = result.unique().scalars().all()
        
        # Преобразуем список продуктов в нужный формат
        return await transform_products_async(products, db)

# Создаем экземпляр CRUD для использования в приложении
product = ProductCRUD()