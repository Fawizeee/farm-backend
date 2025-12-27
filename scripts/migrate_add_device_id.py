"""
Migration script to add device_id column to orders table
Run this script once to update your database schema
"""
from database import engine, SessionLocal
from sqlalchemy import text
import sys

def migrate_add_device_id():
    """Add device_id column to orders table if it doesn't exist"""
    
    db = SessionLocal()
    try:
        # Check if column already exists
        result = db.execute(text("""
            SELECT COUNT(*) as count 
            FROM pragma_table_info('orders') 
            WHERE name='device_id'
        """))
        
        column_exists = result.scalar() > 0
        
        if column_exists:
            print("✓ Column 'device_id' already exists in orders table")
            return True
        
        # Add the device_id column
        print("Adding device_id column to orders table...")
        db.execute(text("""
            ALTER TABLE orders 
            ADD COLUMN device_id VARCHAR(255)
        """))
        
        # Create index on device_id for better query performance
        print("Creating index on device_id...")
        try:
            db.execute(text("""
                CREATE INDEX IF NOT EXISTS ix_orders_device_id 
                ON orders(device_id)
            """))
        except Exception as e:
            # Index might already exist, that's okay
            print(f"Note: Index creation: {e}")
        
        db.commit()
        print("✓ Successfully added device_id column to orders table")
        print("✓ Index created on device_id column")
        return True
        
    except Exception as e:
        db.rollback()
        print(f"✗ Error during migration: {e}")
        return False
    finally:
        db.close()

if __name__ == "__main__":
    print("=" * 50)
    print("Database Migration: Add device_id to orders")
    print("=" * 50)
    
    success = migrate_add_device_id()
    
    if success:
        print("\n✓ Migration completed successfully!")
        sys.exit(0)
    else:
        print("\n✗ Migration failed!")
        sys.exit(1)

