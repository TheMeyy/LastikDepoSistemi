from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel
from app.models.database import get_db
from app.models.models import Brand, Tire

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


@router.delete("/{brand_name}", status_code=status.HTTP_200_OK)
def delete_brand(brand_name: str, db: Session = Depends(get_db)):
    """Delete a brand by its name if not used by any tire"""
    sanitized_name = brand_name.strip()
    brand = db.query(Brand).filter(Brand.marka_adi == sanitized_name).first()
    if not brand:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Marka '{sanitized_name}' bulunamadı"
        )

    # Prevent deleting brands that are already in use (FK constraint safety)
    is_used = db.query(Tire).filter(Tire.marka_id == brand.id).first()
    if is_used:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Bu marka mevcut lastiklerde kullanıldığı için silinemez"
        )

    db.delete(brand)
    db.commit()

    return {"detail": "Marka silindi", "marka_adi": sanitized_name}

