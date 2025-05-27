# app/api/v1/search/router.py
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_async_db
from app.crud.product import product as product_crud
from app.schemas.search import SearchSuggestionsResponse

router = APIRouter()

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
    
    # Преобразуем продукты в подсказки для поиска
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