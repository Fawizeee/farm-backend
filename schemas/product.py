from pydantic import BaseModel, field_validator
from typing import Optional
from datetime import datetime

class ProductBase(BaseModel):
    name: str
    description: str
    price: float
    unit: str = "kg"
    icon: str
    image_url: Optional[str] = None
    available: bool = True
    is_active: bool = True

    @field_validator('is_active', mode='before')
    @classmethod
    def set_active_default(cls, v):
        if v is None:
            return True
        return v

class ProductCreate(ProductBase):
    pass

class ProductUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    price: Optional[float] = None
    unit: Optional[str] = None
    icon: Optional[str] = None
    image_url: Optional[str] = None
    available: Optional[bool] = None
    is_active: Optional[bool] = None

class ProductResponse(ProductBase):
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
