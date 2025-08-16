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
    
    return await product_crud.get_search_suggestions(db=db, query=q, limit=limit)