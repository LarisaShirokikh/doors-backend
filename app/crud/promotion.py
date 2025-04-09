# app/crud/promotion.py
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.promotion import Promotion

class PromotionCRUD:
    async def get_all(self, db: AsyncSession):
        result = await db.execute(select(Promotion))
        return result.scalars().all()

promotion = PromotionCRUD()