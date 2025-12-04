"""
Migration script to add 'DEGISTIRILDI' value to tiredurumenum enum in PostgreSQL
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
    """Add 'DEGISTIRILDI' value to tiredurumenum enum"""
    try:
        with engine.connect() as conn:
            # Check if 'DEGISTIRILDI' already exists in the enum
            check_query = text("""
                SELECT EXISTS (
                    SELECT 1 
                    FROM pg_enum 
                    WHERE enumlabel = 'DEGISTIRILDI' 
                    AND enumtypid = (
                        SELECT oid 
                        FROM pg_type 
                        WHERE typname = 'tiredurumenum'
                    )
                );
            """)
            result = conn.execute(check_query)
            exists = result.scalar()
            
            if exists:
                print("✅ 'DEGISTIRILDI' value already exists in tiredurumenum enum")
                return
            
            # Add 'DEGISTIRILDI' to the enum
            alter_query = text("""
                ALTER TYPE tiredurumenum ADD VALUE IF NOT EXISTS 'DEGISTIRILDI';
            """)
            conn.execute(alter_query)
            conn.commit()
            print("✅ Successfully added 'DEGISTIRILDI' to tiredurumenum enum")
            
    except Exception as e:
        print(f"❌ Error adding enum value: {e}")
        raise

if __name__ == "__main__":
    print("Starting migration: Adding 'DEGISTIRILDI' to tiredurumenum enum...")
    migrate()
    print("Migration completed!")

