from typing import List, Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc
from sqlalchemy.orm import joinedload
from app.core.database import get_async_db
from app.models.product import Product
from app.models.brand import Brand
from app.models.attributes import product_category
from app.models.category import Category
from app.crud.product import product as product_crud

router = APIRouter()

@router.get("/", response_model=List[Dict[str, Any]])
async def get_categories(
    parent_id: Optional[int] = None,
    brand_id: Optional[int] = None,
    is_active: bool = True,
    include_counts: bool = True,
    db: AsyncSession = Depends(get_async_db)
):
    """
    Получить список категорий с возможностью фильтрации
    """
    try:
        # Базовый запрос с предзагрузкой бренда
        query = select(Category).options(
            joinedload(Category.brand)
        )
        
        # Применяем фильтры
        if is_active:
            query = query.where(Category.is_active == True)
        
        if parent_id is not None:
            query = query.where(Category.parent_id == parent_id)
        else:
            # По умолчанию возвращаем категории верхнего уровня
            query = query.where(Category.parent_id.is_(None))
        
        if brand_id is not None:
            query = query.where(Category.brand_id == brand_id)
        
        # Сортировка по имени
        query = query.order_by(Category.name)
        
        # Выполняем запрос
        result = await db.execute(query)
        categories = result.unique().scalars().all()
        
        # Формируем ответ
        category_list = []
        for category in categories:
            category_data = {
                "id": category.id,
                "name": category.name,
                "slug": category.slug,
                "image_url": category.image_url,
                "parent_id": category.parent_id,
                "brand": {
                    "id": category.brand.id,
                    "name": category.brand.name,
                    "slug": category.brand.slug
                } if category.brand else None
            }
            
            # Если нужно включить количество продуктов
            if include_counts:
                if hasattr(category, 'product_count') and category.product_count is not None:
                    # Используем существующее поле, если оно есть
                    category_data["product_count"] = category.product_count
                else:
                    # Иначе делаем запрос на подсчет
                    count_query = select(func.count()).select_from(product_category).where(
                        product_category.c.category_id == category.id
                    )
                    count_result = await db.execute(count_query)
                    category_data["product_count"] = count_result.scalar() or 0
            
            category_list.append(category_data)
        
        return category_list
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка при получении категорий: {str(e)}")

@router.get("/{category_id}/products/", response_model=Dict[str, Any])
async def get_products_by_category(
    category_id: int,
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    sort_by: str = "created_at",
    sort_order: str = Query("desc", regex="^(asc|desc)$"),
    db: AsyncSession = Depends(get_async_db)
):
    """
    Получить продукты для категории по ID с пагинацией и сортировкой
    """
    try:
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
        print(f"Ошибка при получении продуктов для категории {category_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Ошибка при получении продуктов: {str(e)}")


@router.get("/{slug}", response_model=Dict[str, Any])
async def get_category_by_slug(
    slug: str,
    include_children: bool = True,
    include_products: bool = False,
    product_limit: int = Query(4, ge=0, le=20),
    db: AsyncSession = Depends(get_async_db)
):
    """
    Получить категорию по slug с возможностью включения дочерних категорий и продуктов
    """
    try:
        # Запрос на получение категории
        query = select(Category).options(
            joinedload(Category.brand)
        ).where(
            (Category.slug == slug) & (Category.is_active == True)
        )
        
        result = await db.execute(query)
        category = result.unique().scalar_one_or_none()
        
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
            "meta_keywords": category.meta_keywords,
            "parent_id": category.parent_id,
            "brand": {
                "id": category.brand.id,
                "name": category.brand.name,
                "slug": category.brand.slug
            } if category.brand else None
        }
        
        # Если нужно включить дочерние категории
        if include_children:
            children_query = select(Category).where(
                (Category.parent_id == category.id) & (Category.is_active == True)
            ).order_by(Category.name)
            
            children_result = await db.execute(children_query)
            children = children_result.scalars().all()
            
            children_list = []
            for child in children:
                # Считаем количество товаров для дочерней категории
                count_query = select(func.count()).select_from(product_category).where(
                    product_category.c.category_id == child.id
                )
                count_result = await db.execute(count_query)
                product_count = count_result.scalar() or 0
                
                children_list.append({
                    "id": child.id,
                    "name": child.name,
                    "slug": child.slug,
                    "image_url": child.image_url,
                    "product_count": product_count
                })
            
            response["children"] = children_list
        
        # Если нужно включить продукты
        if include_products:
            products_query = select(Product).options(
                joinedload(Product.product_images),
                joinedload(Product.brand)
            ).join(
                product_category
            ).where(
                (product_category.c.category_id == category.id) &
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
        count_query = select(func.count()).select_from(product_category).where(
            product_category.c.category_id == category.id
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
            func.count(product_category.c.product_id).label("product_count")
        ).join(
            product_category,
            Category.id == product_category.c.category_id,
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

@router.get("/tree/", response_model=List[Dict[str, Any]])
async def get_category_tree(
    brand_id: Optional[int] = None,
    db: AsyncSession = Depends(get_async_db)
):
    """
    Получить дерево категорий (иерархию)
    """
    try:
        # Получаем все категории верхнего уровня
        root_query = select(Category).options(
            joinedload(Category.brand)
        ).where(
            (Category.is_active == True) & 
            (Category.parent_id.is_(None))
        )
        
        if brand_id is not None:
            root_query = root_query.where(Category.brand_id == brand_id)
        
        root_query = root_query.order_by(Category.name)
        
        root_result = await db.execute(root_query)
        root_categories = root_result.unique().scalars().all()
        
        # Рекурсивная функция для построения дерева
        async def build_category_tree(parent_id=None):
            query = select(Category).where(
                (Category.is_active == True) & 
                (Category.parent_id == parent_id)
            )
            
            if brand_id is not None:
                query = query.where(Category.brand_id == brand_id)
            
            query = query.order_by(Category.name)
            
            result = await db.execute(query)
            categories = result.scalars().all()
            
            tree = []
            for category in categories:
                # Получаем количество товаров в категории
                count_query = select(func.count()).select_from(product_category).where(
                    product_category.c.category_id == category.id
                )
                count_result = await db.execute(count_query)
                product_count = count_result.scalar() or 0
                
                # Получаем дочерние категории
                children = await build_category_tree(category.id)
                
                tree.append({
                    "id": category.id,
                    "name": category.name,
                    "slug": category.slug,
                    "image_url": category.image_url,
                    "product_count": product_count,
                    "children": children
                })
            
            return tree
        
        # Формируем дерево категорий
        category_tree = []
        for root_category in root_categories:
            # Получаем количество товаров в корневой категории
            count_query = select(func.count()).select_from(product_category).where(
                product_category.c.category_id == root_category.id
            )
            count_result = await db.execute(count_query)
            product_count = count_result.scalar() or 0
            
            # Получаем дочерние категории
            children = await build_category_tree(root_category.id)
            
            category_tree.append({
                "id": root_category.id,
                "name": root_category.name,
                "slug": root_category.slug,
                "image_url": root_category.image_url,
                "product_count": product_count,
                "children": children
            })
        
        return category_tree
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка при получении дерева категорий: {str(e)}")
    
@router.get("/list/", response_model=List[Dict[str, Any]])
async def get_categories_list(
    parent_id: Optional[int] = None,
    brand_id: Optional[int] = None,
    is_active: bool = True,
    include_counts: bool = True,
    db: AsyncSession = Depends(get_async_db)
):
    return await get_categories(parent_id, brand_id, is_active, include_counts, db)