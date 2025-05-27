from typing import List, Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc
from sqlalchemy.orm import joinedload
from app.core.database import get_async_db
from app.models.brand import Brand
from app.models.catalog import Catalog
from app.models.product import Product
from app.models.category import Category
from app.models.attributes import product_category

router = APIRouter()

@router.get("/", response_model=List[Dict[str, Any]])
async def get_brands(
    is_active: bool = True,
    db: AsyncSession = Depends(get_async_db)
):
    """
    Получить список всех брендов
    """
    try:
        # Базовый запрос
        query = select(Brand)
        
        # Применяем фильтры
        if is_active:
            query = query.where(Brand.is_active == True)
        
        # Сортировка по имени
        query = query.order_by(Brand.name)
        
        # Выполняем запрос
        result = await db.execute(query)
        brands = result.scalars().all()
        
        # Формируем ответ
        brand_list = []
        for brand in brands:
            # Считаем количество товаров бренда
            count_query = select(func.count()).select_from(Product).where(
                (Product.brand_id == brand.id) & 
                (Product.is_active == True)
            )
            count_result = await db.execute(count_query)
            product_count = count_result.scalar() or 0
            
            brand_list.append({
                "id": brand.id,
                "name": brand.name,
                "slug": brand.slug,
                "logo_url": brand.logo_url,
                "website": brand.website,
                "product_count": product_count
            })
        
        return brand_list
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка при получении брендов: {str(e)}")

@router.get("/{slug}", response_model=Dict[str, Any])
async def get_brand_by_slug(
    slug: str,
    include_products: bool = False,
    include_categories: bool = True,
    product_limit: int = Query(4, ge=0, le=20),
    db: AsyncSession = Depends(get_async_db)
):
    """
    Получить бренд по slug с возможностью включения товаров и категорий
    """
    try:
        # Запрос на получение бренда
        query = select(Brand).where(
            (Brand.slug == slug) & (Brand.is_active == True)
        )
        
        result = await db.execute(query)
        brand = result.scalar_one_or_none()
        
        if not brand:
            raise HTTPException(status_code=404, detail="Бренд не найден")
        
        # Считаем количество товаров бренда
        count_query = select(func.count()).select_from(Product).where(
            (Product.brand_id == brand.id) & 
            (Product.is_active == True)
        )
        count_result = await db.execute(count_query)
        product_count = count_result.scalar() or 0
        
        # Начинаем формировать ответ
        response = {
            "id": brand.id,
            "name": brand.name,
            "slug": brand.slug,
            "description": brand.description,
            "logo_url": brand.logo_url,
            "website": brand.website,
            "product_count": product_count
        }
        
        # Если нужно включить категории бренда
        if include_categories:
            categories_query = select(Category).where(
                (Category.brand_id == brand.id) & 
                (Category.is_active == True)
            ).order_by(Category.name)
            
            categories_result = await db.execute(categories_query)
            categories = categories_result.scalars().all()
            
            categories_list = []
            for category in categories:
                # Считаем количество товаров в категории данного бренда
                cat_count_query = select(func.count()).select_from(Product).join(
                    product_category, 
                    Product.id == product_category.c.product_id
                ).where(
                    (product_category.c.category_id == category.id) & 
                    (Product.brand_id == brand.id) & 
                    (Product.is_active == True)
                )
                cat_count_result = await db.execute(cat_count_query)
                cat_product_count = cat_count_result.scalar() or 0
                
                categories_list.append({
                    "id": category.id,
                    "name": category.name,
                    "slug": category.slug,
                    "image_url": category.image_url,
                    "product_count": cat_product_count
                })
            
            response["categories"] = categories_list
        
        # Если нужно включить товары бренда
        if include_products:
            products_query = select(Product).options(
                joinedload(Product.product_images)
            ).where(
                (Product.brand_id == brand.id) & 
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
                    "image": main_image
                })
            
            response["products"] = products_list
        
        return response
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка при получении бренда: {str(e)}")

@router.get("/popular/", response_model=List[Dict[str, Any]])
async def get_popular_brands(
    limit: int = Query(6, ge=1, le=20),
    db: AsyncSession = Depends(get_async_db)
):
    """
    Получить популярные бренды (с наибольшим количеством товаров)
    """
    try:
        # Получаем бренды с подсчетом товаров
        query = select(
            Brand, 
            func.count(Product.id).label("product_count")
        ).join(
            Product,
            (Product.brand_id == Brand.id) & (Product.is_active == True),
            isouter=True
        ).where(
            Brand.is_active == True
        ).group_by(
            Brand.id
        ).order_by(
            desc("product_count")
        ).limit(limit)
        
        result = await db.execute(query)
        brands_with_count = result.all()
        
        # Формируем ответ
        brand_list = []
        for brand, count in brands_with_count:
            brand_list.append({
                "id": brand.id,
                "name": brand.name,
                "slug": brand.slug,
                "logo_url": brand.logo_url,
                "product_count": count
            })
        
        return brand_list
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка при получении популярных брендов: {str(e)}")
    
