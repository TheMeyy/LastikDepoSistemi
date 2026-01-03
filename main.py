from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse
from starlette.middleware.sessions import SessionMiddleware

from app.models.database import engine, Base
from app.models import models  # tabloların register olması için

from app.routes import (
    customer_routes,
    rack_routes,
    tire_routes,
    brand_routes,
    tire_size_routes,
    tire_history_routes,
    web_routes,
)

# -------------------------------------------------
# FASTAPI APP
# -------------------------------------------------
app = FastAPI(
    title="LastikDepoSistemi",
    version="1.0.0"
)

# -------------------------------------------------
# SESSION MIDDLEWARE (LOGIN İÇİN)
# ⚠️ ROOT ROUTE'TAN ÖNCE OLMALI
# -------------------------------------------------
app.add_middleware(
    SessionMiddleware,
    secret_key="nusretler_lastik_depo_secret"
)

# -------------------------------------------------
# ROOT ROUTE (LOGIN KONTROLÜ)
# -------------------------------------------------
@app.get("/", include_in_schema=False)
async def root(request: Request):
    if not request.session.get("logged_in"):
        return RedirectResponse(url="/login", status_code=302)
    return RedirectResponse(url="/lastik-ara", status_code=302)

# -------------------------------------------------
# STATIC FILES
# -------------------------------------------------
app.mount("/static", StaticFiles(directory="app/static"), name="static")

# -------------------------------------------------
# CORS
# -------------------------------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # canlıda domain yazılır
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# -------------------------------------------------
# API ROUTER'LAR (⚠️ HEPSİ /api ALTINDA)
# -------------------------------------------------
app.include_router(customer_routes.router)
app.include_router(rack_routes.router)
app.include_router(tire_routes.router)
app.include_router(brand_routes.router)
app.include_router(tire_size_routes.router)
app.include_router(tire_history_routes.router)


# -------------------------------------------------
# WEB ROUTER (HTML SAYFALAR)
# ⚠️ PREFIX YOK
# -------------------------------------------------
app.include_router(web_routes.router)

# -------------------------------------------------
# STARTUP EVENT
# -------------------------------------------------
@app.on_event("startup")
async def startup_event():
    try:
        Base.metadata.create_all(bind=engine)
        print("✅ Database connection successful!")
        print("✅ All tables created successfully!")
        print("✅ LastikDepoSistemi is ready!")
    except Exception as e:
        print(f"❌ Error connecting to database: {e}")
        raise

# -------------------------------------------------
# API & HEALTH
# -------------------------------------------------
@app.get("/api", include_in_schema=False)
async def api_root():
    return {
        "message": "LastikDepoSistemi API",
        "status": "running",
        "version": "1.0.0"
    }

@app.get("/health", include_in_schema=False)
async def health_check():
    return {"status": "healthy"}
