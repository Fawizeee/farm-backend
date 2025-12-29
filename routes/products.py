from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Request
from sqlalchemy.orm import Session
from typing import List, Optional
import uuid
from pathlib import Path
import os

from database import get_db
from models import Admin
import schemas
from auth import get_current_active_admin
from services import ProductService
from .limiter import limiter

router = APIRouter(prefix="/api/products", tags=["Products"])

# Get upload directories from environment or use defaults
IS_SERVERLESS = os.getenv("VERCEL") or os.getenv("VERCEL_ENV") or os.getenv("AWS_LAMBDA_FUNCTION_NAME")
if IS_SERVERLESS:
    UPLOADS_BASE_DIR = Path("/tmp/uploads")
else:
    UPLOADS_BASE_DIR = Path("uploads")

PRODUCT_IMAGES_DIR = UPLOADS_BASE_DIR / "product_images"


@router.get("", response_model=List[schemas.ProductResponse])
async def get_products(
    skip: int = 0,
    limit: int = 100,
    available_only: bool = False,
    db: Session = Depends(get_db)
):
    """Get all products"""
    return ProductService.get_products(db, skip, limit, available_only)


@router.get("/{product_id}", response_model=schemas.ProductResponse)
async def get_product(product_id: int, db: Session = Depends(get_db)):
    """Get a single product by ID"""
    product = ProductService.get_product(db, product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    return product


@router.post("", response_model=schemas.ProductResponse)
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


@router.put("/{product_id}", response_model=schemas.ProductResponse)
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


@router.delete("/{product_id}")
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