@router.get("/list/", response_model=List[Dict[str, Any]])
async def get_brands_list(
    is_active: bool = True,
    include_counts: bool = True,
    db: AsyncSession = Depends(get_async_db)
):
    return await get_brands(is_active, db)

@router.get("/{slug}/catalogs/", response_model=List[Dict[str, Any]])
async def get_brand_catalogs(
    slug: str,  # ✅ Изменено с brand_id на slug
    page: int = Query(1, ge=1),
    per_page: int = Query(12, ge=1, le=50),
    db: AsyncSession = Depends(get_async_db)
):
    """
    Get catalogs associated with a brand by slug
    """
    try:
        # Сначала находим бренд по slug
        brand_query = select(Brand).where(
            (Brand.slug == slug) & (Brand.is_active == True)
        )
        brand_result = await db.execute(brand_query)
        brand = brand_result.scalar_one_or_none()
        
        if not brand:
            raise HTTPException(status_code=404, detail="Бренд не найден")
        
        # Теперь получаем каталоги этого бренда
        query = select(Catalog).where(
            (Catalog.brand_id == brand.id) & 
            (Catalog.is_active == True)
        ).order_by(Catalog.name)
        
        result = await db.execute(query)
        catalogs = result.scalars().all()
        
        # Format response
        catalogs_list = []
        for catalog in catalogs:
            # Count products in this catalog for this brand
            count_query = select(func.count()).select_from(Product).where(
                (Product.catalog_id == catalog.id) &
                (Product.brand_id == brand.id) &
                (Product.is_active == True)
            )
            count_result = await db.execute(count_query)
            product_count = count_result.scalar() or 0
            
            catalogs_list.append({
                "id": catalog.id,
                "name": catalog.name,
                "slug": catalog.slug,
                "image": catalog.image,
                "product_count": product_count
            })
        
        return catalogs_list
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting brand catalogs: {str(e)}")


# ДОПОЛНИТЕЛЬНО: Можно добавить endpoint для получения бренда с каталогами в одном запросе
@router.get("/{slug}/with-catalogs/", response_model=Dict[str, Any])
async def get_brand_with_catalogs(
    slug: str,
    page: int = Query(1, ge=1),
    per_page: int = Query(12, ge=1, le=50),
    db: AsyncSession = Depends(get_async_db)
):
    """
    Get brand with its catalogs in one request
    """
    try:
        # Получаем бренд
        brand_query = select(Brand).where(
            (Brand.slug == slug) & (Brand.is_active == True)
        )
        brand_result = await db.execute(brand_query)
        brand = brand_result.scalar_one_or_none()
        
        if not brand:
            raise HTTPException(status_code=404, detail="Бренд не найден")
        
        # Считаем общее количество товаров бренда
        count_query = select(func.count()).select_from(Product).where(
            (Product.brand_id == brand.id) & 
            (Product.is_active == True)
        )
        count_result = await db.execute(count_query)
        product_count = count_result.scalar() or 0
        
        # Получаем каталоги
        catalogs_query = select(Catalog).where(
            (Catalog.brand_id == brand.id) & 
            (Catalog.is_active == True)
        ).order_by(Catalog.name)
        
        catalogs_result = await db.execute(catalogs_query)
        catalogs = catalogs_result.scalars().all()
        
        # Формируем каталоги с подсчетом товаров
        catalogs_list = []
        for catalog in catalogs:
            cat_count_query = select(func.count()).select_from(Product).where(
                (Product.catalog_id == catalog.id) &
                (Product.brand_id == brand.id) &
                (Product.is_active == True)
            )
            cat_count_result = await db.execute(cat_count_query)
            cat_product_count = cat_count_result.scalar() or 0
            
            catalogs_list.append({
                "id": catalog.id,
                "name": catalog.name,
                "slug": catalog.slug,
                "image": catalog.image,
                "product_count": cat_product_count
            })
        
        return {
            "brand": {
                "id": brand.id,
                "name": brand.name,
                "slug": brand.slug,
                "description": brand.description,
                "logo_url": brand.logo_url,
                "website": brand.website,
                "product_count": product_count
            },
            "catalogs": catalogs_list,
            "pagination": {
                "page": page,
                "per_page": per_page,
                "total": len(catalogs_list),
                "pages": 1  # Пока без пагинации каталогов
            }
        }
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting brand with catalogs: {str(e)}")