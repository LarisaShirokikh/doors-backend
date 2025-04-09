from typing import Optional
from pydantic import BaseModel

class ManufacturerBase(BaseModel):
    name: str
    description: Optional[str] = None

class ManufacturerCreate(ManufacturerBase):
    pass

class ManufacturerUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None

class ManufacturerRead(ManufacturerBase):
    id: int

    class Config:
        from_attributes = True