# app/crud/banner.py
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.content import Banner

class BannerCRUD:
    async def get_all(self, db: AsyncSession):
        result = await db.execute(select(Banner))
        return result.scalars().all()
    
    

banner = BannerCRUD()