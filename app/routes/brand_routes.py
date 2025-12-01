from fastapi import APIRouter
from app.utils.enums import BRAND_LIST

router = APIRouter(prefix="/api/brands", tags=["brands"])


@router.get("/")
def get_brands():
    """Get all available tire brands"""
    return {"brands": BRAND_LIST}

