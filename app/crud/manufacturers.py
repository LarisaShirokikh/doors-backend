from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.manufacturer import Manufacturer
from app.schemas.manufacturer import ManufacturerCreate, ManufacturerUpdate

class ManufacturerCRUD:
    async def get_manufacturers(
        self,
        db: AsyncSession, 
        skip: int = 0, 
        limit: int = 100
    ) -> List[Manufacturer]:
        """
        Получить список производителей
        """
        stmt = select(Manufacturer).offset(skip).limit(limit)
        result = await db.execute(stmt)
        return result.scalars().all()

    async def get_manufacturer(self, db: AsyncSession, manufacturer_id: int) -> Optional[Manufacturer]:
        """
        Получить производителя по ID
        """
        stmt = select(Manufacturer).where(Manufacturer.id == manufacturer_id)
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_manufacturer_by_name(self, db: AsyncSession, name: str) -> Optional[Manufacturer]:
        """
        Получить производителя по имени
        """
        stmt = select(Manufacturer).where(Manufacturer.name == name)
        result = await db.execute(stmt)
        return result.scalar_one_or_none()
        
    async def create_manufacturer(self, db: AsyncSession, manufacturer: ManufacturerCreate) -> Manufacturer:
        """
        Создать нового производителя
        """
        db_manufacturer = Manufacturer(**manufacturer.dict())
        db.add(db_manufacturer)
        await db.commit()
        await db.refresh(db_manufacturer)
        return db_manufacturer
        
    async def update_manufacturer(self, db: AsyncSession, manufacturer_id: int, manufacturer: ManufacturerUpdate) -> Optional[Manufacturer]:
        """
        Обновить производителя
        """
        db_manufacturer = await self.get_manufacturer(db, manufacturer_id)
        if not db_manufacturer:
            return None
            
        # Обновляем данные производителя
        update_data = manufacturer.dict(exclude_unset=True)
        for key, value in update_data.items():
            setattr(db_manufacturer, key, value)
            
        await db.commit()
        await db.refresh(db_manufacturer)
        return db_manufacturer
        
    async def delete_manufacturer(self, db: AsyncSession, manufacturer_id: int) -> bool:
        """
        Удалить производителя
        """
        db_manufacturer = await self.get_manufacturer(db, manufacturer_id)
        if not db_manufacturer:
            return False
            
        await db.delete(db_manufacturer)
        await db.commit()
        return True

manufacturer = ManufacturerCRUD()