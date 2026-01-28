from fastapi import APIRouter
from .device import router as device_router
from .auth import router as auth_router
from .products import router as products_router
from .orders import router as orders_router
from .testimonials import router as testimonials_router
from .contact import router as contact_router
from .dashboard import router as dashboard_router
from .notifications import router as notifications_router
from .health import router as health_router
from .payment import router as payment_router

# Create main API router
api_router = APIRouter()

# Include all route modules
api_router.include_router(device_router, tags=["Device"])
api_router.include_router(auth_router, tags=["Authentication"])
api_router.include_router(products_router, tags=["Products"])
api_router.include_router(orders_router, tags=["Orders"])
api_router.include_router(testimonials_router, tags=["Testimonials"])
api_router.include_router(contact_router, tags=["Contact"])
api_router.include_router(dashboard_router, tags=["Dashboard"])
api_router.include_router(notifications_router, tags=["Notifications"])
api_router.include_router(health_router, tags=["Health"])
api_router.include_router(payment_router, tags=["Payment"])

__all__ = ["api_router"]





