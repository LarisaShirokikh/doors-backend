from typing import List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.content import Tip
from app.schemas.content import TipCreate


class TipCRUD:

    async def get_tips_from_db(self, db: AsyncSession, limit: int = 6) -> List[Tip]:
        """
        Получить список советов из базы данных
        """
        query = select(Tip).limit(limit)
        result = await db.execute(query)
        return result.scalars().all()

    async def create_tip(self, db: AsyncSession, tip: TipCreate) -> Tip:
        """
        Создать новый совет
        """
        db_tip = Tip(**tip.model_dump())
        db.add(db_tip)
        await db.commit()
        await db.refresh(db_tip)
        return db_tip

    async def get_tip_by_id(self, db: AsyncSession, tip_id: int) -> Tip:
        """
        Получить совет по ID
        """
        query = select(Tip).where(Tip.id == tip_id)
        result = await db.execute(query)
        return result.scalar_one_or_none()
    
    async def get_tips(self, db: AsyncSession, limit: int = 6) -> List[dict]:
        """
        Получить и преобразовать список советов в формат для фронтенда
        """
        tips = await self.get_tips_from_db(db, limit)
        
        # Преобразуем в формат, который ожидает фронтенд
        return [
            {
                "id": str(tip.id),
                "title": tip.title,
                "description": tip.description or "",
                "image": tip.image or "",
                "content": tip.content or ""
            }
            for tip in tips
        ]
    
tip = TipCRUD()  # Создаем экземпляр класса