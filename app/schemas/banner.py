# app/schemas/banner.py
from pydantic import BaseModel
from typing import Optional

class BannerRead(BaseModel):
    id: int
    title: str
    image: str
    url: Optional[str] = None

    class Config:
        from_attributes = True