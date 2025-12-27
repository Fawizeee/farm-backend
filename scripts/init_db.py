import sys
import os

# Add parent directory to path so we can import from root
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import Base, engine, SessionLocal
from models import Product, Admin, Testimonial
from auth import get_password_hash
from sqlalchemy import func
from dotenv import load_dotenv

load_dotenv()

def init_database():
    """Initialize database with tables and seed data"""
    
    # Create all tables
    Base.metadata.create_all(bind=engine)
    
    db = SessionLocal()
    try:
        # Check if admin already exists
        admin_exists = db.query(Admin).filter(Admin.username == "admin").first()
        if not admin_exists:
            admin_username = os.getenv("ADMIN_USERNAME", "admin")
            admin_password = os.getenv("ADMIN_PASSWORD", "admin123")
            
            admin = Admin(
                username=admin_username,
                hashed_password=get_password_hash(admin_password),
                email="admin@mufufarm.com",
                is_active=True
            )
            db.add(admin)
            print(f"Admin user created with username: {admin_username}")
        
        # Check if products exist
        products_count = db.query(func.count(Product.id)).scalar()
        if products_count == 0:
            initial_products = [
                Product(
                    name="Fresh Catfish (Small)",
                    description="Whole cleaned catfish, 0.5-1kg each",
                    price=3000,
                    unit="kg",
                    icon="fish-small",
                    available=True
                ),
                Product(
                    name="Fresh Catfish (Medium)",
                    description="Whole cleaned catfish, 1-2kg each",
                    price=3500,
                    unit="kg",
                    icon="fish-medium",
                    available=True
                ),
                Product(
                    name="Fresh Catfish (Large)",
                    description="Whole cleaned catfish, 2-3kg each",
                    price=4000,
                    unit="kg",
                    icon="fish-large",
                    available=True
                ),
                Product(
                    name="Catfish Fillet",
                    description="Boneless premium cuts, ready to cook",
                    price=5000,
                    unit="kg",
                    icon="fillet",
                    available=True
                ),
                Product(
                    name="Smoked Catfish",
                    description="Traditionally smoked for rich flavor",
                    price=4500,
                    unit="kg",
                    icon="smoked",
                    available=True
                ),
                Product(
                    name="Live Catfish",
                    description="Fresh from the pond, sold alive",
                    price=2800,
                    unit="kg",
                    icon="live",
                    available=True
                )
            ]
            db.add_all(initial_products)
            print(f"Added {len(initial_products)} products")
        
        # Check if testimonials exist
        testimonials_count = db.query(func.count(Testimonial.id)).scalar()
        if testimonials_count == 0:
            initial_testimonials = [
                Testimonial(
                    name="Adebayo Johnson",
                    role="Restaurant Owner",
                    text="The catfish from Mufu Farm is consistently the best. My customers always compliment the freshness and taste. Highly recommended!",
                    rating=5,
                    is_active=True
                ),
                Testimonial(
                    name="Sarah Williams",
                    role="Home Cook",
                    text="Convenient delivery and amazing quality. The smoked catfish adds such a rich flavor to my soups. I'm a loyal customer now.",
                    rating=5,
                    is_active=True
                ),
                Testimonial(
                    name="Chinedu Eze",
                    role="Hotel Manager",
                    text="Reliable supply and professional service. We've been sourcing our fish from Mufu Farm for over a year and haven't had a single issue.",
                    rating=5,
                    is_active=True
                ),
                Testimonial(
                    name="Grace Olayinka",
                    role="Event Caterer",
                    text="Bulk orders are handled so efficiently. The fish are always clean and well-packaged. Mufu Farm makes my job easier.",
                    rating=4,
                    is_active=True
                ),
                Testimonial(
                    name="Emmanuel Peters",
                    role="Customer",
                    text="I love the live catfish option. It doesn't get fresher than that! Delivery is always prompt too.",
                    rating=5,
                    is_active=True
                )
            ]
            db.add_all(initial_testimonials)
            print(f"Added {len(initial_testimonials)} testimonials")
        
        db.commit()
        print("Database initialized successfully!")
        
    except Exception as e:
        print(f"Error initializing database: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    init_database()
