from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
import os
import uuid
from pathlib import Path
from dotenv import load_dotenv

from database import engine
from models import Base
from routes import api_router

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
    allow_origins=["https://mufucatfishfarm.vercel.app",http://10.241.122.254:3000] ,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include all routes
app.include_router(api_router)

# ==================== ROUTES MOVED TO routes/ FOLDER ====================
# All routes have been moved to separate files in the routes/ folder:
# - routes/device.py - Device ID routes
# - routes/auth.py - Authentication routes
# - routes/products.py - Product routes
# - routes/orders.py - Order routes
# - routes/testimonials.py - Testimonial routes
# - routes/contact.py - Contact routes
# - routes/dashboard.py - Dashboard stats
# - routes/notifications.py - Notification routes
# - routes/health.py - Health check routes

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
