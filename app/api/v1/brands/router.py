from typing import List, Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc, and_
from sqlalchemy.orm import joinedload
from app.core.database import get_async_db
from app.models.brand import Brand
from app.models.catalog import Catalog
from app.models.product import Product
from app.models.category import Category
from app.models.attributes import product_categories

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
        
        query = query.order_by(desc(Brand.id))
        
        # Выполняем запрос
        result = await db.execute(query)
        brands = result.scalars().all()
        
        # Формируем ответ
        brand_list = []
        for brand in brands:
            # Считаем количество товаров бренда
            count_query = select(func.count()).select_from(Product).where(
                and_(
                    Product.brand_id == brand.id,
                    Product.is_active == True
                )
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

@router.get("/list/", response_model=List[Dict[str, Any]])
async def get_brands_list(
    is_active: bool = True,
    include_counts: bool = True,
    db: AsyncSession = Depends(get_async_db)
):
    return await get_brands(is_active, db)

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
        ).outerjoin(
            Product,
            and_(
                Product.brand_id == Brand.id,
                Product.is_active == True
            )
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
                "product_count": count or 0
            })
        
        return brand_list
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка при получении популярных брендов: {str(e)}")

@router.get("/{brand_id:int}/catalogs/", response_model=List[Dict[str, Any]])
async def get_brand_catalogs_by_id(
    brand_id: int,
    page: int = Query(1, ge=1),
    per_page: int = Query(12, ge=1, le=50),
    db: AsyncSession = Depends(get_async_db)
):
    """
    Получить каталоги бренда по ID бренда
    """
    try:
        # Сначала находим бренд по ID
        brand_query = select(Brand).where(
            and_(
                Brand.id == brand_id,
                Brand.is_active == True
            )
        )
        brand_result = await db.execute(brand_query)
        brand = brand_result.scalar_one_or_none()
        
        if not brand:
            raise HTTPException(status_code=404, detail="Бренд не найден")
        
        # Получаем каталоги через товары бренда
        query = select(Catalog).join(
            Product,
            Product.catalog_id == Catalog.id
        ).where(
            and_(
                Product.brand_id == brand.id,
                Product.is_active == True,
                Catalog.is_active == True
            )
        ).distinct().order_by(Catalog.name)
        
        result = await db.execute(query)
        catalogs = result.scalars().all()
        
        # Формируем ответ
        catalogs_list = []
        for catalog in catalogs:
            # Считаем товары в каталоге для данного бренда
            count_query = select(func.count()).select_from(Product).where(
                and_(
                    Product.catalog_id == catalog.id,
                    Product.brand_id == brand.id,
                    Product.is_active == True
                )
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
        raise HTTPException(status_code=500, detail=f"Ошибка при получении каталогов бренда по ID: {str(e)}")

@router.get("/{brand_id:int}/with-catalogs/", response_model=Dict[str, Any])
async def get_brand_with_catalogs_by_id(
    brand_id: int,
    page: int = Query(1, ge=1),
    per_page: int = Query(12, ge=1, le=50),
    db: AsyncSession = Depends(get_async_db)
):
    """
    Получить бренд с каталогами по ID в одном запросе
    """
    try:
        # Получаем бренд по ID
        brand_query = select(Brand).where(
            and_(
                Brand.id == brand_id,
                Brand.is_active == True
            )
        )
        brand_result = await db.execute(brand_query)
        brand = brand_result.scalar_one_or_none()
        
        if not brand:
            raise HTTPException(status_code=404, detail="Бренд не найден")
        
        # Считаем общее количество товаров бренда
        count_query = select(func.count()).select_from(Product).where(
            and_(
                Product.brand_id == brand.id,
                Product.is_active == True
            )
        )
        count_result = await db.execute(count_query)
        product_count = count_result.scalar() or 0
        
        # Получаем каталоги через товары бренда
        catalogs_query = select(Catalog).join(
            Product,
            Product.catalog_id == Catalog.id
        ).where(
            and_(
                Product.brand_id == brand.id,
                Product.is_active == True,
                Catalog.is_active == True
            )
        ).distinct().order_by(Catalog.name)
        
        catalogs_result = await db.execute(catalogs_query)
        catalogs = catalogs_result.scalars().all()
        
        # Формируем каталоги с подсчетом товаров
        catalogs_list = []
        for catalog in catalogs:
            cat_count_query = select(func.count()).select_from(Product).where(
                and_(
                    Product.catalog_id == catalog.id,
                    Product.brand_id == brand.id,
                    Product.is_active == True
                )
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
        raise HTTPException(status_code=500, detail=f"Ошибка при получении бренда с каталогами по ID: {str(e)}")

@router.patch("/{brand_id:int}", response_model=Dict[str, Any])
async def patch_brand(
    brand_id: int,
    brand_data: dict,
    db: AsyncSession = Depends(get_async_db)
):
    """
    Частично обновить бренд по ID
    """
    try:
        # Находим бренд
        brand_query = select(Brand).where(Brand.id == brand_id)
        brand_result = await db.execute(brand_query)
        brand = brand_result.scalar_one_or_none()
        
        if not brand:
            raise HTTPException(status_code=404, detail="Бренд не найден")
        
        # Обновляем поля
        for key, value in brand_data.items():
            if hasattr(brand, key):
                setattr(brand, key, value)
        
        await db.commit()
        await db.refresh(brand)
        
        return {
            "id": brand.id,
            "name": brand.name,
            "slug": brand.slug,
            "description": brand.description,
            "logo_url": brand.logo_url,
            "website": brand.website,
            "is_active": brand.is_active
        }
    
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Ошибка при обновлении бренда: {str(e)}")

@router.get("/{brand_id:int}/", response_model=Dict[str, Any])
async def get_brand_by_id_with_slash(
    brand_id: int,
    include_products: bool = False,
    include_categories: bool = False,
    product_limit: int = Query(4, ge=0, le=20),
    db: AsyncSession = Depends(get_async_db)
):
    """
    Получить бренд по ID (с trailing slash)
    """
    return await get_brand_by_id_internal(brand_id, include_products, include_categories, product_limit, db)

@router.get("/{brand_id:int}", response_model=Dict[str, Any])
async def get_brand_by_id(
    brand_id: int,
    include_products: bool = False,
    include_categories: bool = False,
    product_limit: int = Query(4, ge=0, le=20),
    db: AsyncSession = Depends(get_async_db)
):
    """
    Получить бренд по ID (без trailing slash)
    """
    return await get_brand_by_id_internal(brand_id, include_products, include_categories, product_limit, db)

@router.get("/{slug}/catalogs/", response_model=List[Dict[str, Any]])
async def get_brand_catalogs_by_slug(
    slug: str, 
    page: int = Query(1, ge=1),
    per_page: int = Query(12, ge=1, le=50),
    db: AsyncSession = Depends(get_async_db)
):
    """
    Получить каталоги бренда по slug
    """
    try:
        # Сначала находим бренд по slug
        brand_query = select(Brand).where(
            and_(
                Brand.slug == slug,
                Brand.is_active == True
            )
        )
        brand_result = await db.execute(brand_query)
        brand = brand_result.scalar_one_or_none()
        
        if not brand:
            raise HTTPException(status_code=404, detail="Бренд не найден")
        
        # Получаем каталоги через товары бренда
        query = select(Catalog).join(
            Product,
            Product.catalog_id == Catalog.id
        ).where(
            and_(
                Product.brand_id == brand.id,
                Product.is_active == True,
                Catalog.is_active == True
            )
        ).distinct().order_by(Catalog.name)
        
        result = await db.execute(query)
        catalogs = result.scalars().all()
        
        # Формируем ответ
        catalogs_list = []
        for catalog in catalogs:
            # Считаем товары в каталоге для данного бренда
            count_query = select(func.count()).select_from(Product).where(
                and_(
                    Product.catalog_id == catalog.id,
                    Product.brand_id == brand.id,
                    Product.is_active == True
                )
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
        raise HTTPException(status_code=500, detail=f"Ошибка при получении каталогов бренда по slug: {str(e)}")

@router.get("/{slug}/with-catalogs/", response_model=Dict[str, Any])
async def get_brand_with_catalogs_by_slug(
    slug: str,
    page: int = Query(1, ge=1),
    per_page: int = Query(12, ge=1, le=50),
    db: AsyncSession = Depends(get_async_db)
):
    """
    Получить бренд с каталогами по slug в одном запросе
    """
    try:
        # Получаем бренд по slug
        brand_query = select(Brand).where(
            and_(
                Brand.slug == slug,
                Brand.is_active == True
            )
        )
        brand_result = await db.execute(brand_query)
        brand = brand_result.scalar_one_or_none()
        
        if not brand:
            raise HTTPException(status_code=404, detail="Бренд не найден")
        
        # Считаем общее количество товаров бренда
        count_query = select(func.count()).select_from(Product).where(
            and_(
                Product.brand_id == brand.id,
                Product.is_active == True
            )
        )
        count_result = await db.execute(count_query)
        product_count = count_result.scalar() or 0
        
        # Получаем каталоги через товары бренда
        catalogs_query = select(Catalog).join(
            Product,
            Product.catalog_id == Catalog.id
        ).where(
            and_(
                Product.brand_id == brand.id,
                Product.is_active == True,
                Catalog.is_active == True
            )
        ).distinct().order_by(Catalog.name)
        
        catalogs_result = await db.execute(catalogs_query)
        catalogs = catalogs_result.scalars().all()
        
        # Формируем каталоги с подсчетом товаров
        catalogs_list = []
        for catalog in catalogs:
            cat_count_query = select(func.count()).select_from(Product).where(
                and_(
                    Product.catalog_id == catalog.id,
                    Product.brand_id == brand.id,
                    Product.is_active == True
                )
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
        raise HTTPException(status_code=500, detail=f"Ошибка при получении бренда с каталогами по slug: {str(e)}")

@router.get("/{slug}/", response_model=Dict[str, Any])
async def get_brand_by_slug_with_slash(
    slug: str,
    include_products: bool = False,
    include_categories: bool = False,
    product_limit: int = Query(4, ge=0, le=20),
    db: AsyncSession = Depends(get_async_db)
):
    """
    Получить бренд по slug с возможностью включения товаров и категорий (с trailing slash)
    """
    return await get_brand_by_slug_internal(slug, include_products, include_categories, product_limit, db)

@router.get("/{slug}", response_model=Dict[str, Any])
async def get_brand_by_slug(
    slug: str,
    include_products: bool = False,
    include_categories: bool = False,
    product_limit: int = Query(4, ge=0, le=20),
    db: AsyncSession = Depends(get_async_db)
):
    """
    Получить бренд по slug с возможностью включения товаров и категорий (без trailing slash)
    """
    return await get_brand_by_slug_internal(slug, include_products, include_categories, product_limit, db)

async def get_brand_by_id_internal(
    brand_id: int,
    include_products: bool = False,
    include_categories: bool = False,
    product_limit: int = 4,
    db: AsyncSession = None
):
    """
    Внутренняя функция для получения бренда по ID
    """
    try:
        # Запрос на получение бренда
        query = select(Brand).where(
            and_(
                Brand.id == brand_id,
                Brand.is_active == True
            )
        )
        
        result = await db.execute(query)
        brand = result.scalar_one_or_none()
        
        if not brand:
            raise HTTPException(status_code=404, detail="Бренд не найден")
        
        # Считаем количество товаров бренда
        count_query = select(func.count()).select_from(Product).where(
            and_(
                Product.brand_id == brand.id,
                Product.is_active == True
            )
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
        
        # Получаем категории только через товары бренда
        if include_categories:
            try:
                categories_query = select(Category).join(
                    product_categories,
                    Category.id == product_categories.c.category_id
                ).join(
                    Product,
                    Product.id == product_categories.c.product_id
                ).where(
                    and_(
                        Product.brand_id == brand.id,
                        Product.is_active == True,
                        Category.is_active == True
                    )
                ).distinct().order_by(Category.name)
                
                categories_result = await db.execute(categories_query)
                categories = categories_result.scalars().all()
                
                categories_list = []
                for category in categories:
                    cat_count_query = select(func.count()).select_from(Product).join(
                        product_categories, 
                        Product.id == product_categories.c.product_id
                    ).where(
                        and_(
                            product_categories.c.category_id == category.id,
                            Product.brand_id == brand.id,
                            Product.is_active == True
                        )
                    )
                    cat_count_result = await db.execute(cat_count_query)
                    cat_product_count = cat_count_result.scalar() or 0
                    
                    if cat_product_count > 0:
                        categories_list.append({
                            "id": category.id,
                            "name": category.name,
                            "slug": category.slug,
                            "image_url": getattr(category, 'image_url', None),
                            "product_count": cat_product_count
                        })
                
                response["categories"] = categories_list
                
            except Exception as cat_error:
                print(f"Предупреждение: Не удалось загрузить категории для бренда {brand_id}: {cat_error}")
                response["categories"] = []
        
        # Получаем товары бренда
        if include_products:
            try:
                products_query = select(Product).where(
                    and_(
                        Product.brand_id == brand.id,
                        Product.is_active == True
                    )
                ).order_by(
                    desc(Product.popularity_score)
                ).limit(product_limit)
                
                try:
                    products_query = products_query.options(joinedload(Product.product_images))
                    use_images = True
                except Exception:
                    use_images = False
                
                products_result = await db.execute(products_query)
                
                if use_images:
                    try:
                        products = products_result.unique().scalars().all()
                    except Exception:
                        products = products_result.scalars().all()
                else:
                    products = products_result.scalars().all()
                
                products_list = []
                for product in products:
                    main_image = None
                    if use_images:
                        try:
                            if hasattr(product, 'product_images') and product.product_images:
                                for image in product.product_images:
                                    if hasattr(image, 'is_main') and image.is_main:
                                        main_image = image.url
                                        break
                                
                                if not main_image and product.product_images:
                                    main_image = product.product_images[0].url
                        except Exception:
                            pass
                    
                    products_list.append({
                        "id": product.id,
                        "name": product.name,
                        "slug": product.slug,
                        "price": float(product.price) if product.price else 0.0,
                        "discount_price": float(product.discount_price) if product.discount_price else None,
                        "image": main_image
                    })
                
                response["products"] = products_list
                
            except Exception as prod_error:
                print(f"Предупреждение: Не удалось загрузить товары для бренда {brand_id}: {prod_error}")
                response["products"] = []
        
        return response
    
    except HTTPException:
        raise
    except Exception as e:
        print(f"Ошибка в get_brand_by_id для ID '{brand_id}': {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Ошибка при получении бренда: {str(e)}")

async def get_brand_by_slug_internal(
    slug: str,
    include_products: bool = False,
    include_categories: bool = False,
    product_limit: int = 4,
    db: AsyncSession = None
):
    """
    Внутренняя функция для получения бренда по slug
    """
    try:
        # Запрос на получение бренда
        query = select(Brand).where(
            and_(
                Brand.slug == slug,
                Brand.is_active == True
            )
        )
        
        result = await db.execute(query)
        brand = result.scalar_one_or_none()
        
        if not brand:
            raise HTTPException(status_code=404, detail="Бренд не найден")
        
        # Считаем количество товаров бренда
        count_query = select(func.count()).select_from(Product).where(
            and_(
                Product.brand_id == brand.id,
                Product.is_active == True
            )
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
        
        # Получаем категории только через товары бренда
        if include_categories:
            try:
                categories_query = select(Category).join(
                    product_categories,
                    Category.id == product_categories.c.category_id
                ).join(
                    Product,
                    Product.id == product_categories.c.product_id
                ).where(
                    and_(
                        Product.brand_id == brand.id,
                        Product.is_active == True,
                        Category.is_active == True
                    )
                ).distinct().order_by(Category.name)
                
                categories_result = await db.execute(categories_query)
                categories = categories_result.scalars().all()
                
                categories_list = []
                for category in categories:
                    cat_count_query = select(func.count()).select_from(Product).join(
                        product_categories, 
                        Product.id == product_categories.c.product_id
                    ).where(
                        and_(
                            product_categories.c.category_id == category.id,
                            Product.brand_id == brand.id,
                            Product.is_active == True
                        )
                    )
                    cat_count_result = await db.execute(cat_count_query)
                    cat_product_count = cat_count_result.scalar() or 0
                    
                    if cat_product_count > 0:
                        categories_list.append({
                            "id": category.id,
                            "name": category.name,
                            "slug": category.slug,
                            "image_url": getattr(category, 'image_url', None),
                            "product_count": cat_product_count
                        })
                
                response["categories"] = categories_list
                
            except Exception as cat_error:
                print(f"Предупреждение: Не удалось загрузить категории для бренда {slug}: {cat_error}")
                response["categories"] = []
        
        # Получаем товары бренда
        if include_products:
            try:
                products_query = select(Product).where(
                    and_(
                        Product.brand_id == brand.id,
                        Product.is_active == True
                    )
                ).order_by(
                    desc(Product.popularity_score)
                ).limit(product_limit)
                
                try:
                    products_query = products_query.options(joinedload(Product.product_images))
                    use_images = True
                except Exception:
                    use_images = False
                
                products_result = await db.execute(products_query)
                
                if use_images:
                    try:
                        products = products_result.unique().scalars().all()
                    except Exception:
                        products = products_result.scalars().all()
                else:
                    products = products_result.scalars().all()
                
                products_list = []
                for product in products:
                    main_image = None
                    if use_images:
                        try:
                            if hasattr(product, 'product_images') and product.product_images:
                                for image in product.product_images:
                                    if hasattr(image, 'is_main') and image.is_main:
                                        main_image = image.url
                                        break
                                
                                if not main_image and product.product_images:
                                    main_image = product.product_images[0].url
                        except Exception:
                            pass
                    
                    products_list.append({
                        "id": product.id,
                        "name": product.name,
                        "slug": product.slug,
                        "price": float(product.price) if product.price else 0.0,
                        "discount_price": float(product.discount_price) if product.discount_price else None,
                        "image": main_image
                    })
                
                response["products"] = products_list
                
            except Exception as prod_error:
                print(f"Предупреждение: Не удалось загрузить товары для бренда {slug}: {prod_error}")
                response["products"] = []
        
        return response
    
    except HTTPException:
        raise
    except Exception as e:
        print(f"Ошибка в get_brand_by_slug для slug '{slug}': {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Ошибка при получении бренда: {str(e)}")