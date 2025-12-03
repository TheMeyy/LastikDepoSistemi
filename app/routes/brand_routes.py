from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel
from app.models.database import get_db
from app.models.models import Brand

router = APIRouter(prefix="/api/brands", tags=["brands"])


class BrandCreate(BaseModel):
    marka_adi: str


@router.get("/")
def get_brands(db: Session = Depends(get_db)):
    """Get all available tire brands from database"""
    brands = db.query(Brand).order_by(Brand.marka_adi).all()
    return {"brands": [brand.marka_adi for brand in brands]}


@router.post("/", status_code=status.HTTP_201_CREATED)
def create_brand(brand: BrandCreate, db: Session = Depends(get_db)):
    """Create a new brand"""
    # Check if brand already exists
    existing_brand = db.query(Brand).filter(Brand.marka_adi == brand.marka_adi.strip()).first()
    if existing_brand:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Marka '{brand.marka_adi}' zaten mevcut"
        )
    
    new_brand = Brand(marka_adi=brand.marka_adi.strip())
    db.add(new_brand)
    db.commit()
    db.refresh(new_brand)
    
    return {"id": new_brand.id, "marka_adi": new_brand.marka_adi}

