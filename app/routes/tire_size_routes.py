from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel
from app.models.database import get_db
from app.models.models import TireSize

router = APIRouter(prefix="/api/tire-sizes", tags=["tire-sizes"])


class TireSizeCreate(BaseModel):
    ebat: str


@router.get("/")
def get_tire_sizes(db: Session = Depends(get_db)):
    """Get all available tire sizes from database"""
    tire_sizes = db.query(TireSize).order_by(TireSize.ebat).all()
    return {"tire_sizes": [size.ebat for size in tire_sizes]}


@router.post("/", status_code=status.HTTP_201_CREATED)
def create_tire_size(tire_size: TireSizeCreate, db: Session = Depends(get_db)):
    """Create a new tire size"""
    # Check if tire size already exists
    existing_size = db.query(TireSize).filter(TireSize.ebat == tire_size.ebat.strip()).first()
    if existing_size:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Ebat '{tire_size.ebat}' zaten mevcut"
        )
    
    new_size = TireSize(ebat=tire_size.ebat.strip())
    db.add(new_size)
    db.commit()
    db.refresh(new_size)
    
    return {"id": new_size.id, "ebat": new_size.ebat}


@router.delete("/", status_code=status.HTTP_200_OK)
def delete_tire_size(ebat: str, db: Session = Depends(get_db)):
    """Delete a tire size by its value (query param to allow slashes like 225/50 R17)"""
    sanitized_size = ebat.strip()
    tire_size = db.query(TireSize).filter(TireSize.ebat == sanitized_size).first()
    if not tire_size:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Ebat '{sanitized_size}' bulunamadı"
        )

    db.delete(tire_size)
    db.commit()

    return {"detail": "Ebat silindi", "ebat": sanitized_size}









