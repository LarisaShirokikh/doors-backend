# app/crud/product_ranking.py
import logging
from datetime import datetime
from typing import Any, Dict, List
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.product_ranking import ProductRanking as ProductRankingModel

logger = logging.getLogger(__name__)

class ProductRanking:
    """Сервис для управления ранжированием товаров"""
    
    @staticmethod
    async def process_analytics_events(db: AsyncSession, events: List[Dict[str, Any]]) -> None:
        """
        Обрабатывает список событий аналитики с клиента
        """
        try:
            # Группируем события по типу и продукту
            events_by_product = {}
            
            for event in events:
                product_id = event.get("product_id")
                event_type = event.get("type")
                
                if not product_id or not event_type:
                    continue
                    
                if product_id not in events_by_product:
                    events_by_product[product_id] = {
                        "product_views": 0,
                        "product_detail_views": 0,
                        "view_duration": 0,
                        "interactions": [],
                    }
                
                # Обрабатываем разные типы событий
                if event_type == "product_card_view":
                    events_by_product[product_id]["product_views"] += 1
                    
                elif event_type == "product_detail_view":
                    events_by_product[product_id]["product_detail_views"] += 1
                    
                elif event_type == "product_view_duration":
                    duration = event.get("duration_seconds", 0)
                    events_by_product[product_id]["view_duration"] += duration
                    
                elif event_type == "product_interaction":
                    interaction_type = event.get("interaction_type")
                    if interaction_type:
                        events_by_product[product_id]["interactions"].append({
                            "type": interaction_type,
                            "data": event.get("interaction_data", {})
                        })
            
            # Обновляем рейтинги продуктов на основе собранных данных
            for product_id, data in events_by_product.items():
                await ProductRanking._update_product_ranking_from_analytics(
                    db, 
                    product_id, 
                    data["product_views"],
                    data["product_detail_views"],
                    data["view_duration"],
                    data["interactions"]
                )
            
            await db.commit()
            logger.info(f"Обработаны события аналитики для {len(events_by_product)} продуктов")
            
        except Exception as e:
            logger.error(f"Ошибка при обработке событий аналитики: {str(e)}")
            await db.rollback()

    @staticmethod
    async def process_product_view(
        db: AsyncSession, 
        product_id: Any, 
        session_data: Dict[str, Any] = None
    ) -> None:
        """
        Обрабатывает просмотр продукта
        """
        try:
            # Находим запись рейтинга
            ranking_query = select(ProductRankingModel).where(ProductRankingModel.product_id == product_id)
            result = await db.execute(ranking_query)
            ranking = result.scalar_one_or_none()
            
            if not ranking:
                # Создаем новую запись, если не существует
                ranking = ProductRankingModel(product_id=product_id)
                db.add(ranking)
                await db.flush()
            
            # Обновляем счетчик показов
            ranking.impressions_count = (ranking.impressions_count or 0) + 1
            
            # Немного увеличиваем рейтинг
            ranking_score_increase = 0.1  # Небольшое увеличение за просмотр
            ranking.ranking_score = min(100, (ranking.ranking_score or 0) + ranking_score_increase)
            
            ranking.updated_at = datetime.utcnow()
            await db.commit()
            
        except Exception as e:
            logger.error(f"Ошибка при обработке просмотра продукта {product_id}: {str(e)}")
            await db.rollback()

    @staticmethod
    async def process_product_interaction(
        db: AsyncSession,
        product_id: Any,
        interaction_type: str,
        interaction_data: Dict[str, Any] = None,
        session_data: Dict[str, Any] = None
    ) -> None:
        """
        Обрабатывает взаимодействие с продуктом
        """
        try:
            # Находим запись рейтинга
            ranking_query = select(ProductRankingModel).where(ProductRankingModel.product_id == product_id)
            result = await db.execute(ranking_query)
            ranking = result.scalar_one_or_none()
            
            if not ranking:
                # Создаем новую запись, если не существует
                ranking = ProductRankingModel(product_id=product_id)
                db.add(ranking)
                await db.flush()
            
            # Определяем вес взаимодействия
            interaction_weights = {
                "view_image": 0.2,          # Просмотр изображения
                "gallery_browse": 0.3,      # Просмотр галереи
                "share": 1.0,               # Шаринг товара
                "favorite": 0.8,            # Добавление в избранное
                "unfavorite": -0.5,         # Удаление из избранного
                "contact_request": 1.5,     # Запрос контакта
                "view_video": 0.5,          # Просмотр видео
                "card_click": 0.4,          # Клик по карточке
                "request_info": 1.2,        # Запрос информации
                "default": 0.2              # Значение по умолчанию
            }
            
            # Получаем вес для данного типа взаимодействия
            weight = interaction_weights.get(interaction_type, interaction_weights["default"])
            
            # Учитываем дополнительные факторы из данных взаимодействия
            if interaction_type == "view_video" and interaction_data:
                # Для просмотра видео учитываем длительность
                if interaction_data.get("action") == "complete":
                    weight = 1.0  # Полный просмотр видео дает больше баллов
                elif interaction_data.get("duration"):
                    # Увеличиваем вес в зависимости от длительности просмотра
                    duration = interaction_data.get("duration", 0)
                    if duration > 30:  # Если смотрел более 30 секунд
                        weight += min(duration / 60, 1.0)  # Максимум +1.0 за длительный просмотр
            
            # Обновляем рейтинг
            ranking.ranking_score = min(100, (ranking.ranking_score or 0) + weight)
            ranking.updated_at = datetime.utcnow()
            
            await db.commit()
            logger.info(f"Обработано взаимодействие '{interaction_type}' для продукта {product_id}")
            
        except Exception as e:
            logger.error(f"Ошибка при обработке взаимодействия '{interaction_type}' для продукта {product_id}: {str(e)}")
            await db.rollback()

    @staticmethod
    async def _update_product_ranking_from_analytics(
        db: AsyncSession,
        product_id: Any,
        product_views: int,
        product_detail_views: int,
        view_duration: int,
        interactions: List[Dict[str, Any]]
    ) -> None:
        """
        Обновляет рейтинг продукта на основе собранных аналитических данных
        """
        try:
            # Находим запись рейтинга
            ranking_query = select(ProductRankingModel).where(ProductRankingModel.product_id == product_id)
            result = await db.execute(ranking_query)
            ranking = result.scalar_one_or_none()
            
            if not ranking:
                # Создаем новую запись, если не существует
                ranking = ProductRankingModel(product_id=product_id)
                db.add(ranking)
                await db.flush()
            
            # Базовый прирост рейтинга в зависимости от просмотров
            views_score = product_views * 0.1 + product_detail_views * 0.3
            
            # Бонус за время просмотра (максимум 3.0 за более 5 минут просмотра)
            duration_score = min(view_duration / 100, 3.0)
            
            # Бонус за взаимодействия
            interaction_score = 0
            interaction_weights = {
                "view_image": 0.2,
                "gallery_browse": 0.3,
                "share": 1.0,
                "favorite": 0.8,
                "unfavorite": -0.5,
                "contact_request": 1.5,
                "view_video": 0.5,
                "card_click": 0.4,
                "request_info": 1.2,
                "default": 0.2
            }
            
            for interaction in interactions:
                interaction_type = interaction.get("type")
                weight = interaction_weights.get(interaction_type, interaction_weights["default"])
                interaction_score += weight
            
            # Общий прирост рейтинга
            total_score_increase = views_score + duration_score + interaction_score
            
            # Ограничиваем прирост для предотвращения слишком резких изменений
            total_score_increase = min(total_score_increase, 5.0)
            
            # Обновляем счетчик показов и рейтинг
            ranking.impressions_count = (ranking.impressions_count or 0) + product_views
            ranking.ranking_score = min(100, (ranking.ranking_score or 0) + total_score_increase)
            ranking.updated_at = datetime.utcnow()
            
        except Exception as e:
            logger.error(f"Ошибка при обновлении рейтинга для продукта {product_id}: {str(e)}")
            # Не делаем rollback, так как эта функция вызывается из process_analytics_events