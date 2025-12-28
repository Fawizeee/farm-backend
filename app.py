from fastapi import FastAPI, Depends, HTTPException, status, UploadFile, File, Request, Response, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import timedelta, datetime
from typing import List, Optional
import os
import uuid
import json
import shutil
from pathlib import Path
from dotenv import load_dotenv

from database import get_db, engine
from models import (
    Base, Product, Order, OrderItem, Admin, Testimonial, 
    ContactMessage, FarmInfo, DeviceToken, Notification, 
    NotificationRecipient
)
import schemas
from auth import (
    authenticate_admin,
    create_access_token,
    get_current_active_admin,
    get_password_hash,
    ACCESS_TOKEN_EXPIRE_MINUTES
)
from services import ProductService, OrderService, NotificationService

load_dotenv()

# Initialize Firebase Admin SDK (optional - only if configured)
firebase_admin_initialized = False
messaging = None
try:
    import firebase_admin
    from firebase_admin import credentials
    from firebase_admin import messaging as fcm_messaging
    import base64
    
    # First, try to get credentials from environment variable (for Vercel/production)
    firebase_cred_json = os.getenv("FIREBASE_CREDENTIALS_JSON")
    firebase_cred_base64 = os.getenv("FIREBASE_CREDENTIALS_BASE64")
    
    cred = None
    temp_cred_file = None
    
    if firebase_cred_base64:
        # Decode base64 encoded credentials
        try:
            firebase_cred_json = base64.b64decode(firebase_cred_base64).decode('utf-8')
        except Exception as e:
            print(f"Error decoding base64 Firebase credentials: {e}")
    
    if firebase_cred_json:
        # Create temporary file from environment variable
        try:
            import tempfile
            temp_cred_file = tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False)
            temp_cred_file.write(firebase_cred_json)
            temp_cred_file.close()
            cred = credentials.Certificate(temp_cred_file.name)
            print("Firebase credentials loaded from environment variable")
        except Exception as e:
            print(f"Error creating Firebase credentials file from env var: {e}")
    else:
        # Fall back to file path method (for local development)
        firebase_cred_path = os.getenv("FIREBASE_CREDENTIALS_PATH")
        if firebase_cred_path and os.path.exists(firebase_cred_path):
            cred = credentials.Certificate(firebase_cred_path)
            print("Firebase credentials loaded from file path")
    
    if cred:
        firebase_admin.initialize_app(cred)
        messaging = fcm_messaging
        firebase_admin_initialized = True
        print("Firebase Admin SDK initialized successfully")
    else:
        print("Firebase credentials not found. Notification sending will be disabled.")
        print("To enable notifications, set FIREBASE_CREDENTIALS_JSON or FIREBASE_CREDENTIALS_BASE64 in environment variables")
        print("Or set FIREBASE_CREDENTIALS_PATH in .env file for local development")
except ImportError:
    print("firebase-admin not installed. Install it with: pip install firebase-admin")
except Exception as e:
    print(f"Error initializing Firebase Admin SDK: {e}") 

# Detect serverless environment
def is_serverless_environment():
    """Check if running in a serverless environment"""
    # Check for Vercel
    if os.getenv("VERCEL") or os.getenv("VERCEL_ENV"):
        return True
    # Check for AWS Lambda
    if os.getenv("AWS_LAMBDA_FUNCTION_NAME"):
        return True
    # Check if /tmp is writable (common in serverless)
    try:
        test_path = Path("/tmp")
        if test_path.exists() and os.access(test_path, os.W_OK):
            # Try to write a test file
            test_file = test_path / f".test_{uuid.uuid4()}"
            try:
                test_file.touch()
                test_file.unlink()
                return True
            except:
                pass
    except:
        pass
    return False

# Determine uploads directory based on environment
IS_SERVERLESS = is_serverless_environment()
if IS_SERVERLESS:
    UPLOADS_BASE_DIR = Path("/tmp/uploads")
else:
    UPLOADS_BASE_DIR = Path("uploads")

