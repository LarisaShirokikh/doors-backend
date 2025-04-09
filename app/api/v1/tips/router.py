# app/api/v1/tips/router.py
from typing import List
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from app.crud.tip import tip as tip_crud
from app.core.database import get_async_db
from app.schemas.tip import TipRead

router = APIRouter()

@router.get("/", response_model=List[dict])
async def read_tips(
    limit: int = Query(6, ge=1, le=20),
    db: AsyncSession = Depends(get_async_db)
):

    return await tip_crud.get_tips(db, limit=limit)