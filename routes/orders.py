from fastapi import APIRouter, Depends, HTTPException, Request, UploadFile, File, Form
from sqlalchemy.orm import Session
from typing import List, Optional
import json
import shutil
import uuid
from pathlib import Path
import os

from database import get_db
from models import Admin, Product, Order
import schemas
from auth import get_current_active_admin
from services import OrderService, NotificationService
from .limiter import limiter

router = APIRouter(prefix="/api/orders", tags=["Orders"])

# Get upload directories from environment or use defaults
IS_SERVERLESS = os.getenv("VERCEL") or os.getenv("VERCEL_ENV") or os.getenv("AWS_LAMBDA_FUNCTION_NAME")
if IS_SERVERLESS:
    UPLOADS_BASE_DIR = Path("/tmp/uploads")
else:
    UPLOADS_BASE_DIR = Path("uploads")

PAYMENT_PROOFS_DIR = UPLOADS_BASE_DIR / "payment_proofs"

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


@router.get("", response_model=List[schemas.OrderResponse])
async def get_orders(
    skip: int = 0,
    limit: int = 100,
    status_filter: str = None,
    date: str = None,  # Format: YYYY-MM-DD
    search: str = None,  # Search by order ID
    db: Session = Depends(get_db),
    current_admin: Admin = Depends(get_current_active_admin)
):
    """Get all orders (Admin only)"""
    return OrderService.get_orders(db, skip, limit, status_filter, date, search)


