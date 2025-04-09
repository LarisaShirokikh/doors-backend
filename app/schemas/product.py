from typing import List, Dict, Any, Optional
from pydantic import BaseModel
from app.schemas.product_image import ProductImageRead, ProductImageCreate

class ProductBase(BaseModel):
    name: str
    description: Optional[str] = None
    price: float
    in_stock: bool = True
    catalog_name: str 
    characteristics: Optional[Dict[str, Any]] = None

class ProductCreate(ProductBase):
    images: List[ProductImageCreate] = []

class ProductUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    price: Optional[float] = None
    in_stock: Optional[bool] = None
    catalog_name: Optional[str] = None 
    characteristics: Optional[Dict[str, Any]] = None
    images: Optional[List[ProductImageCreate]] = None

class ProductImageRead(BaseModel):
    id: int
    url: str
    is_main: bool = False
    alt_text: Optional[str] = None
    
    class Config:
        from_attributes = True

class ProductRead(BaseModel):
    id: int
    name: str
    description: Optional[str] = None
    price: float
    in_stock: bool = True
    catalog_id: int
    characteristics: Optional[dict] = None
    images: List[ProductImageRead] = []
    
    class Config:
        from_attributes = True