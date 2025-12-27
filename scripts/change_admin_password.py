import sys
import os

# Add parent directory to path so we can import from root
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import SessionLocal
from models import Admin
from auth import get_password_hash

def change_admin_password(username: str, new_password: str):
    """Change the password for an admin user"""
    db = SessionLocal()
    try:
        # Find the admin user
        admin = db.query(Admin).filter(Admin.username == username).first()
        
        if not admin:
            print(f"❌ Error: Admin user '{username}' not found!")
            print(f"Available admins:")
            all_admins = db.query(Admin).all()
            for a in all_admins:
                print(f"  - {a.username}")
            return False
        
        # Hash the new password
        admin.hashed_password = get_password_hash(new_password)
        
        # Save to database
        db.commit()
        
        print(f"✅ Password changed successfully for user: {username}")
        print(f"\nNew credentials:")
        print(f"  Username: {username}")
        print(f"  Password: {new_password}")
        print(f"\nYou can now login at: http://localhost:3000/admin")
        return True
        
    except Exception as e:
        print(f"❌ Error changing password: {e}")
        db.rollback()
        return False
    finally:
        db.close()

def create_new_admin(username: str, password: str, email: str = None):
    """Create a new admin user"""
    db = SessionLocal()
    try:
        # Check if username already exists
        existing = db.query(Admin).filter(Admin.username == username).first()
        if existing:
            print(f"❌ Error: Username '{username}' already exists!")
            return False
        
        # Create new admin
        new_admin = Admin(
            username=username,
            hashed_password=get_password_hash(password),
            email=email,
            is_active=True
        )
        
        db.add(new_admin)
        db.commit()
        
        print(f"✅ New admin created successfully!")
        print(f"\nCredentials:")
        print(f"  Username: {username}")
        print(f"  Password: {password}")
        if email:
            print(f"  Email: {email}")
        return True
        
    except Exception as e:
        print(f"❌ Error creating admin: {e}")
        db.rollback()
        return False
    finally:
        db.close()

def list_admins():
    """List all admin users"""
    db = SessionLocal()
    try:
        admins = db.query(Admin).all()
        if not admins:
            print("No admin users found in database.")
            return
        
        print(f"\n{'='*50}")
        print(f"Admin Users in Database:")
        print(f"{'='*50}")
        for admin in admins:
            status = "✅ Active" if admin.is_active else "❌ Inactive"
            print(f"\nUsername: {admin.username}")
            print(f"Email: {admin.email or 'Not set'}")
            print(f"Status: {status}")
            print(f"Created: {admin.created_at}")
        print(f"{'='*50}\n")
        
    finally:
        db.close()

if __name__ == "__main__":
    print("=" * 50)
    print("Admin Password Management")
    print("=" * 50)
    print()
    
    # Show current admins
    list_admins()
    
    print("\nWhat would you like to do?")
    print("1. Change password for existing admin")
    print("2. Create new admin user")
    print("3. Exit")
    
    choice = input("\nEnter choice (1-3): ").strip()
    
    if choice == "1":
        username = input("\nEnter admin username: ").strip()
        new_password = input("Enter new password: ").strip()
        
        if not username or not new_password:
            print("❌ Username and password cannot be empty!")
            sys.exit(1)
        
        if len(new_password) < 6:
            print("⚠️  Warning: Password is less than 6 characters!")
            confirm = input("Continue anyway? (yes/no): ").strip().lower()
            if confirm != "yes":
                print("Password change cancelled.")
                sys.exit(0)
        
        change_admin_password(username, new_password)
        
    elif choice == "2":
        username = input("\nEnter new admin username: ").strip()
        password = input("Enter password: ").strip()
        email = input("Enter email (optional): ").strip() or None
        
        if not username or not password:
            print("❌ Username and password cannot be empty!")
            sys.exit(1)
        
        if len(password) < 6:
            print("⚠️  Warning: Password should be at least 6 characters!")
            confirm = input("Continue anyway? (yes/no): ").strip().lower()
            if confirm != "yes":
                print("Admin creation cancelled.")
                sys.exit(0)
        
        create_new_admin(username, password, email)
        
    else:
        print("Exiting...")
