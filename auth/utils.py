from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
import os
import hashlib
import secrets
from dotenv import load_dotenv

from database import get_db
from models import Admin
from schemas import TokenData

load_dotenv()

# JWT Configuration - SECRET_KEY must be set in environment or .env file
SECRET_KEY = os.getenv("JWT_SECRET_KEY")
if not SECRET_KEY or SECRET_KEY == "your-secret-key-here":
    raise ValueError(
        "CRITICAL SECURITY ERROR: JWT_SECRET_KEY must be set in environment variables.\n"
        "This is required to secure authentication tokens.\n"
        "Generate a secure key with: python -c 'import secrets; print(secrets.token_hex(32))'\n"
        "Then add it to your .env file: JWT_SECRET_KEY=<generated_key>"
    )

ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))

# PBKDF2 configuration
PBKDF2_ITERATIONS = 100000  # Number of iterations for PBKDF2
PBKDF2_HASH_ALGORITHM = 'sha256'  # Hash algorithm for PBKDF2
SALT_SIZE = 16  # Size of salt in bytes

security = HTTPBearer(auto_error=False)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify a plain password against a PBKDF2 hashed password.
    Format: salt:hash (both hex encoded)
    """
    try:
        # Split the stored hash into salt and hash components
        salt, hash_value = hashed_password.split(':')
        salt = bytes.fromhex(salt)
        hash_value = bytes.fromhex(hash_value)
        
        # Hash the provided password with the same salt
        new_hash = hashlib.pbkdf2_hmac(
            PBKDF2_HASH_ALGORITHM,
            plain_password.encode('utf-8'),
            salt,
            PBKDF2_ITERATIONS
        )
        
        # Use constant-time comparison to prevent timing attacks
        return secrets.compare_digest(new_hash, hash_value)
    except (ValueError, AttributeError):
        # Invalid format or missing components
        return False

def get_password_hash(password: str) -> str:
    """
    Hash a password using PBKDF2.
    Returns a string in the format: salt:hash (both hex encoded)
    """
    # Generate a random salt
    salt = secrets.token_bytes(SALT_SIZE)
    
    # Hash the password with PBKDF2
    hash_value = hashlib.pbkdf2_hmac(
        PBKDF2_HASH_ALGORITHM,
        password.encode('utf-8'),
        salt,
        PBKDF2_ITERATIONS
    )
    
    # Return salt:hash as hex strings
    return f"{salt.hex()}:{hash_value.hex()}"

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def authenticate_admin(db: Session, username: str, password: str):
    admin = db.query(Admin).filter(Admin.username == username).first()
    if not admin:
        return False
    if not verify_password(password, admin.hashed_password):
        return False
    return admin

async def get_current_admin(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: Session = Depends(get_db)
):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authenticated. Please provide a valid token.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    try:
        token = credentials.credentials
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
        token_data = TokenData(username=username)
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid or expired token. Please login again.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    admin = db.query(Admin).filter(Admin.username == token_data.username).first()
    if admin is None:
        raise credentials_exception
    return admin

async def get_current_active_admin(
    current_admin: Admin = Depends(get_current_admin)
):
    if not current_admin.is_active:
        raise HTTPException(status_code=400, detail="Inactive admin")
    return current_admin
