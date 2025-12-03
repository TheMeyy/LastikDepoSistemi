"""
Initialize tire_sizes table and add initial data if needed.
Also initialize brands table with initial brands if needed.
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

# Initial tire sizes
INITIAL_TIRE_SIZES = [
    "195/55 R16",
    "205/55 R16",
    "205/60 R15",
    "215/65 R16"
]

# Initial brands
INITIAL_BRANDS = [
    "Michelin",
    "Pirelli",
    "Goodyear",
    "Lassa",
    "Continental",
    "Petlas",
    "Bridgestone",
    "Uniroyal",
    "Matador"
]

def init_tables():
    """Create tire_sizes table and add initial data"""
    with engine.connect() as conn:
        try:
            # Create tire_sizes table if it doesn't exist
            create_table_query = text("""
                CREATE TABLE IF NOT EXISTS tire_sizes (
                    id SERIAL PRIMARY KEY,
                    ebat VARCHAR NOT NULL UNIQUE
                )
            """)
            conn.execute(create_table_query)
            print("✅ tire_sizes table created/verified")
            
            # Add initial tire sizes if they don't exist
            for size in INITIAL_TIRE_SIZES:
                check_query = text("SELECT id FROM tire_sizes WHERE ebat = :ebat")
                result = conn.execute(check_query, {"ebat": size})
                
                if result.fetchone() is None:
                    insert_query = text("INSERT INTO tire_sizes (ebat) VALUES (:ebat)")
                    conn.execute(insert_query, {"ebat": size})
                    print(f"✅ Added initial tire size: {size}")
                else:
                    print(f"⏭️  Tire size already exists: {size}")
            
            # Add initial brands if they don't exist
            for brand in INITIAL_BRANDS:
                check_query = text("SELECT id FROM brands WHERE marka_adi = :marka_adi")
                result = conn.execute(check_query, {"marka_adi": brand})
                
                if result.fetchone() is None:
                    insert_query = text("INSERT INTO brands (marka_adi) VALUES (:marka_adi)")
                    conn.execute(insert_query, {"marka_adi": brand})
                    print(f"✅ Added initial brand: {brand}")
                else:
                    print(f"⏭️  Brand already exists: {brand}")
            
            # Commit the transaction
            conn.commit()
            print("\n✅ Initialization completed successfully!")
            
        except Exception as e:
            conn.rollback()
            print(f"\n❌ Error during initialization: {e}")
            raise

if __name__ == "__main__":
    print("Starting initialization...")
    init_tables()

