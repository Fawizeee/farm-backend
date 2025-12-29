from fastapi import APIRouter, Request
from .limiter import limiter

router = APIRouter(tags=["Health"])


@router.get("/")
@limiter.limit("100/minute")
async def root(request: Request):
    """Health check endpoint"""
    return {
        "status": "online",
        "message": "Mufu Farm API is running",
        "version": "1.0.0"
    }


@router.get("/health")
@limiter.limit("100/minute")
async def health_check(request: Request):
    """Health check endpoint"""
    return {"status": "healthy"}

