"""
Migration script to add tire1_size through tire6_size and tire1_production_date through tire6_production_date columns
to the tires table.
"""
import os
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Database configuration
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_USER = os.getenv("DB_USER", "postgres")
DB_PASSWORD = os.getenv("DB_PASSWORD", "")
DB_NAME = os.getenv("DB_NAME", "lastik_depo_db")

# Create database URL
DATABASE_URL = f"postgresql+psycopg://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

# Create engine
engine = create_engine(DATABASE_URL, echo=True)

def migrate():
    """Add missing columns to tires table"""
    with engine.connect() as conn:
        try:
            # Check if columns already exist and add them if they don't
            columns_to_add = [
                ("tire1_size", "VARCHAR"),
                ("tire1_production_date", "VARCHAR"),
                ("tire2_size", "VARCHAR"),
                ("tire2_production_date", "VARCHAR"),
                ("tire3_size", "VARCHAR"),
                ("tire3_production_date", "VARCHAR"),
                ("tire4_size", "VARCHAR"),
                ("tire4_production_date", "VARCHAR"),
                ("tire5_size", "VARCHAR"),
                ("tire5_production_date", "VARCHAR"),
                ("tire6_size", "VARCHAR"),
                ("tire6_production_date", "VARCHAR"),
            ]
            
            for column_name, column_type in columns_to_add:
                # Check if column exists
                check_query = text(f"""
                    SELECT column_name 
                    FROM information_schema.columns 
                    WHERE table_name='tires' AND column_name='{column_name}'
                """)
                result = conn.execute(check_query)
                
                if result.fetchone() is None:
                    # Column doesn't exist, add it
                    alter_query = text(f"ALTER TABLE tires ADD COLUMN {column_name} {column_type}")
                    conn.execute(alter_query)
                    print(f"✅ Added column: {column_name}")
                else:
                    print(f"⏭️  Column already exists: {column_name}")
            
            # Commit the transaction
            conn.commit()
            print("\n✅ Migration completed successfully!")
            
        except Exception as e:
            conn.rollback()
            print(f"\n❌ Error during migration: {e}")
            raise

if __name__ == "__main__":
    print("Starting migration...")
    migrate()

