"""
Migration script to add image_url column to products table
"""
from database import engine, SessionLocal
from sqlalchemy import text, inspect
import sys

def column_exists(table_name, column_name):
    """Check if a column exists in a table"""
    inspector = inspect(engine)
    columns = [col['name'] for col in inspector.get_columns(table_name)]
    return column_name in columns

def migrate_add_image_url():
    """Add image_url column to products table if it doesn't exist"""
    try:
        # Check if column already exists
        if column_exists('products', 'image_url'):
            print("✓ Column 'image_url' already exists in products table")
            return
        
        print("Adding 'image_url' column to products table...")
        
        # SQLite doesn't support adding columns with ALTER TABLE directly
        # We need to use a workaround: create new table, copy data, drop old, rename new
        with engine.connect() as conn:
            # Start transaction
            trans = conn.begin()
            try:
                # Create new table with image_url column
                conn.execute(text("""
                    CREATE TABLE products_new (
                        id INTEGER NOT NULL PRIMARY KEY,
                        name VARCHAR(255) NOT NULL,
                        description TEXT NOT NULL,
                        price FLOAT NOT NULL,
                        unit VARCHAR(50) NOT NULL DEFAULT 'kg',
                        icon VARCHAR(100) NOT NULL,
                        image_url VARCHAR(500),
                        available BOOLEAN DEFAULT 1,
                        created_at DATETIME,
                        updated_at DATETIME
                    )
                """))
                
                # Copy data from old table to new table
                conn.execute(text("""
                    INSERT INTO products_new 
                    (id, name, description, price, unit, icon, available, created_at, updated_at)
                    SELECT id, name, description, price, unit, icon, available, created_at, updated_at
                    FROM products
                """))
                
                # Drop old table
                conn.execute(text("DROP TABLE products"))
                
                # Rename new table to products
                conn.execute(text("ALTER TABLE products_new RENAME TO products"))
                
                # Commit transaction
                trans.commit()
                print("✓ Successfully added 'image_url' column to products table")
                
            except Exception as e:
                trans.rollback()
                raise e
                
    except Exception as e:
        print(f"✗ Error migrating database: {e}")
        sys.exit(1)

if __name__ == "__main__":
    migrate_add_image_url()

