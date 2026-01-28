from sqlalchemy.orm import Session
from models import DeviceToken, Notification, NotificationRecipient
from datetime import datetime
from typing import Optional
 
class NotificationService:
    @staticmethod
    def register_token(db: Session, token: str, device_id: str, is_admin: bool = False):
        from sqlalchemy.exc import IntegrityError
        
        try:  
            existing_token = db.query(DeviceToken).filter(DeviceToken.fcm_token == token).first()
            if existing_token:
                if existing_token.device_id != device_id:
                    existing_token.device_id = device_id
                if is_admin:
                    existing_token.is_admin = True
                existing_token.updated_at = datetime.utcnow()
                db.commit()
                return {"status": "success", "message": "Token updated"}
            else:
                db_token = DeviceToken(device_id=device_id, fcm_token=token, is_admin=is_admin)
                db.add(db_token)
                db.commit()
                db.refresh(db_token)
                return {"status": "success", "message": "Token registered"}
        except IntegrityError:
            # Handle race condition where another request created the token
            db.rollback()
            # Try to update the existing token instead
            existing_token = db.query(DeviceToken).filter(DeviceToken.fcm_token == token).first()
            if existing_token:
                if existing_token.device_id != device_id:
                    existing_token.device_id = device_id
                if is_admin:
                    existing_token.is_admin = True
                existing_token.updated_at = datetime.utcnow()
                db.commit()
                return {"status": "success", "message": "Token updated (race condition handled)"}
            else:
                # This shouldn't happen, but handle it gracefully
                raise

    @staticmethod
    def unsubscribe_token(db: Session, token: str):
        existing_token = db.query(DeviceToken).filter(DeviceToken.fcm_token == token).first()
        if existing_token:
            # Set fcm_token_id to NULL in related recipients before deleting to avoid FK violation
            db.query(NotificationRecipient).filter(
                NotificationRecipient.fcm_token_id == existing_token.id
            ).update({NotificationRecipient.fcm_token_id: None})
            
            db.delete(existing_token)
            db.commit()
            return True
        return False

    @staticmethod
    def create_notification(db: Session, title: str, message_text: str) -> Notification:
        db_notification = Notification(
            title=title,
            message=message_text,
            sent_count=0,
            failed_count=0
        )
        db.add(db_notification)
        db.flush()
        return db_notification

    @staticmethod
    def send_notification_to_all(db: Session, title: str, message_text: str, device_tokens: list, messaging_instance) -> Notification:
        # Create notification first
        db_notification = Notification(
            title=title,
            message=message_text,
            sent_count=0,
            failed_count=0
        )
        db.add(db_notification)
        db.flush()  # Get the ID before commit
        
        # Store ID to avoid lazy loading issues after potential rollback
        notification_id = db_notification.id
        
        sent_count = 0
        failed_count = 0
        
        from models import NotificationRecipient

        for device_token in device_tokens:
            try:
                from firebase_admin import messaging
                message = messaging_instance.Message(
                    notification=messaging_instance.Notification(
                        title=title,
                        body=message_text,
                    ),
                    data={
                        "notification_id": str(notification_id),
                        "device_id": device_token.device_id,
                        "click_action": "FLUTTER_NOTIFICATION_CLICK"
                    },
                    token=device_token.fcm_token,
                )
                messaging_instance.send(message)
                sent_count += 1
                
                recipient = NotificationRecipient(
                    notification_id=notification_id,
                    device_id=device_token.device_id,
                    fcm_token_id=device_token.id,
                    is_clicked=False
                )
                db.add(recipient)
            except Exception as e:
                print(f"Failed to send notification to token {device_token.id}: {e}")
                failed_count += 1
                if "invalid" in str(e).lower() or "not found" in str(e).lower():
                    # Before deleting device token, set fcm_token_id to NULL in related recipients
                    # to avoid foreign key constraint violation
                    db.query(NotificationRecipient).filter(
                        NotificationRecipient.fcm_token_id == device_token.id
                    ).update({NotificationRecipient.fcm_token_id: None})
                    db.delete(device_token)
        
        # Update counts
        db_notification.sent_count = sent_count
        db_notification.failed_count = failed_count
        
        try:
            db.commit()
            # Re-query to get fresh instance attached to session
            return db.query(Notification).filter(Notification.id == notification_id).first()
        except Exception as e:
            db.rollback()
            print(f"Error committing notification: {e}")
            # After rollback, return None or raise - don't try to access db_notification
            raise

    @staticmethod
    def send_notification_to_admin(db: Session, title: str, message_text: str, redirect_url: str = None, messaging_instance=None) -> Optional[Notification]:
        """Send notification to all admin devices only"""
        if not messaging_instance:
            return None
            
        # Get all admin device tokens
        admin_tokens = db.query(DeviceToken).filter(DeviceToken.is_admin == True).all()
        
        if not admin_tokens:
            print("No admin tokens found")
            return None
        
        # Create notification
        db_notification = Notification(
            title=title,
            message=message_text,
            sent_count=0,
            failed_count=0
        )
        db.add(db_notification)
        db.flush()  # Get ID before commit
        
        # Store ID to avoid lazy loading issues after potential rollback
        notification_id = db_notification.id
        
        sent_count = 0
        failed_count = 0
        
        from models import NotificationRecipient

        for device_token in admin_tokens:
            try:
                from firebase_admin import messaging
                notification_data = {
                    "notification_id": str(notification_id),
                    "device_id": device_token.device_id,
                    "click_action": "FLUTTER_NOTIFICATION_CLICK",
                    "is_admin": "true"
                }
                
                # Add redirect URL if provided
                if redirect_url:
                    notification_data["redirect_url"] = redirect_url
                
                message = messaging_instance.Message(
                    notification=messaging_instance.Notification(
                        title=title,
                        body=message_text,
                    ),
                    data=notification_data,
                    token=device_token.fcm_token,
                )
                messaging_instance.send(message)
                sent_count += 1
                
                recipient = NotificationRecipient(
                    notification_id=notification_id,
                    device_id=device_token.device_id,
                    fcm_token_id=device_token.id,
                    is_clicked=False
                )
                db.add(recipient)
            except Exception as e:
                print(f"Failed to send notification to admin token {device_token.id}: {e}")
                failed_count += 1
                if "invalid" in str(e).lower() or "not found" in str(e).lower():
                    # Before deleting device token, set fcm_token_id to NULL in related recipients
                    # to avoid foreign key constraint violation
                    db.query(NotificationRecipient).filter(
                        NotificationRecipient.fcm_token_id == device_token.id
                    ).update({NotificationRecipient.fcm_token_id: None})
                    db.delete(device_token)
        
        # Update counts
        db_notification.sent_count = sent_count
        db_notification.failed_count = failed_count
        
        try:
            db.commit()
            # Re-query to get fresh instance attached to session
            return db.query(Notification).filter(Notification.id == notification_id).first()
        except Exception as e:
            db.rollback()
            print(f"Error committing admin notification: {e}")
            # After rollback, don't try to access db_notification
            raise

    @staticmethod
    def track_click(db: Session, notification_id: int, device_id: str):
        recipient = db.query(NotificationRecipient).filter(
            NotificationRecipient.notification_id == notification_id,
            NotificationRecipient.device_id == device_id
        ).first()
        
        if recipient and not recipient.is_clicked:
            recipient.is_clicked = True
            recipient.clicked_at = datetime.utcnow()
            db.commit()
            return True
        return False
