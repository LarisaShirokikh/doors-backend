from typing import List, Optional, Dict
from fastapi import APIRouter, Depends, HTTPException, Query, Path
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_async_db
from app.crud.product import product as product_crud
from app.schemas.product import ProductCreate, ProductRead, ProductUpdate

router = APIRouter()

@router.get("/", response_model=List[Dict])
async def read_products(
    db: AsyncSession = Depends(get_async_db),
    skip: int = 0,
    limit: int = 100,
    catalog_id: Optional[int] = None,
    category_id: Optional[int] = None,
    min_price: Optional[float] = None,
    max_price: Optional[float] = None,
    in_stock: Optional[bool] = None,
    search: Optional[str] = None,
    sort_by: Optional[str] = None,
    sort_desc: bool = False
):
    """
    Получить список товаров с фильтрацией и сортировкой
    """
    return await product_crud.get_all_products_filtered(
        db, 
        skip=skip, 
        limit=limit,
        catalog_id=catalog_id,
        category_id=category_id,
        min_price=min_price,
        max_price=max_price,
        in_stock=in_stock,
        search=search,
        sort_by=sort_by,
        sort_desc=sort_desc
    )

@router.get("/{product_id}", response_model=Dict)
async def read_product(
    product_id: int = Path(..., title="ID товара", gt=0),
    db: AsyncSession = Depends(get_async_db)
):
    """
    Получить детальную информацию о товаре по ID
    """
    product = await product_crud.get_product_by_id(db, product_id=product_id)
    if product is None:
        raise HTTPException(status_code=404, detail="Товар не найден")
    return product

@router.post("/", response_model=Dict, status_code=201)
async def create_product(
    product: ProductCreate, 
    db: AsyncSession = Depends(get_async_db)
):
    """
    Создать новый товар
    """
    return await product_crud.create_product(db=db, product_data=product, auto_commit=True)

@router.get("/recommended/", response_model=List[Dict])
async def get_recommended_products(
    limit: int = Query(8, ge=1, le=50),
    db: AsyncSession = Depends(get_async_db)
):
    """
    Получить рекомендуемые товары
    """
    return await product_crud.get_recommended_products(db, limit=limit)

@router.get("/new/", response_model=List[Dict])
async def get_new_products(
    limit: int = Query(8, ge=1, le=50),
    db: AsyncSession = Depends(get_async_db)
):
    """
    Получить новые товары
    """
    return await product_crud.get_new_products(db, limit=limit)

@router.get("/discount/", response_model=List[Dict])
async def get_discount_products(
    limit: int = Query(10, ge=1, le=50),
    db: AsyncSession = Depends(get_async_db)
):
    """
    Получить товары со скидкой
    """
    return await product_crud.get_discount_products(db, limit=limit)