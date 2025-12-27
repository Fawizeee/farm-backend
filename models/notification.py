from sqlalchemy import Column, Integer, String, DateTime, Text, ForeignKey, Boolean
from sqlalchemy.orm import relationship
from datetime import datetime
from .base import Base

class DeviceToken(Base):
    __tablename__ = "device_tokens"
    
    id = Column(Integer, primary_key=True, index=True)
    device_id = Column(String(255), nullable=False, index=True)
    fcm_token = Column(String(500), nullable=False, unique=True)
    is_admin = Column(Boolean, default=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class Notification(Base):
    __tablename__ = "notifications"
    
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(255), nullable=False)
    message = Column(Text, nullable=False)
    sent_count = Column(Integer, default=0)
    failed_count = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    recipients = relationship("NotificationRecipient", back_populates="notification", cascade="all, delete-orphan")

class NotificationRecipient(Base):
    __tablename__ = "notification_recipients"
    
    id = Column(Integer, primary_key=True, index=True)
    notification_id = Column(Integer, ForeignKey("notifications.id"), nullable=False)
    device_id = Column(String(255), nullable=False, index=True)
    fcm_token_id = Column(Integer, ForeignKey("device_tokens.id"), nullable=True)
    sent_at = Column(DateTime, default=datetime.utcnow)
    clicked_at = Column(DateTime, nullable=True)
    is_clicked = Column(Boolean, default=False)
    
    notification = relationship("Notification", back_populates="recipients")
    device_token = relationship("DeviceToken")
