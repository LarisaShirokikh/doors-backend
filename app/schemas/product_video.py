# app/schemas/product_video.py
from pydantic import BaseModel
from typing import Optional

class ProductVideoBase(BaseModel):
    title: str
    description: str
    price: int
    product_id: int

class ProductVideoCreate(ProductVideoBase):
    pass

class ProductVideoRead(ProductVideoBase):
    id: int
    video_url: str

    class Config:
        from_attributes = True