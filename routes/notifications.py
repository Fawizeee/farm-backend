from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List
import os

from database import get_db
from models import Admin, DeviceToken, Notification, NotificationRecipient
import schemas
from auth import get_current_active_admin
from services import NotificationService
from .limiter import limiter

router = APIRouter(prefix="/api", tags=["Notifications"])

# Import Firebase messaging if available
firebase_admin_initialized = False
messaging = None
try:
    import firebase_admin
    from firebase_admin import messaging as fcm_messaging
    firebase_admin_initialized = True
    messaging = fcm_messaging
except ImportError:
    pass


@router.post("/notifications/register")
@limiter.limit("10/minute")
async def register_notification_token(
    request: Request,
    token_data: schemas.DeviceTokenRegister,
    db: Session = Depends(get_db)
):
    """Register or update FCM token for a device"""
    return NotificationService.register_token(db, token_data.token, token_data.deviceId)


@router.delete("/notifications/unsubscribe")
@limiter.limit("10/minute")
async def unsubscribe_notification_token(
    request: Request,
    token: str,
    db: Session = Depends(get_db)
):
    """Unsubscribe a device from notifications"""
    success = NotificationService.unsubscribe_token(db, token)
    if success:
        return {"success": True, "message": "Successfully unsubscribed"}
    else:
        # We return success even if not found to be idempotent, or specific message if preferred.
        # User asked for "unsubscribe", implying they want it gone.
        # If it's already gone, that's a success state for the client.
        return {"success": True, "message": "Token not found or already unsubscribed"}


@router.post("/admin/notifications/register")
@limiter.limit("10/minute")
async def register_admin_notification_token(
    request: Request,
    token_data: schemas.DeviceTokenRegister,
    db: Session = Depends(get_db),
    current_admin: Admin = Depends(get_current_active_admin)
):
    """Register or update FCM token for an admin device (Admin only)"""
    return NotificationService.register_token(db, token_data.token, token_data.deviceId, is_admin=True)


@router.post("/admin/send-notification", response_model=schemas.NotificationResponse)
@limiter.limit("10/minute")
async def send_notification_to_all(
    request: Request,
    notification: schemas.NotificationSend,
    db: Session = Depends(get_db),
    current_admin: Admin = Depends(get_current_active_admin)
):
    """Send notification to all registered customers (Admin only)"""
    # Get all registered FCM tokens
    device_tokens = db.query(DeviceToken).all()
    
    if not firebase_admin_initialized:
        raise HTTPException(
            status_code=503,
            detail="Firebase Admin SDK not initialized. Please configure FIREBASE_CREDENTIALS_PATH in .env file"
        )
    
    if not device_tokens:
        return {
            "success": True,
            "message": "No registered devices found",
            "sent_count": 0,
            "failed_count": 0,
            "notification_id": None
        }
    
    # Use Service to send notification
    db_notification = NotificationService.send_notification_to_all(
        db, notification.title, notification.message, device_tokens, messaging
    )
    
    return {
        "success": True,
        "message": f"Notification sent to {db_notification.sent_count} device(s)",
        "sent_count": db_notification.sent_count,
        "failed_count": db_notification.failed_count,
        "notification_id": db_notification.id
    }


@router.post("/notifications/track-click")
@limiter.limit("30/minute")
async def track_notification_click(
    request: Request,
    click_data: schemas.NotificationClickTrack,
    db: Session = Depends(get_db)
):
    """Track when a user clicks on a notification"""
    success = NotificationService.track_click(db, click_data.notification_id, click_data.device_id)
    if success:
        return {"success": True, "message": "Click tracked"}
    else:
        # Check if it was already tracked or recipient not found
        # For simplicity, returning failure if not successful in service
        return {"success": False, "message": "Recipient not found or already tracked"}


@router.get("/admin/notifications/analytics", response_model=List[schemas.NotificationAnalyticsResponse])
async def get_notification_analytics(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_admin: Admin = Depends(get_current_active_admin)
):
    """Get analytics for all notifications (Admin only)"""
    notifications = db.query(Notification).order_by(Notification.created_at.desc()).offset(skip).limit(limit).all()
    
    # Calculate clicked_count for each notification
    result = []
    for notif in notifications:
        clicked_count = db.query(func.count(NotificationRecipient.id)).filter(
            NotificationRecipient.notification_id == notif.id,
            NotificationRecipient.is_clicked == True
        ).scalar()
        
        result.append({
            "id": notif.id,
            "title": notif.title,
            "message": notif.message,
            "sent_count": notif.sent_count,
            "failed_count": notif.failed_count,
            "clicked_count": clicked_count,
            "created_at": notif.created_at
        })
    
    return result


@router.get("/admin/notifications/{notification_id}/analytics")
async def get_notification_detail_analytics(
    notification_id: int,
    db: Session = Depends(get_db),
    current_admin: Admin = Depends(get_current_active_admin)
):
    """Get detailed analytics for a specific notification (Admin only)"""
    notification = db.query(Notification).filter(Notification.id == notification_id).first()
    if not notification:
        raise HTTPException(status_code=404, detail="Notification not found")
    
    # Get all recipients
    recipients = db.query(NotificationRecipient).filter(
        NotificationRecipient.notification_id == notification_id
    ).all()
    
    clicked_count = sum(1 for r in recipients if r.is_clicked)
    total_recipients = len(recipients)
    click_rate = (clicked_count / total_recipients * 100) if total_recipients > 0 else 0
    
    # Format recipient data
    recipient_data = []
    for recipient in recipients:
        recipient_data.append({
            "device_id": recipient.device_id,
            "sent_at": recipient.sent_at.isoformat() if recipient.sent_at else None,
            "clicked_at": recipient.clicked_at.isoformat() if recipient.clicked_at else None,
            "is_clicked": recipient.is_clicked
        })
    
    return {
        "notification": {
            "id": notification.id,
            "title": notification.title,
            "message": notification.message,
            "sent_count": notification.sent_count,
            "failed_count": notification.failed_count,
            "clicked_count": clicked_count,
            "created_at": notification.created_at
        },
        "total_recipients": total_recipients,
        "clicked_count": clicked_count,
        "click_rate": round(click_rate, 2),
        "recipients": recipient_data
    }

