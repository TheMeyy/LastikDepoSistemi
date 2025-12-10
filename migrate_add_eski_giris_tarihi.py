"""
Migration script to add 'eski_lastik_giris_tarihi' column to tire_history table
"""
import os
from dotenv import load_dotenv
from sqlalchemy import create_engine, text

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
    """Add 'eski_lastik_giris_tarihi' column to tire_history table"""
    try:
        with engine.connect() as conn:
            # Check if column already exists
            check_query = text("""
                SELECT EXISTS (
                    SELECT 1 
                    FROM information_schema.columns 
                    WHERE table_name = 'tire_history' 
                    AND column_name = 'eski_lastik_giris_tarihi'
                );
            """)
            result = conn.execute(check_query)
            exists = result.scalar()
            
            if exists:
                print("✅ 'eski_lastik_giris_tarihi' column already exists in tire_history table")
                return
            
            # Add column
            alter_query = text("""
                ALTER TABLE tire_history 
                ADD COLUMN eski_lastik_giris_tarihi TIMESTAMP WITH TIME ZONE;
            """)
            conn.execute(alter_query)
            conn.commit()
            print("✅ Successfully added 'eski_lastik_giris_tarihi' column to tire_history table")
            
    except Exception as e:
        print(f"❌ Error adding column: {e}")
        raise

if __name__ == "__main__":
    print("Starting migration: Adding 'eski_lastik_giris_tarihi' column to tire_history table...")
    migrate()
    print("Migration completed!")









