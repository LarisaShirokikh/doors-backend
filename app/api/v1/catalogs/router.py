from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Path
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_async_db
from app.crud.catalogs import catalog as catalog_crud
from app.schemas.catalog import CatalogCreate, CatalogRead, CatalogUpdate

router = APIRouter()

@router.get("/", response_model=List[CatalogRead])
async def read_catalogs(
    db: AsyncSession = Depends(get_async_db),
    skip: int = 0,
    limit: int = 100,
    category_id: Optional[int] = None
):
    """
    Получить список каталогов с возможностью фильтрации по категории
    """
    return await catalog_crud.get_catalogs(
        db, 
        skip=skip, 
        limit=limit,
        category_id=category_id
    )

@router.get("/{catalog_id}", response_model=CatalogRead)
async def read_catalog(
    catalog_id: int = Path(..., title="ID каталога", gt=0),
    db: AsyncSession = Depends(get_async_db)
):
    """
    Получить каталог по ID
    """
    catalog = await catalog_crud.get_catalog(db, catalog_id=catalog_id)
    if catalog is None:
        raise HTTPException(status_code=404, detail="Каталог не найден")
    return catalog

# @router.post("/", response_model=CatalogRead, status_code=201)
# def create_catalog(
#     catalog: CatalogCreate, 
#     db: AsyncSession = Depends(get_async_db)
# ):
#     """
#     Создать новый каталог
#     """
#     # Проверка на дубликат имени
#     db_catalog = catalogs_service.get_catalog_by_name(db, name=catalog.name)
#     if db_catalog:
#         raise HTTPException(
#             status_code=400,
#             detail=f"Каталог с именем '{catalog.name}' уже существует"
#         )
#     return catalogs_service.create_catalog(db=db, catalog=catalog)

# @router.put("/{catalog_id}", response_model=CatalogRead)
# def update_catalog(
#     catalog: CatalogUpdate,
#     catalog_id: int = Path(..., title="ID каталога", gt=0),
#     db: AsyncSession = Depends(get_async_db)
# ):
#     """
#     Обновить каталог
#     """
#     # Проверяем, существует ли каталог с таким ID
#     db_catalog = catalogs_service.get_catalog(db, catalog_id=catalog_id)
#     if db_catalog is None:
#         raise HTTPException(status_code=404, detail="Каталог не найден")
    
#     # Проверяем, не существует ли каталог с таким именем (кроме текущего)
#     if catalog.name:
#         existing_catalog = catalogs_service.get_catalog_by_name(db, name=catalog.name)
#         if existing_catalog and existing_catalog.id != catalog_id:
#             raise HTTPException(
#                 status_code=400,
#                 detail=f"Каталог с именем '{catalog.name}' уже существует"
#             )
    
#     return catalogs_service.update_catalog(db=db, catalog_id=catalog_id, catalog=catalog)

# @router.delete("/{catalog_id}", response_model=bool)
# def delete_catalog(
#     catalog_id: int = Path(..., title="ID каталога", gt=0),
#     db: AsyncSession = Depends(get_async_db)
# ):
#     """
#     Удалить каталог
#     """
#     db_catalog = await catalogs_service.get_catalog(db, catalog_id=catalog_id)
#     if db_catalog is None:
#         raise HTTPException(status_code=404, detail="Каталог не найден")
#     return catalogs_service.delete_catalog(db=db, catalog_id=catalog_id)