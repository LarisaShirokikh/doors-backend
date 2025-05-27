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
from app.crud.catalogs import catalog
from app.crud.product import product as product_crud
import logging


router = APIRouter()

@router.get("/", response_model=Dict[str, Any])
async def get_catalogs(
    page: int = Query(1, ge=1),
    per_page: int = Query(12, ge=1, le=100),
    sort: str = Query("name", regex="^(name|newest|popular|product_count)$"),
    category_id: Optional[int] = None,
    brand_id: Optional[int] = None,
    search: Optional[str] = None,
    is_active: bool = True,
    db: AsyncSession = Depends(get_async_db)
):
    """
    Получить список каталогов с пагинацией и сортировкой
    """
    return await get_catalogs_paginated(
        page=page, 
        per_page=per_page, 
        sort=sort, 
        category_id=category_id,
        brand_id=brand_id,
        search=search,
        is_active=is_active,
        db=db
    )

@router.get("/paginated/", response_model=Dict[str, Any])
@router.get("/paginated", response_model=Dict[str, Any])
async def get_catalogs_paginated(
    page: int = Query(1, ge=1),
    per_page: int = Query(12, ge=1, le=100),
    sort: str = Query("name", regex="^(name|name_asc|name_desc|newest|popular|product_count)$"),
    category_id: Optional[int] = None,
    brand_id: Optional[int] = None,
    search: Optional[str] = None,
    is_active: bool = True,
    db: AsyncSession = Depends(get_async_db)
):
    """
    Получить список каталогов с пагинацией и сортировкой
    """
    try:
        
        # Получаем все ID каталогов сначала
        catalog_ids_query = select(Catalog.id)
        
        # Применяем фильтры
        if is_active:
            catalog_ids_query = catalog_ids_query.where(Catalog.is_active == True)
        
        if category_id is not None:
            catalog_ids_query = catalog_ids_query.where(Catalog.category_id == category_id)
            
        if brand_id is not None:
            catalog_ids_query = catalog_ids_query.where(Catalog.brand_id == brand_id)
            
        if search:
            search_term = f"%{search}%"
            catalog_ids_query = catalog_ids_query.where(Catalog.name.ilike(search_term))
        
        # Сортировка и подсчет
        if sort == "newest":
            catalog_ids_query = catalog_ids_query.order_by(desc(Catalog.created_at))
        elif sort == "popular" or sort == "product_count":
            # Сортировка по количеству продуктов
            catalog_ids_query = catalog_ids_query.outerjoin(Product, Catalog.id == Product.catalog_id).\
                group_by(Catalog.id).\
                order_by(desc(func.count(Product.id)))
        elif sort == "name_desc":
            # Сортировка по имени в обратном порядке (Я-А)
            catalog_ids_query = catalog_ids_query.order_by(desc(Catalog.name))
        else:
            # По умолчанию сортируем по имени
            catalog_ids_query = catalog_ids_query.order_by(Catalog.name)
        
        # Подсчет общего количества
        if sort != "popular" and sort != "product_count":
            count_query = select(func.count()).select_from(catalog_ids_query.subquery())
            count_result = await db.execute(count_query)
            total = count_result.scalar() or 0
        else:
            # Для сортировки по популярности считаем иначе
            count_result = await db.execute(
                select(func.count()).select_from(
                    select(Catalog.id).where(catalog_ids_query.whereclause).subquery()
                )
            )
            total = count_result.scalar() or 0
        
        # Применяем пагинацию к запросу ID
        if sort != "popular" and sort != "product_count":
            catalog_ids_query = catalog_ids_query.offset((page - 1) * per_page).limit(per_page)
            catalog_ids_result = await db.execute(catalog_ids_query)
            catalog_ids = [row[0] for row in catalog_ids_result.all()]
        else:
            # Для сортировки по популярности
            catalog_ids_query = catalog_ids_query.offset((page - 1) * per_page).limit(per_page)
            catalog_ids_result = await db.execute(catalog_ids_query)
            catalog_ids = [row[0] for row in catalog_ids_result.all()]
        
        # Формируем ответ пустым, если нет ID
        if not catalog_ids:
            return {
                "items": [],
                "total": total,
                "page": page,
                "per_page": per_page,
                "pages": (total + per_page - 1) // per_page
            }
        
        # Получаем полную информацию о каталогах по ID
        catalogs_query = select(Catalog).where(Catalog.id.in_(catalog_ids))
        catalogs_result = await db.execute(catalogs_query)
        catalogs = catalogs_result.scalars().all()
        
        # Получаем ID категорий и брендов для всех каталогов
        category_ids = [c.category_id for c in catalogs if c.category_id is not None]
        brand_ids = [c.brand_id for c in catalogs if c.brand_id is not None]
        
        # Загружаем категории и бренды одним запросом, если есть ID
        categories = {}
        if category_ids:
            categories_query = select(Category).where(Category.id.in_(category_ids))
            categories_result = await db.execute(categories_query)
            categories = {c.id: c for c in categories_result.scalars().all()}
        
        brands = {}
        if brand_ids:
            brands_query = select(Brand).where(Brand.id.in_(brand_ids))
            brands_result = await db.execute(brands_query)
            brands = {b.id: b for b in brands_result.scalars().all()}
        
        # Получаем количество продуктов для каждого каталога
        product_counts_query = select(
            Product.catalog_id,
            func.count(Product.id).label("count")
        ).where(
            (Product.catalog_id.in_(catalog_ids)) & 
            (Product.is_active == True)
        ).group_by(
            Product.catalog_id
        )
        product_counts_result = await db.execute(product_counts_query)
        product_counts = {row[0]: row[1] for row in product_counts_result.all()}
        
        # Формируем список результатов в правильном порядке
        catalog_dict = {c.id: c for c in catalogs}
        catalog_list = []
        
        for catalog_id in catalog_ids:
            if catalog_id not in catalog_dict:
                continue
                
            catalog = catalog_dict[catalog_id]
            
            # Получаем данные категории
            category_data = None
            if catalog.category_id and catalog.category_id in categories:
                category = categories[catalog.category_id]
                category_data = {
                    "id": category.id,
                    "name": category.name,
                    "slug": category.slug
                }
            
            # Получаем данные бренда
            brand_data = None
            if catalog.brand_id and catalog.brand_id in brands:
                brand = brands[catalog.brand_id]
                brand_data = {
                    "id": brand.id,
                    "name": brand.name,
                    "slug": brand.slug
                }
            
            # Получаем количество продуктов
            product_count = product_counts.get(catalog.id, 0)
            
            catalog_list.append({
                "id": catalog.id,
                "name": catalog.name,
                "slug": catalog.slug,
                "description": catalog.description,
                "image": catalog.image,
                "brand": brand_data,
                "category": category_data,
                "product_count": product_count
            })
        
        # Рассчитываем количество страниц
        pages = (total + per_page - 1) // per_page  # Округление вверх
        
        return {
            "items": catalog_list,
            "total": total,
            "page": page,
            "per_page": per_page,
            "pages": pages
        }
    
    except Exception as e:
        # Подробное логирование для отладки
        import traceback
        logging.error(f"Error in get_catalogs_paginated: {str(e)}")
        logging.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Ошибка при получении каталогов: {str(e)}")

