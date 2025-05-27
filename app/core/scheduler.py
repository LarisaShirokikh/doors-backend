# app/core/scheduler.py 
from fastapi import FastAPI
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from app.core.database import get_async_db_for_scheduler
from app.crud.product_ranking import ProductRankingService

async def recalculate_all_rankings():
    """
    Задача для регулярного пересчета рейтингов всех товаров
    """
    db = None
    try:
        db = await get_async_db_for_scheduler()
        await ProductRankingService.recalculate_ranking(db)
    except Exception as e:
        print(f"Ошибка при пересчете рейтингов товаров: {str(e)}")
    finally:
        if db:
            await db.close()

async def ensure_ranking_records():
    """
    Задача для создания записей ранжирования для новых товаров
    """
    db = None
    try:
        db = await get_async_db_for_scheduler()
        await ProductRankingService.ensure_ranking_records(db)
    except Exception as e:
        print(f"Ошибка при создании записей ранжирования: {str(e)}")
    finally:
        if db:
            await db.close()

def init_scheduler(app: FastAPI):
    """
    Инициализация планировщика задач
    """
    scheduler = AsyncIOScheduler()
    
    # Пересчитываем рейтинги каждую ночь в 1 час
    scheduler.add_job(
        recalculate_all_rankings,
        CronTrigger(hour=1, minute=0),
        id="recalculate_all_rankings",
        replace_existing=True
    )
    
    # Создаем записи ранжирования для новых товаров каждый час
    scheduler.add_job(
        ensure_ranking_records,
        CronTrigger(minute=5),  # Каждый час в 5 минут
        id="ensure_ranking_records",
        replace_existing=True
    )
    
    scheduler.start()
    app.state.scheduler = scheduler