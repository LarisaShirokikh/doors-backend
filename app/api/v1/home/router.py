# app/api/v1/home.py
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.crud.banner import banner  
from app.crud.promotion import promotion  
from app.crud.categories import categories
from app.core.database import get_async_db

router = APIRouter()

import logging
logger = logging.getLogger(__name__)

@router.get("/", response_model=dict)
async def get_home_data(session: AsyncSession = Depends(get_async_db)):
    logger.debug("Получение данных для главной страницы")
    
    banners = await banner.get_all(session)
    logger.debug(f"Получено баннеров: {len(banners)}")
    
    promotions = await promotion.get_all(session)
    logger.debug(f"Получено акций: {len(promotions)}")
    
    categories_list = await categories.get_categories(session, limit=10)
    logger.debug(f"Получено категорий: {len(categories_list)}")
    
    return {
        "banners": banners,
        "promotions": promotions,
        "categories": categories_list,
    }
