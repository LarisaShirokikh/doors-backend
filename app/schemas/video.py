from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime

class VideoBase(BaseModel):
    title: str
    description: Optional[str] = None
    url: str
    thumbnail_url: Optional[str] = None
    duration: Optional[float] = None
    is_active: bool = True
    is_featured: bool = False

class VideoCreate(VideoBase):
    product_id: Optional[int] = None
    auto_detect_product: bool = True

class VideoUpdate(BaseModel):
    id: int
    uuid: str
    title: str
    description: Optional[str] = None
    url: str
    thumbnail_url: Optional[str] = None
    duration: Optional[float] = None
    
    # Поля для продукта
    product_slug: Optional[str] = None
    product_id: Optional[int] = None
    
    created_at: datetime
    updated_at: Optional[datetime] = None
    is_active: bool = True
    is_featured: bool = False
    auto_detected: Optional[bool] = False

    class Config:
        orm_mode = True

class VideoInDB(VideoBase):
    id: int
    uuid: str
    product_id: Optional[int] = None
    product_slug: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
    auto_detected: Optional[bool] = False

    class Config:
        orm_mode = True

class Video(VideoInDB):
    pass

class VideoWithProduct(Video):
    product: Optional[Dict[str, Any]] = None