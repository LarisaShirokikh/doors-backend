from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.sql import desc
from app.models.categories import Category
from app.models.product import Product
from app.models.catalog import Catalog
from app.schemas.category import CategoryBase, CategoryCreate, CategoryUpdate

class CategoriesCRUD:
    async def get_categories(
        self,
        db: AsyncSession, 
        skip: int = 0, 
        limit: int = 100,
        manufacturer_id: Optional[int] = None
    ) -> List[CategoryBase]:
        """
        Получить список категорий с фильтрацией по производителю
        """
        query = select(Category)
        
        if manufacturer_id is not None:
            query = query.where(Category.manufacturer_id == manufacturer_id)
    
        result = await db.execute(query.offset(skip).limit(limit))
        categories = result.scalars().all()
        print("🔥 categories:", categories)
        return [CategoryBase.model_validate(category) for category in categories]

    async def get_category(self, db: AsyncSession, category_id: int) -> Optional[CategoryBase]:
        """
        Получить категорию по ID
        """
        query = select(Category).where(Category.id == category_id)
        result = await db.execute(query)
        category = result.scalar_one_or_none()
        
        if category:
            return CategoryBase.model_validate(category)
        return None

    async def create_category(self, db: AsyncSession, category: CategoryCreate) -> CategoryBase:
        """
        Создать новую категорию
        """
        db_category = Category(**category.model_dump())
        db.add(db_category)
        await db.commit()
        await db.refresh(db_category)
        return CategoryBase.model_validate(db_category)

    async def update_category(self, db: AsyncSession, category_id: int, category: CategoryUpdate) -> Optional[CategoryBase]:
        """
        Обновить категорию
        """
        query = select(Category).where(Category.id == category_id)
        result = await db.execute(query)
        db_category = result.scalar_one_or_none()
        
        if not db_category:
            return None
        
        update_data = category.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(db_category, key, value)
        
        db.add(db_category)
        await db.commit()
        await db.refresh(db_category)
        return CategoryBase.model_validate(db_category)

    async def delete_category(self, db: AsyncSession, category_id: int) -> bool:
        """
        Удалить категорию
        """
        query = select(Category).where(Category.id == category_id)
        result = await db.execute(query)
        db_category = result.scalar_one_or_none()
        
        if not db_category:
            return False
        
        await db.delete(db_category)
        await db.commit()
        return True

    async def get_popular_categories(self, db: AsyncSession, limit: int = 4) -> List[CategoryBase]:
        """
        Получить популярные категории
        """
        # Асинхронная версия запроса для получения популярных категорий
        # Примечание: для сложных запросов с join используйте текстовый SQL или ORM expression language
        query = select(Category, func.count(Product.id).label('product_count'))\
            .join(Catalog, Category.id == Catalog.category_id)\
            .join(Product, Catalog.id == Product.catalog_id)\
            .group_by(Category.id)\
            .order_by(desc('product_count'))\
            .limit(limit)
            
        result = await db.execute(query)
        category_counts = result.all()
        
        # Извлекаем только объекты категорий и преобразуем в Pydantic модели
        return [CategoryBase.model_validate(item[0]) for item in category_counts]
    
    
    
categories = CategoriesCRUD()