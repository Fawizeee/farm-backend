from fastapi import APIRouter, Depends, HTTPException, status, Form, Request
from sqlalchemy.orm import Session
from datetime import timedelta
import os

from database import get_db
from models import Admin
import schemas
from auth import (
    authenticate_admin,
    create_access_token,
    get_current_active_admin,
    get_password_hash,
    ACCESS_TOKEN_EXPIRE_MINUTES
)
from .limiter import limiter

router = APIRouter(prefix="/api/admin", tags=["Authentication"])


@router.post("/login", response_model=schemas.Token)
@limiter.limit("5/minute")
async def login(request: Request, admin_login: schemas.AdminLogin, db: Session = Depends(get_db)):
    """Admin login endpoint - Rate limited to prevent brute force attacks"""
    admin = authenticate_admin(db, admin_login.username, admin_login.password)
    if not admin:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": admin.username}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}


@router.get("/me", response_model=schemas.AdminResponse)
async def read_admin_me(current_admin: Admin = Depends(get_current_active_admin)):
    """Get current admin user info"""
    return current_admin


@router.post("/setup-qwerty")
@limiter.limit("3/minute")
async def setup_qwerty_admin(
    request: Request,
    setup_secret: str = Form(...),
    db: Session = Depends(get_db)
):
    """
    One-time setup endpoint to create qwerty admin user
    Protected by a secret key
    """
    # Check secret key from environment variable
    expected_secret = os.getenv("SETUP_SECRET")
    
    if not expected_secret:
        raise HTTPException(
            status_code=503,
            detail="Setup secret not configured"
        )
    
    if setup_secret != expected_secret:
        raise HTTPException(
            status_code=401,
            detail="Invalid setup secret"
        )
    
    try:
        # Password for qwerty admin
        # get_password_hash handles truncation automatically
        password = "qwerty"
        
        # Check if qwerty user exists
        admin = db.query(Admin).filter(Admin.username == "qwerty").first()
        
        if admin:
            # Reset password
            admin.hashed_password = get_password_hash(password)
            admin.is_active = True
            db.commit()
            return {
                "success": True,
                "message": "Password reset for user: qwerty",
                "action": "reset"
            }
        else:
            # Create new admin
            new_admin = Admin(
                username="qwerty",
                hashed_password=get_password_hash(password),
                email=None,
                is_active=True
            )
            db.add(new_admin)
            db.commit()
            return {
                "success": True,
                "message": "Created new admin user: qwerty",
                "action": "created"
            }
    
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Error creating admin: {str(e)}"
        )

