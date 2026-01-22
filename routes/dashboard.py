from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from database import get_db
from models import Admin
import schemas
from auth import get_current_active_admin
from services import OrderService

router = APIRouter(prefix="/api/admin", tags=["Dashboard"])


@router.get("/dashboard-stats", response_model=schemas.DashboardStats)
async def get_dashboard_stats(
    db: Session = Depends(get_db),
    current_admin: Admin = Depends(get_current_active_admin)
):
    """Get dashboard statistics (Admin only)"""
    return OrderService.get_dashboard_stats(db)





