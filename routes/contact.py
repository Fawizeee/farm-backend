from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from typing import List

from database import get_db
from models import Admin, ContactMessage
import schemas
from auth import get_current_active_admin
from .limiter import limiter

router = APIRouter(prefix="/api", tags=["Contact"])


@router.get("/contact-messages", response_model=List[schemas.ContactMessageResponse])
async def get_contact_messages(
    skip: int = 0,
    limit: int = 100,
    unread_only: bool = False,
    db: Session = Depends(get_db),
    current_admin: Admin = Depends(get_current_active_admin)
):
    """Get all contact messages (Admin only)"""
    query = db.query(ContactMessage)
    if unread_only:
        query = query.filter(ContactMessage.is_read == False)
    messages = query.order_by(ContactMessage.created_at.desc()).offset(skip).limit(limit).all()
    return messages


@router.post("/contact", response_model=schemas.ContactMessageResponse)
@limiter.limit("5/minute")
async def create_contact_message(
    request: Request,
    message: schemas.ContactMessageCreate,
    db: Session = Depends(get_db)
):
    """Submit a contact form message"""
    db_message = ContactMessage(**message.dict())
    db.add(db_message)
    db.commit()
    db.refresh(db_message)
    return db_message


@router.put("/contact-messages/{message_id}/read")
async def mark_message_read(
    message_id: int,
    db: Session = Depends(get_db),
    current_admin: Admin = Depends(get_current_active_admin)
):
    """Mark a contact message as read (Admin only)"""
    db_message = db.query(ContactMessage).filter(ContactMessage.id == message_id).first()
    if not db_message:
        raise HTTPException(status_code=404, detail="Message not found")
    
    db_message.is_read = True
    db.commit()
    return {"message": "Message marked as read"}