@router.get("/{order_id}", response_model=schemas.OrderResponse)
async def get_order(
    order_id: int,
    db: Session = Depends(get_db),
    current_admin: Admin = Depends(get_current_active_admin)
):
    """Get a single order by ID (Admin only)"""
    order = OrderService.get_order(db, order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    return order


@router.get("/user/orders", response_model=List[schemas.OrderResponse])
async def get_user_orders(
    request: Request,
    user_id: str = None,
    status_filter: str = None,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """Get orders for the current user (identified by user_id from localStorage or device_id cookie)"""
    # Get user_id from query parameter (from localStorage) or fall back to device_id from cookie
    device_id = user_id or request.cookies.get("device_id")
    
    if not device_id:
        # Return empty list if no user_id or device_id
        return []
    
    # Query orders by device_id (user_id is stored as device_id in the database)
    query = db.query(Order).filter(Order.device_id == device_id)
    
    # Filter by status if provided
    # Support comma-separated statuses for multiple status filtering
    if status_filter:
        statuses = [s.strip() for s in status_filter.split(',')]
        if len(statuses) == 1:
            query = query.filter(Order.status == statuses[0])
        else:
            query = query.filter(Order.status.in_(statuses))
    
    # Order by most recent first
    orders = query.order_by(Order.created_at.desc()).offset(skip).limit(limit).all()
    return orders


@router.post("", response_model=schemas.OrderResponse)
@limiter.limit("10/minute")
async def create_order(
    request: Request,
    customer_name: str = Form(...),
    customer_phone: str = Form(...),
    delivery_address: Optional[str] = Form(None),
    items: str = Form(...),  # JSON string of items array
    payment_method: str = Form("transfer"), # transfer or paystack
    device_id: Optional[str] = Form(None),
    payment_proof: Optional[UploadFile] = File(None),
    db: Session = Depends(get_db)
):
    """Create a new order with file upload support"""
    # Get device_id from form or cookie
    device_id = device_id or request.cookies.get("device_id")
    
    # Parse items JSON string
    try:
        items_list = json.loads(items)
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid items format")
    
    # Handle file upload
    payment_proof_url = None
    if payment_proof:
        # Validate file size (max 10MB)
        MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB in bytes
        
        # Read file content to check size
        file_content = await payment_proof.read()
        file_size = len(file_content)
        
        if file_size > MAX_FILE_SIZE:
            raise HTTPException(
                status_code=400,
                detail=f"File too large. Maximum size is {MAX_FILE_SIZE / (1024 * 1024):.0f}MB"
            )
        
        if file_size == 0:
            raise HTTPException(
                status_code=400,
                detail="File is empty"
            )
        
        # Validate file type
        file_ext = Path(payment_proof.filename).suffix.lower()
        allowed_extensions = {'.jpg', '.jpeg', '.png', '.gif', '.pdf', '.webp'}
        if file_ext not in allowed_extensions:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid file type. Allowed types: {', '.join(allowed_extensions)}"
            )
        
        # Generate unique filename
        unique_filename = f"{uuid.uuid4()}{file_ext}"
        file_path = PAYMENT_PROOFS_DIR / unique_filename
        
        # Save file
        try:
            # Ensure directory exists
            PAYMENT_PROOFS_DIR.mkdir(parents=True, exist_ok=True)
            
            with open(file_path, "wb") as buffer:
                buffer.write(file_content)
            
            # Store relative URL path
            payment_proof_url = f"/uploads/payment_proofs/{unique_filename}"
        except OSError as e:
            raise HTTPException(
                status_code=500,
                detail=f"Error saving file: Storage not available. Please try again later."
            )
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Error saving file: {str(e)}")
    
    # Calculate total amount
    total_amount = 0
    order_items = []
    
    for item in items_list:
        product_id = item.get("product_id")
        quantity = item.get("quantity")
        
        if not product_id or not quantity:
            raise HTTPException(status_code=400, detail="Invalid item format")
        
        # Validate product_id is positive integer
        try:
            product_id = int(product_id)
            if product_id <= 0:
                raise ValueError()
        except (ValueError, TypeError):
            raise HTTPException(
                status_code=400,
                detail=f"Invalid product_id: must be a positive integer"
            )
        
        # Validate quantity is positive integer with maximum limit
        try:
            quantity = int(quantity)
            if quantity <= 0:
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid quantity for product {product_id}: must be greater than 0"
                )
            if quantity > 1000:
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid quantity for product {product_id}: cannot exceed 1000 items per product"
                )
        except (ValueError, TypeError):
            raise HTTPException(
                status_code=400,
                detail=f"Invalid quantity for product {product_id}: must be an integer"
            )
        
        product = db.query(Product).filter(Product.id == product_id).first()
        if not product:
            raise HTTPException(status_code=404, detail=f"Product {product_id} not found")
        if not product.available:
            raise HTTPException(status_code=400, detail=f"Product {product.name} is not available")
        
        # Validate product price is positive
        if product.price <= 0:
            raise HTTPException(
                status_code=400,
                detail=f"Product {product.name} has invalid price"
            )
        
        subtotal = float(product.price) * int(quantity)
        
        # Additional sanity check for subtotal
        if subtotal <= 0:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid subtotal calculated for product {product.name}"
            )
        
        total_amount += subtotal
        
        order_items.append({
            "product_id": product.id,
            "product_name": product.name,
            "product_price": product.price,
            "quantity": quantity,
            "subtotal": subtotal
        })
    
    # Validate total amount sanity
    if total_amount <= 0:
        raise HTTPException(
            status_code=400,
            detail="Order total must be greater than 0"
        )
    
    if total_amount > 10000000:  # 10 million limit to prevent overflow
        raise HTTPException(
            status_code=400,
            detail="Order total exceeds maximum allowed amount"
        )

    
    # Create order
    order_data = {
        "customer_name": customer_name,
        "customer_phone": customer_phone,
        "delivery_address": delivery_address if delivery_address else None,
        "total_amount": total_amount,
        "payment_proof_url": payment_proof_url,
        "device_id": device_id,
        "status": "pending"
    }
    created_order = OrderService.create_order(db, order_data, order_items)
    
    # Store order ID immediately after creation to avoid lazy loading issues
    order_id = created_order.id
    
    # Send notification to admin about new order
    # NOTE: This happens AFTER order commit, so notification failure won't affect order
    # Only notify for transfer payments immediately. Paystack payments notify after success.
    if payment_method == "transfer" and firebase_admin_initialized and messaging:
        try:
            NotificationService.send_notification_to_admin(
                db=db,
                title="New Order Received",
                message_text=f"New order from {customer_name} - ₦{total_amount:,.2f}",
                redirect_url="/admin/orders",
                messaging_instance=messaging
            )
        except Exception as e:
            # Log the error but don't fail the order creation
            # The order was already successfully created and committed
            print(f"Warning: Failed to send admin notification for order {order_id}: {e}")
            # Don't rollback - order is already committed successfully
    
    return created_order


@router.put("/{order_id}", response_model=schemas.OrderResponse)
@limiter.limit("30/minute")
async def update_order(
    request: Request,
    order_id: int,
    order_update: schemas.OrderUpdate,
    db: Session = Depends(get_db),
    current_admin: Admin = Depends(get_current_active_admin)
):
    """Update an order (Admin only)"""
    db_order = OrderService.get_order(db, order_id)
    if not db_order:
        raise HTTPException(status_code=404, detail="Order not found")
    
    if order_update.status:
        return OrderService.update_order_status(db, db_order, order_update.status)
    
    return db_order


@router.delete("/{order_id}")
@limiter.limit("20/minute")
async def delete_order(
    request: Request,
    order_id: int,
    db: Session = Depends(get_db),
    current_admin: Admin = Depends(get_current_active_admin)
):
    """Delete an order (Admin only)"""
    db_order = OrderService.get_order(db, order_id)
    if not db_order:
        raise HTTPException(status_code=404, detail="Order not found")
    
    OrderService.delete_order(db, db_order)
    return {"message": "Order deleted successfully"}

