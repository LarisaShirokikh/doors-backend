
import logging
from typing import Any, Dict, List, Optional
from sqlalchemy import desc, func, select, inspect, or_
from sqlalchemy.dialects.postgresql import INTERVAL, INTEGER
from sqlalchemy import Tuple as SqlTuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload
from app.api.v1.schemas_transformer import transform_product_async, transform_products_async
from app.models import Product, ProductImage
from app.models.catalog import Catalog
from app.models.category import Category
from app.schemas.product import ProductCreate
from app.schemas.product_image import ProductImageCreate
from app.models.attributes import product_categories

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
                catalog_id=catalog.id
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

    async def get_products_by_catalog(
        self,  # Add self parameter
        db: AsyncSession,
        catalog_id: int,
        offset: int,
        limit: int
    ) -> List[Product]:
        query = select(Product).options(
            joinedload(Product.product_images),
            joinedload(Product.brand)
        ).where(
            (Product.catalog_id == catalog_id) &
            (Product.is_active == True)
        ).order_by(
            desc(Product.popularity_score)
        ).offset(offset).limit(limit)
        
        result = await db.execute(query)
        return result.unique().scalars().all()

    async def get_products_by_category(
        self,
        db: AsyncSession,
        category_id: int,
        page: int = 1,
        per_page: int = 20,
        sort_by: str = "smart_rank",  # Новый вариант сортировки по умолчанию
        sort_order: str = "desc",
        price_range: Optional[tuple[float, float]] = None,
        in_stock_only: bool = False
    ):
        """
        Получить продукты для категории по ID с интеллектуальной сортировкой и фильтрацией
        """
        try:
            # Проверяем существование категории
            category_query = select(Category).where(Category.id == category_id)
            category_result = await db.execute(category_query)
            category = category_result.scalar_one_or_none()
            
            if not category:
                self.logger.warning(f"Категория с ID {category_id} не найдена")
                return None  # Категория не найдена
            
            # Базовый запрос продуктов из этой категории
            products_query = select(Product).options(
                joinedload(Product.product_images),
                joinedload(Product.brand)
            ).join(
                product_categories
            ).where(
                product_categories.c.category_id == category_id
            )
            
            # Применяем дополнительные фильтры
            if in_stock_only:
                products_query = products_query.where(Product.in_stock == True)
                
            if price_range:
                min_price, max_price = price_range
                if min_price is not None:
                    products_query = products_query.where(Product.price >= min_price)
                if max_price is not None:
                    products_query = products_query.where(Product.price <= max_price)
            
            in_stock_int = func.coalesce(
                func.nullif(Product.in_stock == True, False), 
                0
            ).cast(INTEGER)
            # Создаем интеллектуальный рейтинг для сортировки
            smart_rank = (
                # Популярность как основа (0-100)
                (Product.popularity_score * 0.5) +
                # Рейтинг товара (обычно 0-5)
                (Product.rating * 10 * 0.3) +
                # Количество отзывов (нормализуем до 0-10)
                (func.least(Product.review_count, 50) / 5 * 0.1) +
                # Бонус для товаров в наличии
                (in_stock_int * 10 * 0.1)
            ).label('smart_rank')
            
            # Применяем сортировку
            if sort_by == "smart_rank":
                products_query = products_query.add_columns(smart_rank)
                products_query = products_query.order_by(
                    desc('smart_rank') if sort_order.lower() == "desc" else 'smart_rank'
                )
            elif sort_by == "price":
                products_query = products_query.order_by(
                    desc(Product.price) if sort_order.lower() == "desc" else Product.price
                )
            elif sort_by == "name":
                products_query = products_query.order_by(
                    desc(Product.name) if sort_order.lower() == "desc" else Product.name
                )
            elif sort_by == "popularity":
                products_query = products_query.order_by(
                    desc(Product.popularity_score) if sort_order.lower() == "desc" else Product.popularity_score
                )
            elif sort_by == "rating":
                products_query = products_query.order_by(
                    desc(Product.rating) if sort_order.lower() == "desc" else Product.rating
                )
            elif sort_by == "created_at" and hasattr(Product, 'created_at'):
                products_query = products_query.order_by(
                    desc(Product.created_at) if sort_order.lower() == "desc" else Product.created_at
                )
            else:
                # Если указанный столбец не существует или не указан, используем smart_rank
                self.logger.warning(f"Столбец {sort_by} не распознан, используем smart_rank")
                products_query = products_query.add_columns(smart_rank)
                products_query = products_query.order_by(desc('smart_rank'))
                
            # Считаем общее количество товаров с учетом фильтров
            count_query = select(func.count()).select_from(products_query.subquery())
            count_result = await db.execute(count_query)
            total = count_result.scalar() or 0
            
            # Применяем пагинацию
            products_query = products_query.offset((page - 1) * per_page).limit(per_page)
            
            # Выполняем запрос
            result = await db.execute(products_query)
            
            # Определяем, использовалась ли умная сортировка с дополнительным полем
            has_smart_rank = sort_by == "smart_rank" or (sort_by not in ["price", "name", "created_at", "popularity", "rating"])
            
            # Обрабатываем результаты соответственно
            if has_smart_rank:
                product_results = result.unique().all()
            else:
                product_results = result.unique().scalars().all()
            
            # Формируем список продуктов
            products_list = []
            for product_item in product_results:
                if has_smart_rank:
                    # Если использовалась умная сортировка, первый элемент - это объект Product
                    product = product_item[0]
                else:
                    # Иначе уже получили объект Product напрямую
                    product = product_item
                
                # Находим основное изображение
                main_image = None
                if hasattr(product, 'product_images') and product.product_images:
                    for image in product.product_images:
                        if image.is_main:
                            main_image = image.url
                            break
                    
                    if not main_image and product.product_images:
                        main_image = product.product_images[0].url
                
                # Формируем основные данные товара
                product_dict = {
                    "id": product.id,
                    "name": product.name,
                    "slug": product.slug if hasattr(product, 'slug') else None,
                    "price": float(product.price) if hasattr(product, 'price') else 0.0,
                    "in_stock": product.in_stock,
                    "rating": product.rating,
                    "review_count": product.review_count
                }
                
                # Добавляем опциональные поля
                if hasattr(product, 'discount_price') and product.discount_price:
                    product_dict["discount_price"] = float(product.discount_price)
                    # Вычисляем процент скидки
                    discount_percent = round((1 - (product.discount_price / product.price)) * 100)
                    product_dict["discount_percent"] = discount_percent
                else:
                    product_dict["discount_price"] = None
                    
                product_dict["image"] = main_image
                
                if hasattr(product, 'brand') and product.brand:
                    product_dict["brand"] = product.brand.name
                else:
                    product_dict["brand"] = None
                
                products_list.append(product_dict)
            
            # Рассчитываем количество страниц
            pages = (total + per_page - 1) // per_page if total > 0 else 0
            
            self.logger.info(f"Получено {len(products_list)} продуктов для категории {category_id}, всего: {total}, страниц: {pages}")
            
            return {
                "items": products_list,
                "total": total,
                "pages": pages,
                "page": page,
                "sort": sort_by,
                "order": sort_order
            }
        except Exception as e:
            self.logger.error(f"Ошибка при получении продуктов для категории {category_id}: {str(e)}", exc_info=True)
            raise
    
    # Also fix the count_products_in_catalog method
    async def count_products_in_catalog(
        self,  # Add self parameter
        db: AsyncSession,
        catalog_id: int
    ) -> int:
        count_query = select(func.count()).select_from(Product).where(
            (Product.catalog_id == catalog_id) &
            (Product.is_active == True)
        )
        result = await db.execute(count_query)
        return result.scalar() or 0
    
# Создаем экземпляр CRUD для использования в приложении
product = ProductCRUD()