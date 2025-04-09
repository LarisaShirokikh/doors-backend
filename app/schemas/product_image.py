from typing import Optional
from pydantic import BaseModel

class ProductImageBase(BaseModel):
    url: str
    alt_text: Optional[str] = None
    is_main: bool = False

class ProductImageCreate(ProductImageBase):
    pass

class ProductImageUpdate(BaseModel):
    url: Optional[str] = None
    alt_text: Optional[str] = None
    is_main: Optional[bool] = None

class ProductImageRead(ProductImageBase):
    id: int
    product_id: int

    class Config:
        from_attributes = True