# Create uploads directories if they don't exist
PAYMENT_PROOFS_DIR = UPLOADS_BASE_DIR / "payment_proofs"
PRODUCT_IMAGES_DIR = UPLOADS_BASE_DIR / "product_images"

# Try to create directories, but don't fail if we can't (e.g., in read-only filesystem)
try:
    PAYMENT_PROOFS_DIR.mkdir(parents=True, exist_ok=True)
    PRODUCT_IMAGES_DIR.mkdir(parents=True, exist_ok=True)
except (OSError, PermissionError) as e:
    print(f"Warning: Could not create upload directories: {e}")
    print("File uploads may not work properly in this environment")
    # In serverless, /tmp should work, so this is unexpected
    if IS_SERVERLESS:
        print("Note: Running in serverless environment, using /tmp for uploads")

# Create tables
Base.metadata.create_all(bind=engine)

app = FastAPI(title="Mufu Farm API", version="1.0.0")

# Initialize rate limiter
limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Set default rate limit for all endpoints (can be overridden per endpoint)
default_limit = os.getenv("RATE_LIMIT_DEFAULT", "100/minute")

# Mount static files for serving uploaded images (only in non-serverless environments)
# In serverless, static files should be served via CDN or object storage
if not IS_SERVERLESS:
    try:
        app.mount("/uploads", StaticFiles(directory=str(UPLOADS_BASE_DIR)), name="uploads")
    except Exception as e:
        print(f"Warning: Could not mount static files directory: {e}")
else:
    print("Note: Static file serving disabled in serverless environment")
    print("Consider using a CDN or object storage (S3, Cloudinary, etc.) for file serving")

# CORS Configuration
origins = os.getenv("CORS_ORIGINS", "http://localhost:3000,http://10.241.122.254:3000").split(",")
# Strip whitespace from origins
origins = [origin.strip() for origin in origins]

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000,http://10.241.122.254:3000,https://farm-frontend-iota.vercel.app"] ,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ==================== DEVICE ID ROUTES ====================

@app.get("/api/device-id")
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

# ==================== AUTHENTICATION ROUTES ====================

@app.post("/api/admin/login", response_model=schemas.Token)
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

@app.get("/api/admin/me", response_model=schemas.AdminResponse)
async def read_admin_me(current_admin: Admin = Depends(get_current_active_admin)):
    """Get current admin user info"""
    return current_admin

# ==================== PRODUCT ROUTES ====================

@app.get("/api/products", response_model=List[schemas.ProductResponse])
async def get_products(
    skip: int = 0,
    limit: int = 100,
    available_only: bool = False,
    db: Session = Depends(get_db)
):
    """Get all products"""
    return ProductService.get_products(db, skip, limit, available_only)

@app.get("/api/products/{product_id}", response_model=schemas.ProductResponse)
async def get_product(product_id: int, db: Session = Depends(get_db)):
    """Get a single product by ID"""
    product = ProductService.get_product(db, product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    return product

@app.post("/api/products", response_model=schemas.ProductResponse)
@limiter.limit("20/minute")
async def create_product(
    request: Request,
    name: str = Form(...),
    description: str = Form(...),
    price: float = Form(...),
    unit: str = Form("kg"),
    icon: str = Form("🐟"),
    available: str = Form("true"),
    image: Optional[UploadFile] = File(None),
    db: Session = Depends(get_db),
    current_admin: Admin = Depends(get_current_active_admin)
):
    """Create a new product with image upload (Admin only)"""
    # Handle image upload
    image_url = None
    if image and image.filename:
        # Validate file type
        file_ext = Path(image.filename).suffix.lower()
        allowed_extensions = {'.jpg', '.jpeg', '.png', '.gif', '.webp'}
        if file_ext not in allowed_extensions:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid file type. Allowed types: {', '.join(allowed_extensions)}"
            )
        
        # Generate unique filename
        unique_filename = f"{uuid.uuid4()}{file_ext}"
        file_path = PRODUCT_IMAGES_DIR / unique_filename
        
        # Save file
        try:
            # Read file content
            contents = await image.read()
            with open(file_path, "wb") as buffer:
                buffer.write(contents)
            
            # Store relative URL path
            image_url = f"/uploads/product_images/{unique_filename}"
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Error saving image: {str(e)}")
    
    # Convert available string to boolean
    available_bool = available.lower() in ('true', '1', 'yes', 'on')
    
    # Create product
    product_data = {
        "name": name,
        "description": description,
        "price": price,
        "unit": unit,
        "icon": icon,
        "image_url": image_url,
        "available": available_bool
    }
    return ProductService.create_product(db, product_data)

