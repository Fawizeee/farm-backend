from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

class DeviceTokenRegister(BaseModel):
    token: str
    deviceId: str

class NotificationSend(BaseModel):
    title: str
    message: str

class NotificationResponse(BaseModel):
    success: bool
    message: str
    sent_count: int
    failed_count: int
    notification_id: Optional[int] = None

class NotificationAnalyticsResponse(BaseModel):
    id: int
    title: str
    message: str
    sent_count: int
    failed_count: int
    clicked_count: int
    created_at: datetime
    
    class Config:
        from_attributes = True

class NotificationClickTrack(BaseModel):
    notification_id: int
    device_id: str

class NotificationAnalyticsDetail(BaseModel):
    notification: NotificationAnalyticsResponse
    total_recipients: int
    clicked_count: int
    click_rate: float
    recipients: List[dict]
