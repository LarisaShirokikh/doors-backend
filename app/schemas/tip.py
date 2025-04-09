# app/schemas/tip.py
from typing import Optional
from pydantic import BaseModel

class TipBase(BaseModel):
    title: str
    description: Optional[str] = None
    image: Optional[str] = None
    content: Optional[str] = None

class TipCreate(TipBase):
    pass

class TipUpdate(TipBase):
    title: Optional[str] = None

class TipRead(TipBase):
    id: int

    class Config:
        from_attributes = True