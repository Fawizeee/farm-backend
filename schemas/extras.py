from pydantic import BaseModel, Field, EmailStr
from typing import Optional
from datetime import datetime

class TestimonialBase(BaseModel):
    name: str
    role: str
    text: str
    rating: int = Field(ge=1, le=5)

class TestimonialCreate(TestimonialBase):
    pass

class TestimonialUpdate(BaseModel):
    name: Optional[str] = None
    role: Optional[str] = None
    text: Optional[str] = None
    rating: Optional[int] = Field(default=None, ge=1, le=5)
    is_active: Optional[bool] = None

class TestimonialResponse(TestimonialBase):
    id: int
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True

class ContactMessageCreate(BaseModel):
    name: str
    email: EmailStr
    phone: Optional[str] = None
    subject: str
    message: str

class ContactMessageResponse(BaseModel):
    id: int
    name: str
    email: str
    phone: Optional[str]
    subject: str
    message: str
    is_read: bool
    created_at: datetime

    class Config:
        from_attributes = True

class FarmInfoUpdate(BaseModel):
    key: str
    value: str

class FarmInfoResponse(BaseModel):
    id: int
    key: str
    value: str
    updated_at: datetime

    class Config:
        from_attributes = True

class DashboardStats(BaseModel):
    total_orders: int
    pending_orders: int
    completed_orders: int
    total_revenue: float
    total_products: int
    active_products: int
