from typing import List, Dict, Any, Optional, Union
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc
from sqlalchemy.orm import joinedload
from app.core.database import get_async_db
from app.models.product import Product
from app.models.brand import Brand
from app.models.attributes import product_categories
from app.models.category import Category
from app.crud.product import product as product_crud

router = APIRouter()

@router.get("/", response_model=List[Dict[str, Any]])
async def get_categories(
    is_active: bool = True,
    include_counts: bool = True,
    db: AsyncSession = Depends(get_async_db)
):
    """
    Получить список категорий с возможностью фильтрации
    """
    try:
        # Базовый запрос без предзагрузки бренда
        query = select(Category)
        
        # Применяем фильтры
        if is_active:
            query = query.where(Category.is_active == True)
        
        # Сортировка по имени
        query = query.order_by(Category.name)
        
        # Выполняем запрос
        result = await db.execute(query)
        categories = result.scalars().all()
        
        # Формируем ответ
        category_list = []
        for category in categories:
            category_data = {
                "id": category.id,
                "name": category.name,
                "slug": category.slug,
                "image_url": category.image_url,
                "description": category.description,
                "meta_title": category.meta_title,
                "meta_description": category.meta_description,
                "meta_keywords": category.meta_keywords
            }
            
            # Если нужно включить количество продуктов
            if include_counts:
                if hasattr(category, 'product_count') and category.product_count is not None:
                    # Используем существующее поле, если оно есть
                    category_data["product_count"] = category.product_count
                else:
                    # Иначе делаем запрос на подсчет
                    count_query = select(func.count()).select_from(product_categories).where(
                        product_categories.c.category_id == category.id
                    )
                    count_result = await db.execute(count_query)
                    category_data["product_count"] = count_result.scalar() or 0
            
            category_list.append(category_data)
        
        return category_list
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка при получении категорий: {str(e)}")

@router.get("/{category_identifier}/products/", response_model=Dict[str, Any])
async def get_products_by_category(
    category_identifier: str,  # ИСПРАВЛЕНО: Теперь принимает строку (может быть ID или slug)
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    sort_by: str = "created_at",
    sort_order: str = Query("desc", regex="^(asc|desc)$"),
    db: AsyncSession = Depends(get_async_db)
):
    """
    Получить продукты для категории по ID или slug с пагинацией и сортировкой
    """
    try:
        # Определяем, передан ID (число) или slug (строка)
        category_id = None
        
        if category_identifier.isdigit():
            # Если передан числовой ID
            category_id = int(category_identifier)
        else:
            # Если передан slug, находим ID категории
            category_query = select(Category.id).where(
                (Category.slug == category_identifier) & (Category.is_active == True)
            )
            category_result = await db.execute(category_query)
            category_id = category_result.scalar_one_or_none()
            
            if not category_id:
                raise HTTPException(status_code=404, detail=f"Категория с slug '{category_identifier}' не найдена")
        
        # Используем CRUD-метод для получения продуктов
        result = await product_crud.get_products_by_category(
            db=db,
            category_id=category_id,
            page=page,
            per_page=per_page,
            sort_by=sort_by,
            sort_order=sort_order
        )
        
        # Если категория не найдена
        if result is None:
            raise HTTPException(status_code=404, detail="Категория не найдена")
        
        return result
    
    except HTTPException:
        raise
    except Exception as e:
        # Логируем ошибку для отладки
        print(f"Ошибка при получении продуктов для категории {category_identifier}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Ошибка при получении продуктов: {str(e)}")

# ДОБАВЛЕН: Отдельный эндпоинт специально для slug (более явный)
@router.get("/slug/{slug}/products/", response_model=Dict[str, Any])
async def get_products_by_category_slug(
    slug: str,
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    sort_by: str = "created_at",
    sort_order: str = Query("desc", regex="^(asc|desc)$"),
    db: AsyncSession = Depends(get_async_db)
):
    """
    Получить продукты для категории по slug (явная версия)
    """
    try:
        # Находим ID категории по slug
        category_query = select(Category.id).where(
            (Category.slug == slug) & (Category.is_active == True)
        )
        category_result = await db.execute(category_query)
        category_id = category_result.scalar_one_or_none()
        
        if not category_id:
            raise HTTPException(status_code=404, detail=f"Категория с slug '{slug}' не найдена")
        
        # Используем CRUD-метод для получения продуктов
        result = await product_crud.get_products_by_category(
            db=db,
            category_id=category_id,
            page=page,
            per_page=per_page,
            sort_by=sort_by,
            sort_order=sort_order
        )
        
        if result is None:
            raise HTTPException(status_code=404, detail="Категория не найдена")
        
        return result
    
    except HTTPException:
        raise
    except Exception as e:
        print(f"Ошибка при получении продуктов для категории slug '{slug}': {str(e)}")
        raise HTTPException(status_code=500, detail=f"Ошибка при получении продуктов: {str(e)}")

