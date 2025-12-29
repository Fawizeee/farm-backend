from fastapi import APIRouter, Request, Response
import uuid
from .limiter import limiter

router = APIRouter(prefix="/api", tags=["Device"])


@router.get("/device-id")
@limiter.limit("30/minute")
async def get_or_create_device_id(request: Request, response: Response):
    """Get or create a device ID and set it as a cookie"""
    # Check if device_id cookie already exists
    device_id = request.cookies.get("device_id")
    
    if not device_id:
        # Generate a new device ID
        device_id = str(uuid.uuid4())
    
    # Set cookie with 1 year expiration
    response.set_cookie(
        key="device_id",
        value=device_id,
        max_age=31536000,  # 1 year in seconds
        httponly=False,  # Allow JavaScript access
        samesite="lax",  # CSRF protection
        secure=False  # Set to True in production with HTTPS
    )
    
    return {"device_id": device_id}

