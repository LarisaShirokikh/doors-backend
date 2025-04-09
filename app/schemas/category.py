from typing import Optional
from pydantic import BaseModel

class CategoryBase(BaseModel):
    name: str
    manufacturer_id: int
    image_url: Optional[str] = None

class CategoryCreate(CategoryBase):
    pass

class CategoryUpdate(BaseModel):
    name: Optional[str] = None
    manufacturer_id: Optional[int] = None

class CategoryRead(CategoryBase):
    id: int
    image_url: Optional[str] = None

    class Config:
        from_attributes = True