@router.get("/{slug}", response_model=Dict[str, Any])
async def get_category_by_slug(
    slug: str,
    include_products: bool = False,
    product_limit: int = Query(4, ge=0, le=20),
    db: AsyncSession = Depends(get_async_db)
):
    """
    Получить категорию по slug с возможностью включения продуктов
    """
    try:
        # Запрос на получение категории
        query = select(Category).where(
            (Category.slug == slug) & (Category.is_active == True)
        )
        
        result = await db.execute(query)
        category = result.scalar_one_or_none()
        
        if not category:
            raise HTTPException(status_code=404, detail="Категория не найдена")
        
        # Начинаем формировать ответ
        response = {
            "id": category.id,
            "name": category.name,
            "slug": category.slug,
            "description": category.description,
            "image_url": category.image_url,
            "meta_title": category.meta_title,
            "meta_description": category.meta_description,
            "meta_keywords": category.meta_keywords
        }
        
        # Если нужно включить продукты
        if include_products:
            products_query = select(Product).options(
                joinedload(Product.product_images),
                joinedload(Product.brand)
            ).join(
                product_categories
            ).where(
                (product_categories.c.category_id == category.id) &
                (Product.is_active == True)
            ).order_by(
                desc(Product.popularity_score)
            ).limit(product_limit)
            
            products_result = await db.execute(products_query)
            products = products_result.unique().scalars().all()
            
            products_list = []
            for product in products:
                # Находим основное изображение
                main_image = None
                if product.product_images:
                    for image in product.product_images:
                        if image.is_main:
                            main_image = image.url
                            break
                    
                    if not main_image and product.product_images:
                        main_image = product.product_images[0].url
                
                products_list.append({
                    "id": product.id,
                    "name": product.name,
                    "slug": product.slug,
                    "price": float(product.price),
                    "discount_price": float(product.discount_price) if product.discount_price else None,
                    "image": main_image,
                    "brand": product.brand.name if product.brand else None
                })
            
            response["products"] = products_list
        
        # Добавляем количество товаров в категории
        count_query = select(func.count()).select_from(product_categories).where(
            product_categories.c.category_id == category.id
        )
        count_result = await db.execute(count_query)
        response["product_count"] = count_result.scalar() or 0
        
        return response
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка при получении категории: {str(e)}")

@router.get("/popular/", response_model=List[Dict[str, Any]])
async def get_popular_categories(
    limit: int = Query(6, ge=1, le=20),
    db: AsyncSession = Depends(get_async_db)
):
    """
    Получить популярные категории (с наибольшим количеством товаров)
    """
    try:
        # Получаем категории с подсчетом товаров
        query = select(
            Category, 
            func.count(product_categories.c.product_id).label("product_count")
        ).join(
            product_categories,
            Category.id == product_categories.c.category_id,
            isouter=True
        ).where(
            Category.is_active == True
        ).group_by(
            Category.id
        ).order_by(
            desc("product_count")
        ).limit(limit)
        
        result = await db.execute(query)
        categories_with_count = result.all()
        
        # Формируем ответ
        category_list = []
        for category, count in categories_with_count:
            category_list.append({
                "id": category.id,
                "name": category.name,
                "slug": category.slug,
                "image_url": category.image_url,
                "product_count": count
            })
        
        return category_list
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка при получении популярных категорий: {str(e)}")

@router.get("/list/", response_model=List[Dict[str, Any]])
async def get_categories_list(
    is_active: bool = True,
    include_counts: bool = True,
    db: AsyncSession = Depends(get_async_db)
):
    """
    Простой список категорий (алиас для основного метода)
    """
    return await get_categories(is_active, include_counts, db)