@app.put("/api/products/{product_id}", response_model=schemas.ProductResponse)
@limiter.limit("20/minute")
async def update_product(
    request: Request,
    product_id: int,
    name: Optional[str] = Form(None),
    description: Optional[str] = Form(None),
    price: Optional[float] = Form(None),
    unit: Optional[str] = Form(None),
    icon: Optional[str] = Form(None),
    available: Optional[str] = Form(None),
    image: Optional[UploadFile] = File(None),
    db: Session = Depends(get_db),
    current_admin: Admin = Depends(get_current_active_admin)
):
    """Update a product with optional image upload (Admin only)"""
    db_product = ProductService.get_product(db, product_id)
    if not db_product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    # Collect update data
    update_data = {}
    if name is not None: update_data["name"] = name
    if description is not None: update_data["description"] = description
    if price is not None: update_data["price"] = price
    if unit is not None: update_data["unit"] = unit
    if icon is not None: update_data["icon"] = icon
    if available is not None:
        update_data["available"] = available.lower() in ('true', '1', 'yes', 'on')
    
    # Handle image upload if provided
    if image and image.filename:
        # Validate file type
        file_ext = Path(image.filename).suffix.lower()
        allowed_extensions = {'.jpg', '.jpeg', '.png', '.gif', '.webp'}
        if file_ext not in allowed_extensions:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid file type. Allowed types: {', '.join(allowed_extensions)}"
            )
        
        # Delete old image if it exists
        if db_product.image_url:
            # Remove /uploads/ prefix if present, then construct path using UPLOADS_BASE_DIR
            relative_path = db_product.image_url.replace("/uploads/", "").lstrip("/")
            old_image_path = UPLOADS_BASE_DIR / relative_path
            if old_image_path.exists():
                try:
                    old_image_path.unlink()
                except Exception as e:
                    print(f"Warning: Could not delete old image: {e}")
        
        # Generate unique filename
        unique_filename = f"{uuid.uuid4()}{file_ext}"
        file_path = PRODUCT_IMAGES_DIR / unique_filename
        
        # Save new file
        try:
            # Read file content
            contents = await image.read()
            with open(file_path, "wb") as buffer:
                buffer.write(contents)
            
            # Store relative URL path
            update_data["image_url"] = f"/uploads/product_images/{unique_filename}"
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Error saving image: {str(e)}")
    
    return ProductService.update_product(db, db_product, update_data)

@app.delete("/api/products/{product_id}")
@limiter.limit("20/minute")
async def delete_product(
    request: Request,
    product_id: int,
    db: Session = Depends(get_db),
    current_admin: Admin = Depends(get_current_active_admin)
):
    """Delete a product (Admin only)"""
    db_product = ProductService.get_product(db, product_id)
    if not db_product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    ProductService.delete_product(db, db_product)
    return {"message": "Product deleted successfully"}

# ==================== ORDER ROUTES ====================

@app.get("/api/orders", response_model=List[schemas.OrderResponse])
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

@app.get("/api/orders/{order_id}", response_model=schemas.OrderResponse)
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

