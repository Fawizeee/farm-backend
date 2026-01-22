from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from database import get_db
from models import Admin, Testimonial
import schemas
from auth import get_current_active_admin

router = APIRouter(prefix="/api/testimonials", tags=["Testimonials"])


@router.get("", response_model=List[schemas.TestimonialResponse])
async def get_testimonials(
    skip: int = 0,
    limit: int = 100,
    active_only: bool = True,
    db: Session = Depends(get_db)
):
    """Get all testimonials"""
    query = db.query(Testimonial)
    if active_only:
        query = query.filter(Testimonial.is_active == True)
    testimonials = query.offset(skip).limit(limit).all()
    return testimonials


@router.post("", response_model=schemas.TestimonialResponse)
async def create_testimonial(
    testimonial: schemas.TestimonialCreate,
    db: Session = Depends(get_db),
    current_admin: Admin = Depends(get_current_active_admin)
):
    """Create a new testimonial (Admin only)"""
    db_testimonial = Testimonial(**testimonial.dict())
    db.add(db_testimonial)
    db.commit()
    db.refresh(db_testimonial)
    return db_testimonial


@router.put("/{testimonial_id}", response_model=schemas.TestimonialResponse)
async def update_testimonial(
    testimonial_id: int,
    testimonial: schemas.TestimonialUpdate,
    db: Session = Depends(get_db),
    current_admin: Admin = Depends(get_current_active_admin)
):
    """Update a testimonial (Admin only)"""
    db_testimonial = db.query(Testimonial).filter(Testimonial.id == testimonial_id).first()
    if not db_testimonial:
        raise HTTPException(status_code=404, detail="Testimonial not found")
    
    update_data = testimonial.dict(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_testimonial, key, value)
    
    db.commit()
    db.refresh(db_testimonial)
    return db_testimonial


@router.delete("/{testimonial_id}")
async def delete_testimonial(
    testimonial_id: int,
    db: Session = Depends(get_db),
    current_admin: Admin = Depends(get_current_active_admin)
):
    """Delete a testimonial (Admin only)"""
    db_testimonial = db.query(Testimonial).filter(Testimonial.id == testimonial_id).first()
    if not db_testimonial:
        raise HTTPException(status_code=404, detail="Testimonial not found")
    
    db.delete(db_testimonial)
    db.commit()
    return {"message": "Testimonial deleted successfully"}





