from typing import Any, Dict, List

from sqlalchemy import desc, select
from sqlalchemy.orm import joinedload
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.product import Product
from app.models.video import Video


async def get_featured_videos(db: AsyncSession, limit: int = 6) -> List[Dict[str, Any]]:
    """Получение рекомендуемых видео"""
    query = (
        select(Video)
        .options(joinedload(Video.product).joinedload(Product.product_images))
        .where(Video.is_active == True, Video.is_featured == True)
        .order_by(desc(Video.created_at))
        .limit(limit)
    )
    
    result = await db.execute(query)
    videos = result.unique().scalars().all()
    
    featured_videos = []
    
    for video in videos:
        video_data = {
            "id": video.id,
            "uuid": video.uuid,
            "title": video.title,
            "description": video.description,
            "url": video.url,
            "thumbnail_url": video.thumbnail_url,
            "duration": video.duration,
            "created_at": video.created_at,
            "is_featured": video.is_featured,
            "auto_detected": video.auto_detected,
            "product": None
        }
        
        # Добавляем информацию о продукте, если есть
        if video.product:
            main_image = None
            if hasattr(video.product, 'product_images') and video.product.product_images:
                main_image = video.product.product_images[0].url if video.product.product_images else None
                
            video_data["product"] = {
                "id": video.product.id,
                "uuid": video.product.uuid,
                "name": video.product.name,
                "slug": video.product.slug,
                "price": video.product.price,
                "discount_price": video.product.discount_price,
                "in_stock": video.product.in_stock,
                "is_active": video.product.is_active,
                "is_new": video.product.is_new,
                "rating": video.product.rating,
                "review_count": video.product.review_count,
                "main_image": main_image
            }
        
        featured_videos.append(video_data)
    
    return featured_videos

async def get_videos_by_product(db: AsyncSession, product_slug: str, limit: int = 10) -> List[Dict[str, Any]]:
    """Получение видео для конкретного продукта"""
    # Сначала находим продукт
    product_query = select(Product).where(Product.slug == product_slug, Product.is_active == True)
    product_result = await db.execute(product_query)
    product = product_result.scalar_one_or_none()
    
    if not product:
        return []
    
    # Запрос видео для этого продукта
    query = (
        select(Video)
        .where(Video.product_id == product.id, Video.is_active == True)
        .order_by(desc(Video.created_at))
        .limit(limit)
    )
    
    result = await db.execute(query)
    videos = result.scalars().all()
    
    # Формируем ответ
    product_videos = []
    
    for video in videos:
        video_data = {
            "id": video.id,
            "uuid": video.uuid,
            "title": video.title,
            "description": video.description,
            "url": video.url,
            "thumbnail_url": video.thumbnail_url,
            "duration": video.duration,
            "created_at": video.created_at,
            "is_featured": video.is_featured
        }
        
        product_videos.append(video_data)
    
    return product_videos

async def get_popular_videos(db: AsyncSession, limit: int = 6) -> List[Dict[str, Any]]:
    """Получение популярных видео на основе рейтинга продукта"""
    query = (
        select(Video)
        .join(Product, Video.product_id == Product.id)
        .where(Video.is_active == True, Product.is_active == True)
        .order_by(desc(Product.popularity_score), desc(Product.rating), desc(Video.created_at))
        .options(joinedload(Video.product))
        .limit(limit)
    )
    
    result = await db.execute(query)
    videos = result.unique().scalars().all()
    
    # Формируем ответ
    popular_videos = []
    
    for video in videos:
        video_data = {
            "id": video.id,
            "uuid": video.uuid,
            "title": video.title,
            "description": video.description,
            "url": video.url,
            "thumbnail_url": video.thumbnail_url,
            "duration": video.duration,
            "created_at": video.created_at,
            "is_featured": video.is_featured,
            "product": None
        }
        
        # Добавляем информацию о продукте, если есть
        if video.product:
            video_data["product"] = {
                "id": video.product.id,
                "uuid": video.product.uuid,
                "name": video.product.name,
                "slug": video.product.slug,
                "price": video.product.price,
                "discount_price": video.product.discount_price,
                "in_stock": video.product.in_stock,
                "rating": video.product.rating,
                "popularity_score": video.product.popularity_score,
                "main_image": video.product.product_images[0].url if video.product.product_images else None
            }
        
        popular_videos.append(video_data)
    
    return popular_videos