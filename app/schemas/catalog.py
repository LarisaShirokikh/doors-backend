from typing import Optional
from pydantic import BaseModel

class CatalogBase(BaseModel):
    name: str
    category_id: int

class CatalogCreate(CatalogBase):
    pass

class CatalogUpdate(BaseModel):
    name: Optional[str] = None
    category_id: Optional[int] = None

class CatalogRead(CatalogBase):
    id: int

    class Config:
        from_attributes = True