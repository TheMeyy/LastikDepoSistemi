from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from app.models.database import engine, Base
from app.models import models  # Import models to register them with Base
from app.routes import customer_routes, rack_routes, tire_routes, brand_routes, tire_size_routes, web_routes

# Initialize FastAPI app
app = FastAPI(title="LastikDepoSistemi", version="1.0.0")

# Mount static files
app.mount("/static", StaticFiles(directory="app/static"), name="static")

# Enable CORS for frontend connection
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with specific origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(customer_routes.router)
app.include_router(rack_routes.router)
app.include_router(tire_routes.router)
app.include_router(brand_routes.router)
app.include_router(tire_size_routes.router)
app.include_router(web_routes.router)


@app.on_event("startup")
async def startup_event():
    """Create database tables on startup"""
    try:
        # Create all tables
        Base.metadata.create_all(bind=engine)
        print("✅ Database connection successful!")
        print("✅ All tables created successfully!")
        print("✅ LastikDepoSistemi is ready!")
    except Exception as e:
        print(f"❌ Error connecting to database: {e}")
        raise


@app.get("/api")
async def api_root():
    """API root endpoint"""
    return {
        "message": "LastikDepoSistemi API",
        "status": "running",
        "version": "1.0.0"
    }


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy"}

