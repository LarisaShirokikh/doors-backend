# app/api/v1/analytics/router.py
from fastapi import APIRouter, Depends, BackgroundTasks, Body
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Dict, Any
from app.core.database import get_async_db
from app.crud.product_ranking import ProductRanking

router = APIRouter()

@router.post("/batch")
async def process_analytics_batch(
    events: Dict[str, List[Dict[str, Any]]] = Body(...),
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

@router.post("/product-view")
async def track_product_view(
    data: Dict[str, Any] = Body(...),
    background_tasks: BackgroundTasks = None,
    db: AsyncSession = Depends(get_async_db)
):
    """
    Обрабатывает просмотр продукта
    """
    try:
        product_id = data.get("product_id")
        session_data = data.get("session_data", {})
        
        if not product_id:
            return {"success": False, "message": "Не указан product_id"}
        
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

@router.post("/product-interaction")
async def track_product_interaction(
    data: Dict[str, Any] = Body(...),
    background_tasks: BackgroundTasks = None,
    db: AsyncSession = Depends(get_async_db)
):
    """
    Обрабатывает взаимодействие с продуктом
    """
    try:
        product_id = data.get("product_id")
        interaction_type = data.get("interaction_type")
        interaction_data = data.get("interaction_data", {})
        session_data = data.get("session_data", {})
        
        if not product_id or not interaction_type:
            return {"success": False, "message": "Не указаны обязательные параметры"}
        
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