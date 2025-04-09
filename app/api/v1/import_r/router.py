from typing import List
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_async_db
from app.schemas.import_log import ImportLogRead
from app.crud.import_log import import_log as import_log_crud

router = APIRouter()

@router.post("/products-excel/", status_code=202)
async def import_products_from_excel(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_async_db),
):
    """
    Импорт товаров из Excel-файла
    """
    if file.content_type not in [
        "application/vnd.ms-excel",
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    ]:
        raise HTTPException(
            status_code=400, 
            detail="Неверный формат файла. Пожалуйста, загрузите файл Excel (.xls или .xlsx)"
        )
    
    contents = await file.read()
    import_result = import_log_crud.import_products_from_excel(db, contents, file.filename)
    
    return import_result

@router.get("/logs/", response_model=List[ImportLogRead])
async def read_import_logs(
    skip: int = 0, 
    limit: int = 100, 
    db: AsyncSession = Depends(get_async_db),
):
    """
    Получить список логов импорта
    """
    return await import_log_crud.get_import_logs(db, skip=skip, limit=limit)

@router.get("/logs/{import_log_id}", response_model=ImportLogRead)
async def read_import_log(import_log_id: int, db: AsyncSession = Depends(get_async_db),):
    """
    Получить детальную информацию о логе импорта по ID
    """
    import_log = await import_log_crud.get_import_log(db, import_log_id=import_log_id)
    if import_log is None:
        raise HTTPException(status_code=404, detail="Лог импорта не найден")
    return import_log