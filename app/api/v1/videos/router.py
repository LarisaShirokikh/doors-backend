from typing import Any, Dict, List
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_async_db
from app.crud.video import get_featured_videos, get_latest_videos, get_popular_videos, get_videos_by_product


router = APIRouter()

@router.get("/featured/", response_model=List[Dict[str, Any]])
async def get_featured_videos_api(
    limit: int = Query(6, ge=1, le=20),
    db: AsyncSession = Depends(get_async_db)
):
    """
    Получить рекомендуемые видео с интеллектуальным алгоритмом
    """
    videos = await get_featured_videos(db, limit)
    return videos

@router.get("/by-product/{product_slug}", response_model=List[Dict[str, Any]])
async def get_videos_by_product_api(
    product_slug: str,
    limit: int = Query(10, ge=1, le=50),
    db: AsyncSession = Depends(get_async_db)
):
    """
    Получить видео для конкретного продукта по его slug
    """
    videos = await get_videos_by_product(db, product_slug, limit)
    if not videos:
        raise HTTPException(status_code=404, detail=f"Продукт со slug {product_slug} не найден или у него нет видео")
    return videos

@router.get("/popular/", response_model=List[Dict[str, Any]])
async def get_popular_videos_api(
    limit: int = Query(6, ge=1, le=20),
    db: AsyncSession = Depends(get_async_db)
):
    """
    Получить популярные видео на основе рейтинга продукта
    """
    videos = await get_popular_videos(db, limit)
    return videos

@router.get("/latest/", response_model=List[Dict[str, Any]])
async def get_latest_videos_api(
    limit: int = Query(6, ge=1, le=20),
    db: AsyncSession = Depends(get_async_db)
):
    """
    Получить последние добавленные видео
    """
    videos = await get_latest_videos(db, limit)
    return videos

@router.get("/recent/", response_model=List[Dict[str, Any]])
async def get_recent_videos_api(
    limit: int = Query(6, ge=1, le=20),
    db: AsyncSession = Depends(get_async_db)
):
    """
    Получить недавние видео (алиас для latest)
    """
    videos = await get_latest_videos(db, limit)
    return videos