from typing import List
from fastapi import APIRouter, Depends, HTTPException, Query, Path
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_async_db
from app.crud.manufacturers import manufacturer as manufacturer_crud
from app.schemas.manufacturer import ManufacturerCreate, ManufacturerRead, ManufacturerUpdate

router = APIRouter()

@router.get("/", response_model=List[ManufacturerRead])
async def read_manufacturers(
    db: AsyncSession = Depends(get_async_db),
    skip: int = 0, 
    limit: int = 100
):
    """
    Получить список всех производителей
    """
    return await manufacturer_crud.get_manufacturers(db, skip=skip, limit=limit)

@router.get("/{manufacturer_id}", response_model=ManufacturerRead)
async def read_manufacturer(
    manufacturer_id: int = Path(..., title="ID производителя", gt=0),
    db: AsyncSession = Depends(get_async_db)
):
    """
    Получить производителя по ID
    """
    manufacturer = await manufacturer_crud.get_manufacturer(db, manufacturer_id=manufacturer_id)
    if manufacturer is None:
        raise HTTPException(status_code=404, detail="Производитель не найден")
    return manufacturer

# @router.post("/", response_model=ManufacturerRead, status_code=201)
# def create_manufacturer(
#     manufacturer: ManufacturerCreate, 
#     db: AsyncSession = Depends(get_async_db)
# ):
#     """
#     Создать нового производителя
#     """
#     # Проверка на дубликат имени
#     db_manufacturer = manufacturers_service.get_manufacturer_by_name(db, name=manufacturer.name)
#     if db_manufacturer:
#         raise HTTPException(
#             status_code=400,
#             detail=f"Производитель с именем '{manufacturer.name}' уже существует"
#         )
#     return manufacturers_service.create_manufacturer(db=db, manufacturer=manufacturer)

# @router.put("/{manufacturer_id}", response_model=ManufacturerRead)
# async def update_manufacturer(
#     manufacturer: ManufacturerUpdate,
#     manufacturer_id: int = Path(..., title="ID производителя", gt=0),
#     db: AsyncSession = Depends(get_async_db)
# ):
#     """
#     Обновить производителя
#     """
#     # Проверяем, существует ли производитель с таким ID
#     db_manufacturer = await manufacturers_service.get_manufacturer(db, manufacturer_id=manufacturer_id)
#     if db_manufacturer is None:
#         raise HTTPException(status_code=404, detail="Производитель не найден")
    
#     # Проверяем, не существует ли производитель с таким именем (кроме текущего)
#     if manufacturer.name:
#         existing_manufacturer = await manufacturers_service.get_manufacturer_by_name(db, name=manufacturer.name)
#         if existing_manufacturer and existing_manufacturer.id != manufacturer_id:
#             raise HTTPException(
#                 status_code=400,
#                 detail=f"Производитель с именем '{manufacturer.name}' уже существует"
#             )
    
#     return await manufacturers_service.update_manufacturer(
#         db=db, 
#         manufacturer_id=manufacturer_id, 
#         manufacturer=manufacturer
#     )

# @router.delete("/{manufacturer_id}", response_model=bool)
# async def delete_manufacturer(
#     manufacturer_id: int = Path(..., title="ID производителя", gt=0),
#     db: AsyncSession = Depends(get_async_db)
# ):
#     """
#     Удалить производителя
#     """
#     db_manufacturer = await manufacturers_service.get_manufacturer(db, manufacturer_id=manufacturer_id)
#     if db_manufacturer is None:
#         raise HTTPException(status_code=404, detail="Производитель не найден")
#     return await manufacturers_service.delete_manufacturer(db=db, manufacturer_id=manufacturer_id)