@app.get("/api/user/orders", response_model=List[schemas.OrderResponse])
async def get_user_orders(
    request: Request,
    status_filter: str = None,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """Get orders for the current user (identified by device_id cookie)"""
    # Get device_id from cookie
    device_id = request.cookies.get("device_id")
    
    if not device_id:
        # Return empty list if no device_id
        return []
    
    # Query orders by device_id
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

@app.post("/api/orders", response_model=schemas.OrderResponse)
@limiter.limit("10/minute")
async def create_order(
    request: Request,
    customer_name: str = Form(...),
    customer_phone: str = Form(...),
    delivery_address: Optional[str] = Form(None),
    items: str = Form(...),  # JSON string of items array
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
            with open(file_path, "wb") as buffer:
                shutil.copyfileobj(payment_proof.file, buffer)
            
            # Store relative URL path
            payment_proof_url = f"/uploads/payment_proofs/{unique_filename}"
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
        
        product = db.query(Product).filter(Product.id == product_id).first()
        if not product:
            raise HTTPException(status_code=404, detail=f"Product {product_id} not found")
        if not product.available:
            raise HTTPException(status_code=400, detail=f"Product {product.name} is not available")
        
        subtotal = product.price * quantity
        total_amount += subtotal
        
        order_items.append({
            "product_id": product.id,
            "product_name": product.name,
            "product_price": product.price,
            "quantity": quantity,
            "subtotal": subtotal
        })
    
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
    
    # Send notification to admin about new order
    if firebase_admin_initialized and messaging:
        try:
            NotificationService.send_notification_to_admin(
                db=db,
                title="New Order Received",
                message_text=f"New order from {customer_name} - ₦{total_amount:,.2f}",
                redirect_url="/admin/orders",
                messaging_instance=messaging
            )
        except Exception as e:
            print(f"Failed to send admin notification for order {created_order.id}: {e}")
            # Don't fail the order creation if notification fails
    
    return created_order

@app.put("/api/orders/{order_id}", response_model=schemas.OrderResponse)
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

@app.delete("/api/orders/{order_id}")
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

# ==================== TESTIMONIAL ROUTES ====================

@app.get("/api/testimonials", response_model=List[schemas.TestimonialResponse])
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

@app.post("/api/testimonials", response_model=schemas.TestimonialResponse)
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

@app.put("/api/testimonials/{testimonial_id}", response_model=schemas.TestimonialResponse)
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

@app.delete("/api/testimonials/{testimonial_id}")
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

# ==================== CONTACT ROUTES ====================

@app.get("/api/contact-messages", response_model=List[schemas.ContactMessageResponse])
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

@app.post("/api/contact", response_model=schemas.ContactMessageResponse)
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

@app.put("/api/contact-messages/{message_id}/read")
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

# ==================== DASHBOARD STATS ====================

@app.get("/api/admin/dashboard-stats", response_model=schemas.DashboardStats)
async def get_dashboard_stats(
    db: Session = Depends(get_db),
    current_admin: Admin = Depends(get_current_active_admin)
):
    """Get dashboard statistics (Admin only)"""
    return OrderService.get_dashboard_stats(db)

# ==================== NOTIFICATION ROUTES ====================

@app.post("/api/notifications/register")
@limiter.limit("10/minute")
async def register_notification_token(
    request: Request,
    token_data: schemas.DeviceTokenRegister,
    db: Session = Depends(get_db)
):
    """Register or update FCM token for a device"""
    return NotificationService.register_token(db, token_data.token, token_data.deviceId)

@app.post("/api/admin/notifications/register")
@limiter.limit("10/minute")
async def register_admin_notification_token(
    request: Request,
    token_data: schemas.DeviceTokenRegister,
    db: Session = Depends(get_db),
    current_admin: Admin = Depends(get_current_active_admin)
):
    """Register or update FCM token for an admin device (Admin only)"""
    return NotificationService.register_token(db, token_data.token, token_data.deviceId, is_admin=True)

@app.post("/api/admin/send-notification", response_model=schemas.NotificationResponse)
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

@app.post("/api/notifications/track-click")
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

@app.get("/api/admin/notifications/analytics", response_model=List[schemas.NotificationAnalyticsResponse])
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

@app.get("/api/admin/notifications/{notification_id}/analytics")
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

# ==================== HEALTH CHECK ====================

@app.get("/")
@limiter.limit("100/minute")
async def root(request: Request):
    """Health check endpoint"""
    return {
        "status": "online",
        "message": "Mufu Farm API is running",
        "version": "1.0.0"
    }

@app.get("/health")
@limiter.limit("100/minute")
async def health_check(request: Request):
    """Health check endpoint"""
    return {"status": "healthy"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
