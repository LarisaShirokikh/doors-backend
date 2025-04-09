# app/schemas/promotion.py
from pydantic import BaseModel
from typing import Optional

class PromotionRead(BaseModel):
    id: int
    title: str
    description: Optional[str] = None
    image: str
    url: Optional[str] = None

    class Config:
        from_attributes = True