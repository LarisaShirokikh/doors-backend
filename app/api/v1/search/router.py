# app/api/v1/search/router.py
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional
from app.core.database import get_async_db
from app.crud.product import product as product_crud
from app.schemas.search import SearchResponse, SearchSuggestionsResponse

router = APIRouter()

@router.get(
        "/", 
        response_model=SearchResponse
    )
async def search_products(
    q: str,
    page: int = Query(1, ge=1),
    per_page: int = Query(24, ge=1, le=100),
    sort: str = Query("popular"),
    min_price: Optional[float] = None,
    max_price: Optional[float] = None,
    category_id: Optional[str] = None,
    brand_slug: Optional[str] = None,
    db: AsyncSession = Depends(get_async_db)
):
    return await product_crud.search_products_paginated(
        db=db,
        query=q,
        page=page,
        per_page=per_page,
        sort=sort,
        min_price=min_price,
        max_price=max_price,
        category_id=category_id,
        brand_slug=brand_slug
    )

@router.get("/suggestions/", response_model=SearchSuggestionsResponse)
async def get_search_suggestions(
    q: str,
    limit: int = Query(5, ge=1, le=20),
    db: AsyncSession = Depends(get_async_db)
):
    """
    Получение подсказок для поисковой строки
    """
    if len(q) < 2:
        return {"suggestions": []}
    
    # Используем существующую функцию поиска в репозитории
    products = await product_crud.search_products(
        db=db,
        query=q,
        limit=limit,
        sort="popular"
    )
    
    
    suggestions = []
    for product in products:
        image = None
        if hasattr(product, 'image'):
            if isinstance(product.image, list) and product.image:
                image = product.image[0]
            else:
                image = product.image
                
        category = None
        if hasattr(product, 'catalog') and product.catalog:
            category = product.catalog.name
        elif hasattr(product, 'category') and product.category:
            category = product.category.name
            
        suggestions.append({
            "id": product.id,
            "name": product.name,
            "slug": product.slug,
            "image": image,
            "category": category
        })
    
    return {"suggestions": suggestions}