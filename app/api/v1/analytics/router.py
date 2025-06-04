# app/api/v1/analytics/router.py
from fastapi import APIRouter, Depends, BackgroundTasks, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Dict, Any, Optional
from app.core.database import get_async_db
from app.crud.product_ranking import ProductRanking

router = APIRouter()

@router.get("/product/{product_id}/view/")
async def track_product_view(
    product_id: int,
    page_type: Optional[str] = Query(None),
    location: Optional[str] = Query(None),
    referrer: Optional[str] = Query(None),
    device_type: Optional[str] = Query(None),
    url: Optional[str] = Query(None),
    timestamp: Optional[str] = Query(None),
    background_tasks: BackgroundTasks = None,
    db: AsyncSession = Depends(get_async_db)
):
    """
    Обрабатывает просмотр продукта
    """
    try:
        # Собираем данные сессии из query параметров
        session_data = {}
        if page_type:
            session_data['page_type'] = page_type
        if location:
            session_data['location'] = location
        if referrer:
            session_data['referrer'] = referrer
        if device_type:
            session_data['device_type'] = device_type
        if url:
            session_data['url'] = url
        if timestamp:
            session_data['timestamp'] = timestamp
        
        # Выполняем в фоне или синхронно
        if background_tasks:
            background_tasks.add_task(
                ProductRanking.process_product_view,
                db,
                product_id,
                session_data
            )
        else:
            await ProductRanking.process_product_view(db, product_id, session_data)
        
        return {"success": True}
        
    except Exception as e:
        print(f"Ошибка при обработке просмотра продукта: {str(e)}")
        return {"success": False, "message": f"Ошибка при обработке: {str(e)}"}

@router.get("/product/{product_id}/interaction/")
async def track_product_interaction(
    product_id: int,
    interaction_type: str = Query(...),
    # Параметры взаимодействия
    duration_seconds: Optional[int] = Query(None),
    image_index: Optional[int] = Query(None),
    action: Optional[str] = Query(None),
    button_text: Optional[str] = Query(None),
    # Параметры сессии
    page_type: Optional[str] = Query(None),
    location: Optional[str] = Query(None),
    referrer: Optional[str] = Query(None),
    device_type: Optional[str] = Query(None),
    url: Optional[str] = Query(None),
    timestamp: Optional[str] = Query(None),
    background_tasks: BackgroundTasks = None,
    db: AsyncSession = Depends(get_async_db)
):
    """
    Обрабатывает взаимодействие с продуктом
    """
    try:
        # Собираем данные взаимодействия
        interaction_data = {}
        if duration_seconds is not None:
            interaction_data['duration_seconds'] = duration_seconds
        if image_index is not None:
            interaction_data['image_index'] = image_index
        if action:
            interaction_data['action'] = action
        if button_text:
            interaction_data['button_text'] = button_text
        
        # Собираем данные сессии
        session_data = {}
        if page_type:
            session_data['page_type'] = page_type
        if location:
            session_data['location'] = location
        if referrer:
            session_data['referrer'] = referrer
        if device_type:
            session_data['device_type'] = device_type
        if url:
            session_data['url'] = url
        if timestamp:
            session_data['timestamp'] = timestamp
        
        if background_tasks:
            background_tasks.add_task(
                ProductRanking.process_product_interaction,
                db,
                product_id,
                interaction_type,
                interaction_data,
                session_data
            )
        else:
            await ProductRanking.process_product_interaction(
                db,
                product_id,
                interaction_type,
                interaction_data,
                session_data
            )
        
        return {"success": True}
        
    except Exception as e:
        print(f"Ошибка при обработке взаимодействия: {str(e)}")
        return {"success": False, "message": f"Ошибка при обработке: {str(e)}"}

@router.post("/batch")
async def process_analytics_batch(
    events: Dict[str, List[Dict[str, Any]]],
    background_tasks: BackgroundTasks = None,
    db: AsyncSession = Depends(get_async_db)
):
    """
    Обрабатывает пакет событий аналитики с клиента
    """
    try:
        # Получаем список событий из тела запроса
        event_list = events.get("events", [])
        
        if not event_list:
            return {"success": False, "message": "Нет событий для обработки"}
        
        # Обрабатываем события в фоновом режиме, если доступно
        if background_tasks:
            background_tasks.add_task(
                ProductRanking.process_analytics_events,
                db,
                event_list
            )
        else:
            # Иначе обрабатываем синхронно
            await ProductRanking.process_analytics_events(db, event_list)
        
        return {"success": True, "message": f"Обработано {len(event_list)} событий"}
        
    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        print(f"Ошибка при обработке аналитики: {error_details}")
        return {"success": False, "message": f"Ошибка при обработке: {str(e)}"}