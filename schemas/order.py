from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

class OrderItemCreate(BaseModel):
    product_id: int
    quantity: int

class OrderItemResponse(BaseModel):
    id: int
    product_id: int
    product_name: str
    product_price: float
    quantity: int
    subtotal: float

    class Config:
        from_attributes = True

class OrderCreate(BaseModel):
    customer_name: str
    customer_phone: str
    delivery_address: Optional[str] = None
    items: List[OrderItemCreate]
    payment_proof_url: Optional[str] = None
    device_id: Optional[str] = None

class OrderUpdate(BaseModel):
    status: Optional[str] = None

class OrderResponse(BaseModel):
    id: int
    customer_name: str
    customer_phone: str
    delivery_address: Optional[str] = None
    total_amount: float
    payment_proof_url: Optional[str]
    device_id: Optional[str]
    status: str
    created_at: datetime
    updated_at: datetime
    order_items: List[OrderItemResponse]

    class Config:
        from_attributes = True
