"""
Migration script to create tire_history table and add DEGISTIRILDI status to tires table.
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
    """Create tire_history table and update tire status enum"""
    with engine.connect() as conn:
        try:
            # Check if tire_history table exists
            check_table = text("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_name='tire_history'
            """)
            result = conn.execute(check_table)
            
            if result.fetchone() is None:
                # Create tire_history table
                create_table = text("""
                    CREATE TABLE tire_history (
                        id SERIAL PRIMARY KEY,
                        musteri_id INTEGER NOT NULL REFERENCES customers(id),
                        musteri_adi VARCHAR NOT NULL,
                        plaka VARCHAR NOT NULL,
                        telefon VARCHAR,
                        islem_turu VARCHAR(50) NOT NULL,
                        islem_tarihi TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL,
                        eski_lastik_ebat TEXT,
                        eski_lastik_marka VARCHAR,
                        yeni_lastik_ebat TEXT,
                        yeni_lastik_marka VARCHAR,
                        raf_kodu VARCHAR,
                        "not" TEXT
                    )
                """)
                conn.execute(create_table)
                print("✅ Created tire_history table")
            else:
                print("⏭️  tire_history table already exists")
            
            # Check if DEGISTIRILDI value exists in tires.durum enum
            # Since durum is stored as VARCHAR (native_enum=False), we don't need to alter enum type
            # Just verify the column exists
            check_column = text("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name='tires' AND column_name='durum'
            """)
            result = conn.execute(check_column)
            if result.fetchone():
                print("✅ tires.durum column exists (VARCHAR, no enum constraint)")
            else:
                print("⚠️  tires.durum column not found")
            
            conn.commit()
            print("\n✅ Migration completed successfully!")
            
        except Exception as e:
            conn.rollback()
            print(f"\n❌ Error during migration: {e}")
            raise

if __name__ == "__main__":
    print("Starting migration...")
    migrate()








