"""
Migration script to make delivery_address column nullable in orders table
Run this script once to update your database schema
"""
import sys
import os

# Add parent directory to path so we can import from root
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import engine, SessionLocal
from sqlalchemy import text

def migrate_delivery_address_nullable():
    """Make delivery_address column nullable in orders table"""
    
    db = SessionLocal()
    try:
        # Check current column definition
        result = db.execute(text("""
            SELECT sql 
            FROM sqlite_master 
            WHERE type='table' AND name='orders'
        """))
        
        table_sql = result.scalar()
        if not table_sql:
            print("[ERROR] Orders table not found!")
            return False
        
        # Check if column is already nullable (check if NOT NULL constraint exists)
        result = db.execute(text("""
            SELECT COUNT(*) as count 
            FROM pragma_table_info('orders') 
            WHERE name='delivery_address' AND "notnull"=0
        """))
        
        is_nullable = result.scalar() > 0
        
        if is_nullable:
            print("[OK] Column 'delivery_address' is already nullable in orders table")
            return True
        
        print("Making delivery_address column nullable...")
        print("Note: SQLite doesn't support ALTER COLUMN, so we'll recreate the table.")
        
        # Step 1: Create new table with nullable delivery_address
        db.execute(text("""
            CREATE TABLE orders_new (
                id INTEGER PRIMARY KEY,
                customer_name VARCHAR(255) NOT NULL,
                customer_phone VARCHAR(50) NOT NULL,
                delivery_address TEXT,
                total_amount FLOAT NOT NULL,
                payment_proof_url VARCHAR(500),
                device_id VARCHAR(255),
                status VARCHAR(50) DEFAULT 'pending',
                created_at DATETIME,
                updated_at DATETIME
            )
        """))
        
        # Step 2: Copy data from old table to new table
        print("Copying data to new table...")
        db.execute(text("""
            INSERT INTO orders_new 
            (id, customer_name, customer_phone, delivery_address, total_amount, 
             payment_proof_url, device_id, status, created_at, updated_at)
            SELECT 
                id, customer_name, customer_phone, delivery_address, total_amount,
                payment_proof_url, device_id, status, created_at, updated_at
            FROM orders
        """))
        
        # Step 3: Drop old table
        print("Dropping old table...")
        db.execute(text("DROP TABLE orders"))
        
        # Step 4: Rename new table
        print("Renaming new table...")
        db.execute(text("ALTER TABLE orders_new RENAME TO orders"))
        
        # Step 5: Recreate indexes if they exist
        print("Recreating indexes...")
        try:
            # Check if device_id index exists and recreate it
            db.execute(text("""
                CREATE INDEX IF NOT EXISTS ix_orders_device_id 
                ON orders(device_id)
            """))
        except Exception as e:
            print(f"Note: Index creation: {e}")
        
        db.commit()
        print("[OK] Successfully made delivery_address column nullable")
        return True
        
    except Exception as e:
        db.rollback()
        print(f"[ERROR] Error during migration: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        db.close()

if __name__ == "__main__":
    print("=" * 50)
    print("Database Migration: Make delivery_address nullable")
    print("=" * 50)
    
    success = migrate_delivery_address_nullable()
    
    if success:
        print("\n[OK] Migration completed successfully!")
        sys.exit(0)
    else:
        print("\n[ERROR] Migration failed!")
        sys.exit(1)

