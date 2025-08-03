from typing import List, Optional, Dict, Any
from sqlalchemy import select, func, desc
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload
from sqlalchemy import select

from app.models.catalog import Catalog
from app.models.product import Product
from app.schemas.catalog import CatalogCreate, CatalogUpdate

class CatalogCRUD:
    async def get_catalogs(
        self,
        db: AsyncSession, 
        skip: int = 0, 
        limit: int = 100,
        category_id: Optional[int] = None
    ) -> List[Catalog]:
        """
        Получить список каталогов с возможностью фильтрации по категории
        """
        stmt = select(Catalog)
        
        if category_id is not None:
            stmt = stmt.where(Catalog.category_id == category_id)
        
        stmt = stmt.offset(skip).limit(limit)
        result = await db.execute(stmt)
        return result.scalars().all()

    async def get_catalog(self, db: AsyncSession, catalog_id: int) -> Optional[Catalog]:
        """
        Получить каталог по ID
        """
        stmt = select(Catalog).where(Catalog.id == catalog_id)
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_catalog_by_name(self, db: AsyncSession, name: str) -> Optional[Catalog]:
        """
        Получить каталог по имени
        """
        stmt = select(Catalog).where(Catalog.name == name)
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    async def create_catalog(self, db: AsyncSession, catalog: CatalogCreate) -> Catalog:
        """
        Создать новый каталог
        """
        db_catalog = Catalog(
            name=catalog.name,
            category_id=catalog.category_id
        )
        db.add(db_catalog)
        await db.commit()
        await db.refresh(db_catalog)
        return db_catalog

    async def update_catalog(self, db: AsyncSession, catalog_id: int, catalog: CatalogUpdate) -> Optional[Catalog]:
        """
        Обновить каталог
        """
        db_catalog = await self.get_catalog(db, catalog_id)
        if not db_catalog:
            return None
        
        # Обновляем данные каталога
        update_data = catalog.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(db_catalog, key, value)
        
        await db.commit()
        await db.refresh(db_catalog)
        return db_catalog

    async def delete_catalog(self, db: AsyncSession, catalog_id: int) -> bool:
        """
        Удалить каталог
        """
        db_catalog = await self.get_catalog(db, catalog_id)
        if not db_catalog:
            return False
        
        await db.delete(db_catalog)
        await db.commit()
        return True
    
   

    async def get_catalogs_list_paginated(
        self,
        db: AsyncSession,
        page: int = 1,
        per_page: int = 20,
        is_active: bool = True,
        sort: str = "name"
    ) -> Dict[str, Any]:
        """
        Получить список каталогов с пагинацией
        """
        try:
            query = select(Catalog)
            
            if is_active:
                query = query.where(Catalog.is_active == True)
            
            count_query = select(func.count()).select_from(query.subquery())
            count_result = await db.execute(count_query)
            total = count_result.scalar() or 0
            
            # Сортировка
            if sort == "name_desc":
                query = query.order_by(desc(Catalog.name))
            elif sort == "newest":
                query = query.order_by(desc(Catalog.created_at))
            elif sort == "random":
                query = query.order_by(func.random())
            else:  # name по умолчанию
                query = query.order_by(Catalog.name)
            
            query = query.offset((page - 1) * per_page).limit(per_page)
            
            result = await db.execute(query)
            catalogs = result.scalars().all()
            
            catalog_list = []
            for catalog in catalogs:
                catalog_list.append({
                    "id": catalog.id,
                    "name": catalog.name,
                    "slug": catalog.slug,
                    "description": catalog.description,
                    "image": catalog.image,
                    "brand_id": catalog.brand_id
                })
            
            return {
                "items": catalog_list,
                "total": total,
                "page": page,
                "per_page": per_page,
                "pages": (total + per_page - 1) // per_page
            }
            
        except Exception as e:
            self.logger.error(f"Ошибка при получении списка каталогов: {str(e)}", exc_info=True)
            raise
    

catalog = CatalogCRUD()