"""
Quick script to create or reset qwerty admin user
"""
from database import SessionLocal
from models import Admin
from auth import get_password_hash

def create_or_reset_qwerty():
    """Create or reset qwerty admin user with password qwerty"""
    db = SessionLocal()
    try:
        # Check if qwerty user exists
        admin = db.query(Admin).filter(Admin.username == "qwerty").first()
        
        if admin:
            # Reset password
            admin.hashed_password = get_password_hash("qwerty")
            admin.is_active = True
            db.commit()
            print("✅ Password reset for user: qwerty")
        else:
            # Create new admin
            new_admin = Admin(
                username="qwerty",
                hashed_password=get_password_hash("qwerty"),
                email=None,
                is_active=True
            )
            db.add(new_admin)
            db.commit()
            print("✅ Created new admin user: qwerty")
        
        print("\nCredentials:")
        print("  Username: qwerty")
        print("  Password: qwerty")
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        db.rollback()
        return False
    finally:
        db.close()

if __name__ == "__main__":
    create_or_reset_qwerty()