@router.get("/{slug}/products/", response_model=Dict[str, Any])
async def get_products_by_catalog_slug(
    slug: str,
    page: int = Query(1, ge=1),
    per_page: int = Query(8, ge=1, le=100),
    db: AsyncSession = Depends(get_async_db)
):
    """
    Получить продукты каталога по его slug
    """
    try:
        # Сначала найдем каталог по slug
        catalog_query = select(Catalog).where(
            (Catalog.slug == slug) & (Catalog.is_active == True)
        )
        
        catalog_result = await db.execute(catalog_query)
        catalog = catalog_result.scalar_one_or_none()
        
        if not catalog:
            raise HTTPException(status_code=404, detail=f"Каталог со slug '{slug}' не найден")
        
        # Теперь получим продукты каталога
        offset = (page - 1) * per_page

        # Получаем товары и общее количество
        try:
            # Добавляем детальное логирование
            logging.info(f"Fetching products for catalog with slug '{slug}' (ID: {catalog.id}), page {page}, per_page {per_page}")
            products = await product_crud.get_products_by_catalog(db=db, catalog_id=catalog.id, offset=offset, limit=per_page)
            total_products = await product_crud.count_products_in_catalog(db=db, catalog_id=catalog.id)
            logging.info(f"Found {len(products)} products out of {total_products} total")
        except Exception as e:
            # Более детальное логирование ошибок
            logging.error(f"Error in product_crud methods: {str(e)}", exc_info=True)
            raise HTTPException(status_code=500, detail=f"Ошибка при получении товаров: {str(e)}")

        products_list = []
        for product in products:
            main_image = None
            
            # Проверяем, какое поле используется для изображений
            images_field = getattr(product, 'product_images', None) or getattr(product, 'images', [])
            
            if images_field:
                for image in images_field:
                    if getattr(image, 'is_main', False):
                        main_image = image.url
                        break
                if not main_image and images_field:
                    main_image = images_field[0].url

            products_list.append({
                "id": product.id,
                "name": product.name,
                "slug": product.slug,
                "price": float(product.price),
                "discount_price": float(product.discount_price) if product.discount_price else None,
                "image": main_image,
                "brand": product.brand.name if hasattr(product, 'brand') and product.brand else None
            })

        return {
            "products": products_list,
            "pagination": {
                "page": page,
                "per_page": per_page,
                "total": total_products
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        # Добавляем полный стек ошибки в лог
        logging.error(f"Unexpected error in get_products_by_catalog_slug for slug '{slug}': {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Ошибка при получении товаров каталога: {str(e)}")
    


@router.get("/by-category/{category_slug}", response_model=List[Dict[str, Any]])
async def get_catalogs_by_category_slug(
    category_slug: str,
    db: AsyncSession = Depends(get_async_db)
):
    """
    Получить список каталогов по slug категории
    """
    try:
        # Сначала находим категорию по slug
        category_query = select(Category).where(
            (Category.slug == category_slug) & 
            (Category.is_active == True)
        )
        
        category_result = await db.execute(category_query)
        category = category_result.scalar_one_or_none()
        
        if not category:
            raise HTTPException(status_code=404, detail="Категория не найдена")
        
        # Теперь получаем каталоги для этой категории
        query = select(Catalog).options(
            joinedload(Catalog.category)
        ).where(
            (Catalog.category_id == category.id) & 
            (Catalog.is_active == True)
        ).order_by(Catalog.name)
        
        result = await db.execute(query)
        catalogs = result.unique().scalars().all()
        
        # Формируем ответ
        catalog_list = []
        for catalog in catalogs:
            # Считаем количество товаров в каталоге
            count_query = select(func.count()).select_from(Product).where(
                (Product.catalog_id == catalog.id) & 
                (Product.is_active == True)
            )
            count_result = await db.execute(count_query)
            product_count = count_result.scalar() or 0
            
            catalog_list.append({
                "id": catalog.id,
                "name": catalog.name,
                "slug": catalog.slug,
                "description": catalog.description,
                "product_count": product_count
            })
        
        return catalog_list
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка при получении каталогов по категории: {str(e)}")

@router.get("/popular/", response_model=List[Dict[str, Any]])
async def get_popular_catalogs(
    limit: int = Query(6, ge=1, le=20),
    db: AsyncSession = Depends(get_async_db)
):
    """
    Получить популярные каталоги (с наибольшим количеством товаров)
    """
    try:
        # Получаем каталоги с подсчетом товаров
        query = select(
            Catalog, 
            func.count(Product.id).label("product_count")
        ).join(
            Product,
            (Product.catalog_id == Catalog.id) & (Product.is_active == True),
            isouter=True
        ).where(
            Catalog.is_active == True
        ).group_by(
            Catalog.id
        ).order_by(
            desc("product_count")
        ).limit(limit)
        
        result = await db.execute(query)
        catalogs_with_count = result.all()
        
        # Формируем ответ
        catalog_list = []
        for catalog, count in catalogs_with_count:
            catalog_list.append({
                "id": catalog.id,
                "name": catalog.name,
                "slug": catalog.slug,
                "image": catalog.image,
                "description": catalog.description,
                "product_count": count
            })
        
        return catalog_list
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка при получении популярных каталогов: {str(e)}")
    
@router.get("/list/", response_model=List[Dict[str, Any]])
async def get_catalogs_list(
    is_active: bool = True,
    db: AsyncSession = Depends(get_async_db)
):
    try:
        # Прямой запрос вместо catalog.get_catalogs
        query = select(Catalog)
        if is_active:
            query = query.where(Catalog.is_active == True)
        query = query.order_by(Catalog.name)
        
        result = await db.execute(query)
        catalogs = result.scalars().all()
        
        return [
            {
                "id": c.id,
                "name": c.name,
                "slug": c.slug,
                "description": c.description,
                "image": c.image,
                "brand_id": c.brand_id
            }
            for c in catalogs
        ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка при получении списка каталогов: {str(e)}")


@router.get("/{catalog_id}/products/", response_model=Dict[str, Any])
async def get_products_by_catalog_endpoint(
    catalog_id: int,
    page: int = Query(1, ge=1),
    per_page: int = Query(8, ge=1, le=100),
    db: AsyncSession = Depends(get_async_db)
):
    try:
        # Проверка, что каталог существует
        catalog_query = select(Catalog).where(Catalog.id == catalog_id, Catalog.is_active == True)
        catalog_result = await db.execute(catalog_query)
        catalog = catalog_result.scalar_one_or_none()
        
        if not catalog:
            raise HTTPException(status_code=404, detail="Каталог не найден")
        
        offset = (page - 1) * per_page

        # Получаем товары и общее количество
        try:
            # Add more detailed logging
            logging.info(f"Fetching products for catalog ID {catalog_id}, page {page}, per_page {per_page}")
            products = await product_crud.get_products_by_catalog(db=db, catalog_id=catalog_id, offset=offset, limit=per_page)
            total_products = await product_crud.count_products_in_catalog(db=db, catalog_id=catalog_id)
            logging.info(f"Found {len(products)} products out of {total_products} total")
        except Exception as e:
            # More detailed error logging
            logging.error(f"Error in product_crud methods: {str(e)}", exc_info=True)
            raise HTTPException(status_code=500, detail=f"Ошибка при получении товаров: {str(e)}")

        products_list = []
        for product in products:
            main_image = None
            
            # Check if we're using product_images or images
            images_field = getattr(product, 'product_images', None) or getattr(product, 'images', [])
            
            if images_field:
                for image in images_field:
                    if getattr(image, 'is_main', False):
                        main_image = image.url
                        break
                if not main_image and images_field:
                    main_image = images_field[0].url

            products_list.append({
                "id": product.id,
                "name": product.name,
                "slug": product.slug,
                "price": float(product.price),
                "discount_price": float(product.discount_price) if product.discount_price else None,
                "image": main_image,
                "brand": product.brand.name if product.brand else None
            })

        return {
            "products": products_list,
            "pagination": {
                "page": page,
                "per_page": per_page,
                "total": total_products
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        # Add stack trace to error log
        logging.error(f"Unexpected error in get_products_by_catalog_endpoint: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Ошибка при получении товаров каталога: {str(e)}")
    

@router.get("/brand/{brand_id}", response_model=List[Dict[str, Any]])
async def get_catalogs_by_brand(
    brand_id: int,
    is_active: bool = True,
    db: AsyncSession = Depends(get_async_db)
):
    """
    Получить каталоги по ID бренда
    """
    try:
        # Проверяем существование бренда
        brand_query = select(Brand).where(Brand.id == brand_id)
        brand_result = await db.execute(brand_query)
        brand = brand_result.scalar_one_or_none()
        
        if not brand:
            raise HTTPException(status_code=404, detail="Бренд не найден")
        
        # Запрос на получение каталогов бренда
        query = select(Catalog).options(
            joinedload(Catalog.category)
        ).where(
            (Catalog.brand_id == brand_id)
        )
        
        if is_active:
            query = query.where(Catalog.is_active == True)
        
        query = query.order_by(Catalog.name)
        
        result = await db.execute(query)
        catalogs = result.unique().scalars().all()
        
        # Формируем ответ
        catalog_list = []
        for catalog in catalogs:
            # Получаем количество продуктов в каталоге
            product_count_query = select(func.count()).select_from(Product).where(
                (Product.catalog_id == catalog.id) & 
                (Product.is_active == True)
            )
            product_count_result = await db.execute(product_count_query)
            product_count = product_count_result.scalar() or 0
            
            catalog_list.append({
                "id": catalog.id,
                "name": catalog.name,
                "slug": catalog.slug,
                "description": catalog.description,
                "image": catalog.image,
                "category": {
                    "id": catalog.category.id,
                    "name": catalog.category.name,
                    "slug": catalog.category.slug
                } if catalog.category else None,
                "product_count": product_count
            })
        
        return catalog_list
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка при получении каталогов бренда: {str(e)}")
    


@router.get("/filtered/", response_model=Dict[str, Any])
async def get_filtered_catalogs(
    page: int = Query(1, ge=1),
    per_page: int = Query(12, ge=1, le=100),
    sort: str = Query("name", regex="^(name|newest|popular|product_count)$"),
    category_id: Optional[int] = None,
    brand_id: Optional[int] = None,
    search: Optional[str] = None,
    is_active: bool = True,
    db: AsyncSession = Depends(get_async_db)
):
    """
    Получить список каталогов с пагинацией и фильтрацией
    """
    try:
        # Базовый запрос без предзагрузки связей
        query = select(Catalog)
        
        # Применяем фильтры
        if is_active:
            query = query.where(Catalog.is_active == True)
        
        if category_id is not None:
            query = query.where(Catalog.category_id == category_id)
            
        if brand_id is not None:
            query = query.where(Catalog.brand_id == brand_id)
            
        if search:
            search_term = f"%{search}%"
            query = query.where(Catalog.name.ilike(search_term))
            
        # Подсчет общего количества записей
        count_query = select(func.count()).select_from(query.subquery())
        count_result = await db.execute(count_query)
        total = count_result.scalar() or 0
        
        # Сортировка
        if sort == "newest":
            query = query.order_by(desc(Catalog.created_at))
        elif sort == "popular" or sort == "product_count":
            # Сортировка по количеству продуктов
            query = query.outerjoin(Product, Catalog.id == Product.catalog_id).\
                group_by(Catalog.id).\
                order_by(desc(func.count(Product.id)))
        else:
            # По умолчанию сортируем по имени
            query = query.order_by(Catalog.name)
        
        # Применяем пагинацию
        offset = (page - 1) * per_page
        query = query.offset(offset).limit(per_page)
        
        # Выполняем запрос без предзагрузки связей
        result = await db.execute(query)
        catalogs = result.scalars().all()
        
        # Формируем ответ
        catalog_list = []
        for catalog in catalogs:
            # Загружаем категорию отдельно
            category_data = None
            if catalog.category_id:
                category_query = select(Category).where(Category.id == catalog.category_id)
                category_result = await db.execute(category_query)
                category = category_result.scalar_one_or_none()
                if category:
                    category_data = {
                        "id": category.id,
                        "name": category.name,
                        "slug": category.slug
                    }
            
            # Загружаем бренд отдельно
            brand_data = None
            if catalog.brand_id:
                brand_query = select(Brand).where(Brand.id == catalog.brand_id)
                brand_result = await db.execute(brand_query)
                brand = brand_result.scalar_one_or_none()
                if brand:
                    brand_data = {
                        "id": brand.id,
                        "name": brand.name,
                        "slug": brand.slug
                    }
            
            # Считаем количество товаров в каталоге
            count_query = select(func.count()).select_from(Product).where(
                (Product.catalog_id == catalog.id) & 
                (Product.is_active == True)
            )
            count_result = await db.execute(count_query)
            product_count = count_result.scalar() or 0
            
            catalog_list.append({
                "id": catalog.id,
                "name": catalog.name,
                "slug": catalog.slug,
                "description": catalog.description,
                "image": catalog.image,
                "brand": brand_data,
                "category": category_data,
                "product_count": product_count
            })
        
        # Рассчитываем количество страниц
        pages = (total + per_page - 1) // per_page  # Округление вверх
        
        return {
            "items": catalog_list,
            "total": total,
            "page": page,
            "per_page": per_page,
            "pages": pages
        }
    
    except Exception as e:
        # Подробное логирование для отладки
        import traceback
        logging.error(f"Error in get_filtered_catalogs: {str(e)}")
        logging.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Ошибка при получении каталогов: {str(e)}")
    
@router.get("/{slug}", response_model=Dict[str, Any])
async def get_catalog_by_slug(
    slug: str,
    include_products: bool = False,
    product_limit: int = Query(4, ge=0, le=20),
    db: AsyncSession = Depends(get_async_db)
):
    """
    Получить каталог по slug с возможностью включения товаров
    """
    try:
        # Запрос на получение каталога
        query = select(Catalog).options(
            joinedload(Catalog.category),
            joinedload(Catalog.brand)
        ).where(
            (Catalog.slug == slug) & (Catalog.is_active == True)
        )
        
        result = await db.execute(query)
        catalog = result.unique().scalar_one_or_none()
        
        if not catalog:
            raise HTTPException(status_code=404, detail="Каталог не найден")
        
        # Считаем количество товаров в каталоге
        count_query = select(func.count()).select_from(Product).where(
            (Product.catalog_id == catalog.id) & 
            (Product.is_active == True)
        )
        count_result = await db.execute(count_query)
        product_count = count_result.scalar() or 0
        
        # Начинаем формировать ответ
        response = {
            "id": catalog.id,
            "name": catalog.name,
            "slug": catalog.slug,
            "image": catalog.image,
            "description": catalog.description,
            "brand": {
                "id": catalog.brand.id,
                "name": catalog.brand.name,
                "slug": catalog.brand.slug
            } if catalog.brand else None,
            "category": {
                "id": catalog.category.id,
                "name": catalog.category.name,
                "slug": catalog.category.slug
            } if catalog.category else None,
            "product_count": product_count
        }
        
        # Если нужно включить товары из каталога
        if include_products:
            products_query = select(Product).options(
                joinedload(Product.product_images),
                joinedload(Product.brand)
            ).where(
                (Product.catalog_id == catalog.id) & 
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
        
        return response
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка при получении каталога: {str(e)}")