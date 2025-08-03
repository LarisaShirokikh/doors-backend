
import logging
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query, Path
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc, and_
from sqlalchemy.orm import joinedload
from app.core.database import get_async_db
from app.models.product import Product
from app.crud.product import product as product_crud

router = APIRouter()

@router.get("/", response_model=Dict[str, Any])
async def get_products(
    category_slug: Optional[str] = None,
    brand_slug: Optional[str] = None,
    catalog_slug: Optional[str] = None,
    min_price: Optional[float] = None,
    max_price: Optional[float] = None,
    in_stock: Optional[bool] = None,
    is_new: Optional[bool] = None,
    type: Optional[str] = None,
    search: Optional[str] = None,
    sort: str = "smart",
    page: int = Query(1, ge=1),
    per_page: int = Query(12, ge=1, le=100),
    db: AsyncSession = Depends(get_async_db)
):
    """
    Получить список продуктов с фильтрацией, сортировкой и пагинацией
    """
    try:
        return await product_crud.get_filtered_products_paginated(
            db=db,
            category_slug=category_slug,
            brand_slug=brand_slug,
            catalog_slug=catalog_slug,
            min_price=min_price,
            max_price=max_price,
            in_stock=in_stock,
            is_new=is_new,
            type=type,
            search=search,
            sort=sort,
            page=page,
            per_page=per_page
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка при получении списка продуктов: {str(e)}")

@router.get("/{slug}", response_model=Dict[str, Any])
async def get_product_by_slug(
    slug: str = Path(..., description="Slug продукта"),
    db: AsyncSession = Depends(get_async_db)
):
    """
    Получить детальную информацию о продукте по slug
    """
    try:
    
        query = select(Product).options(
            joinedload(Product.product_images),
            joinedload(Product.categories),
            joinedload(Product.brand),
            joinedload(Product.catalog)
        ).where(
            and_(
                Product.slug == slug,
                Product.is_active == True
            )
        )
        
        # Выполняем запрос
        result = await db.execute(query)
        product = result.unique().scalar_one_or_none()
        
        if not product:
            logging.warning(f"Продукт с slug {slug} не найден")
            raise HTTPException(status_code=404, detail="Продукт не найден")
        
        logging.info(f"Продукт найден: {product.id} - {product.name}")
        
        # Создаем базовую структуру ответа
        response = {
            "id": product.id,
            "uuid": getattr(product, "uuid", None),
            "name": product.name,
            "slug": product.slug,
            "description": getattr(product, "description", None),
            "price": float(product.price) if product.price is not None else 0.0,
            "discount_price": float(product.discount_price) if product.discount_price is not None else None,
            "in_stock": getattr(product, "in_stock", False),
            "is_new": getattr(product, "is_new", False),
            "type": getattr(product, "type", None),
            "rating": getattr(product, "rating", 0.0),
            "review_count": getattr(product, "review_count", 0),
            "brand": None,
            "catalog": None,
            "categories": [],
            "images": [],
            "created_at": product.created_at.isoformat() if hasattr(product, "created_at") and product.created_at else None,
            "updated_at": product.updated_at.isoformat() if hasattr(product, "updated_at") and product.updated_at else None
        }
        
        # Бренд
        if hasattr(product, "brand") and product.brand:
            response["brand"] = {
                "id": product.brand.id,
                "name": product.brand.name,
                "slug": getattr(product.brand, "slug", None)
            }
        
        if hasattr(product, "catalog") and product.catalog:
            response["catalog"] = {
                "id": product.catalog.id,
                "name": product.catalog.name,
                "slug": getattr(product.catalog, "slug", None)
            }
        
        categories = []
        if hasattr(product, "categories") and product.categories:
            for category in product.categories:
                categories.append({
                    "id": category.id,
                    "name": category.name,
                    "slug": getattr(category, "slug", None)
                })
        response["categories"] = categories
        
        images = []
        if hasattr(product, "product_images") and product.product_images:
            for image in product.product_images:
                img_data = {"id": image.id, "url": image.url}
                if hasattr(image, "is_main"):
                    img_data["is_main"] = image.is_main
                if hasattr(image, "alt_text"):
                    img_data["alt_text"] = image.alt_text
                images.append(img_data)
        response["images"] = images
        
        return response
    
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        error_detail = str(e) + "\n" + traceback.format_exc()
        logging.error(f"Ошибка при получении продукта по slug {slug}: {error_detail}")
        
        raise HTTPException(status_code=500, detail=f"Ошибка при получении продукта: {str(e)}")

@router.get("/featured/", response_model=List[Dict[str, Any]])
async def get_featured_products(
    limit: int = Query(8, ge=1, le=20),
    db: AsyncSession = Depends(get_async_db)
):
    try:
        return await product_crud.get_featured_products(db=db, limit=limit)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка при получении рекомендуемых продуктов: {str(e)}")

@router.get("/new/", response_model=List[Dict[str, Any]])
async def get_new_products(
    limit: int = Query(8, ge=1, le=20),
    db: AsyncSession = Depends(get_async_db)
):
    """
    Получить новые продукты (упрощенная версия для отладки)
    """
    try:
        # Максимально упрощенный запрос
        query = select(Product).options(
            joinedload(Product.product_images),
            joinedload(Product.brand)
        ).where(
            Product.is_active == True
        )
        
        # Простая сортировка по ID (предполагая, что новые имеют большие ID)
        query = query.order_by(desc(Product.id))
        
        # Ограничиваем результаты
        query = query.limit(limit)
        
        # Выполняем запрос
        result = await db.execute(query)
        products = result.unique().scalars().all()
        
        # Простой список продуктов без сложных вычислений
        product_list = []
        for product in products:
            # Находим основное изображение
            main_image = None
            if hasattr(product, 'product_images') and product.product_images:
                for image in product.product_images:
                    if hasattr(image, 'is_main') and image.is_main:
                        main_image = image.url
                        break
                
                if not main_image and product.product_images:
                    main_image = product.product_images[0].url
            
            # Безопасно получаем значения полей
            product_dict = {
                "id": getattr(product, 'id', None),
                "name": getattr(product, 'name', None),
                "slug": getattr(product, 'slug', None),
                "image": main_image,
            }
            
            # Добавляем числовые поля с преобразованием
            if hasattr(product, 'price'):
                product_dict["price"] = float(product.price)
            else:
                product_dict["price"] = 0.0
                
            if hasattr(product, 'discount_price') and product.discount_price:
                product_dict["discount_price"] = float(product.discount_price)
            else:
                product_dict["discount_price"] = None
                
            # Добавляем бренд, если есть
            if hasattr(product, 'brand') and product.brand:
                product_dict["brand"] = product.brand.name
            else:
                product_dict["brand"] = None
                
            # Безопасно добавляем UUID если есть
            if hasattr(product, 'uuid'):
                product_dict["uuid"] = product.uuid
                
            product_list.append(product_dict)
        
        return product_list
    
    except Exception as e:
        # Добавляем подробное логирование ошибки для отладки
        import traceback
        error_detail = str(e) + "\n" + traceback.format_exc()
        raise HTTPException(status_code=500, detail=f"Ошибка при получении новых продуктов: {error_detail}")

@router.get("/discounted/", response_model=List[Dict[str, Any]])
async def get_discounted_products(
    limit: int = Query(8, ge=1, le=20),
    min_discount_percent: int = Query(5, ge=0, le=90),  # Минимальный % скидки
    db: AsyncSession = Depends(get_async_db)
):
    """
    Получить продукты со значительной скидкой, 
    отранжированные по оптимальному соотношению цены и качества
    """
    try:
        # Улучшенное получение товаров со скидкой
        # Помимо размера скидки учитываем рейтинг и популярность товара
        query = select(Product).options(
            joinedload(Product.product_images),
            joinedload(Product.brand)
        ).where(
            and_(
                Product.is_active == True,
                Product.discount_price.is_not(None),
                Product.discount_price < Product.price,
                # Убеждаемся, что скидка не менее указанного процента
                (((Product.price - Product.discount_price) / Product.price) * 100 >= min_discount_percent)
            )
        )
        
        # Вычисляем процент скидки для использования в формуле
        discount_percent = (((Product.price - Product.discount_price) / Product.price) * 100).label('discount_percent')
        deal_score = (
            # Размер скидки (0-100%)
            (discount_percent * 0.5) + 
            # Рейтинг товара (обычно 0-5)
            (Product.rating * 10 * 0.3) + 
            # Популярность
            (Product.popularity_score * 0.2)
        ).label('deal_score')
        
        # Добавляем discount_percent и deal_score в запрос
        query = query.add_columns(discount_percent, deal_score)
        
        # Сортируем по deal_score
        query = query.order_by(desc('deal_score'))
        
        # Ограничиваем количество результатов
        query = query.limit(limit)
        
        # Выполняем запрос
        result = await db.execute(query)
        
        # Извлекаем продукты и их рейтинги
        product_results = result.unique().all()
        
        # Формируем ответ
        product_list = []
        for product_tuple in product_results:
            # Элементы кортежа
            product = product_tuple[0]  # Product
            discount_percent_value = round(product_tuple[1])  # discount_percent
            
            # Находим основное изображение
            main_image = None
            if product.product_images:
                for image in product.product_images:
                    if image.is_main:
                        main_image = image.url
                        break
                
                if not main_image and product.product_images:
                    main_image = product.product_images[0].url
            
            # Вычисляем абсолютную экономию
            savings = float(product.price) - float(product.discount_price)
            
            product_list.append({
                "id": product.id,
                "uuid": product.uuid,
                "name": product.name,
                "slug": product.slug,
                "price": float(product.price),
                "discount_price": float(product.discount_price),
                "discount_percent": discount_percent_value,
                "savings": round(savings, 2),  # Показываем абсолютную экономию
                "image": main_image,
                "brand": product.brand.name if product.brand else None,
                "rating": product.rating  # Добавляем рейтинг
            })
        
        return product_list
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка при получении продуктов со скидкой: {str(e)}")
    
@router.get("/price-range/", response_model=Dict[str, float])
async def get_product_price_range(
    db: AsyncSession = Depends(get_async_db)
):
    """
    Получить минимальную и максимальную цены продуктов
    Используется для инициализации фильтров по цене
    """
    try:
        # Запрос минимальной и максимальной цены всех активных продуктов
        query = select(
            func.min(Product.price).label('min_price'),
            func.max(Product.price).label('max_price')
        ).where(Product.is_active == True)
        
        # Выполняем запрос
        result = await db.execute(query)
        row = result.first()
        
        # Получаем результаты и преобразуем в числа с плавающей точкой
        min_price = float(row.min_price) if row.min_price is not None else 0.0
        max_price = float(row.max_price) if row.max_price is not None else 100000.0
        
        # Если в базе нет товаров или все цены NULL, возвращаем значения по умолчанию
        if min_price == 0.0 and max_price == 0.0:
            min_price = 0.0
            max_price = 100000.0
            
        # Возвращаем минимальную и максимальную цены в виде JSON
        return {
            "min": min_price,
            "max": max_price
        }
    
    except Exception as e:
        # Логируем ошибку для отладки
        logging.error(f"Ошибка при получении диапазона цен продуктов: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Ошибка при получении диапазона цен: {str(e)}")