from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Path
from sqlalchemy.orm import Session
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_async_db
from app.crud.categories import categories as categories_crud
from app.schemas.category import CategoryCreate, CategoryRead, CategoryUpdate
from app.schemas.product import ProductCreate
from app.services.products import auto_categorize_product

router = APIRouter()

@router.get("/", response_model=List[CategoryRead])
async def read_categories(
    db: AsyncSession = Depends(get_async_db),
    skip: int = 0,
    limit: int = 100,
    manufacturer_id: Optional[int] = None
):
    """
    Получить список всех категорий с возможностью фильтрации по производителю
    """
    return await categories_crud.get_categories(
        db, 
        skip=skip, 
        limit=limit, 
        manufacturer_id=manufacturer_id
    )

@router.get("/{category_id}", response_model=CategoryRead)
async def read_category(
    category_id: int = Path(..., title="ID категории", gt=0),
    db: AsyncSession = Depends(get_async_db),
):
    """
    Получить категорию по ID
    """
    category = await categories_crud.get_category(db, category_id=category_id)
    if category is None:
        raise HTTPException(status_code=404, detail="Категория не найдена")
    return category  # Уже Pydantic модель

@router.get("/popular/", response_model=List[CategoryRead])
async def get_popular_categories(
    limit: int = Query(4, ge=1, le=20),
    db: AsyncSession = Depends(get_async_db),
):
    """
    Получить популярные категории
    """
    categories = await categories_crud.get_categories(db, limit=limit)  # Уже список Pydantic моделей

    return categories

@router.post("/auto-category/")
async def predict_category(product: ProductCreate):
    category = await auto_categorize_product(product)
    return {"predicted_category": category}