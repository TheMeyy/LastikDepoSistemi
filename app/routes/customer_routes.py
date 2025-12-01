from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from app.models.database import get_db
from app.models.models import Customer
from app.schemas.customer_schema import CustomerCreate, CustomerRead

router = APIRouter(prefix="/api/customers", tags=["customers"])


@router.post("/", response_model=CustomerRead, status_code=status.HTTP_201_CREATED)
def create_customer(customer: CustomerCreate, db: Session = Depends(get_db)):
    """Create a new customer"""
    db_customer = Customer(
        ad_soyad=customer.ad_soyad,
        telefon=customer.telefon,
        plaka=customer.plaka
    )
    db.add(db_customer)
    db.commit()
    db.refresh(db_customer)
    return db_customer


@router.get("/", response_model=List[CustomerRead])
def get_customers(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    """Get all customers"""
    customers = db.query(Customer).offset(skip).limit(limit).all()
    return customers


@router.get("/{customer_id}", response_model=CustomerRead)
def get_customer(customer_id: int, db: Session = Depends(get_db)):
    """Get a specific customer by ID"""
    customer = db.query(Customer).filter(Customer.id == customer_id).first()
    if not customer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Customer with ID {customer_id} not found"
        )
    return customer


@router.put("/{customer_id}", response_model=CustomerRead)
def update_customer(
    customer_id: int,
    customer: CustomerCreate,
    db: Session = Depends(get_db)
):
    """Update a customer"""
    db_customer = db.query(Customer).filter(Customer.id == customer_id).first()
    if not db_customer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Customer with ID {customer_id} not found"
        )
    
    db_customer.ad_soyad = customer.ad_soyad
    db_customer.telefon = customer.telefon
    db_customer.plaka = customer.plaka
    
    db.commit()
    db.refresh(db_customer)
    return db_customer


@router.delete("/{customer_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_customer(customer_id: int, db: Session = Depends(get_db)):
    """Delete a customer (cascade delete will remove related tires)"""
    try:
        db_customer = db.query(Customer).filter(Customer.id == customer_id).first()
        if not db_customer:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Müşteri bulunamadı"
            )
        
        # Get related tires before deletion to update rack statuses
        from app.models.models import Tire, Rack
        from app.models.models import TireDurumEnum as ModelTireDurumEnum
        from app.utils.enums import RackDurumEnum
        from sqlalchemy import func
        
        related_tires = db.query(Tire).filter(Tire.musteri_id == customer_id).all()
        
        # Get unique rack IDs that will be affected
        affected_rack_ids = list(set([tire.raf_id for tire in related_tires if tire.raf_id]))
        
        # Delete customer (cascade will delete tires)
        db.delete(db_customer)
        db.commit()
        
        # Update rack statuses if needed (check if racks are now empty)
        for rack_id in affected_rack_ids:
            rack = db.query(Rack).filter(Rack.id == rack_id).first()
            if rack:
                # Count remaining tires in this rack with status "DEPODA"
                remaining_tires_count = db.query(func.count(Tire.id)).filter(
                    Tire.raf_id == rack_id,
                    Tire.durum == ModelTireDurumEnum.DEPODA
                ).scalar()
                
                if remaining_tires_count == 0:
                    rack.durum = RackDurumEnum.BOS
                    db.add(rack)
        
        db.commit()
        return None
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Müşteri silinirken bir hata oluştu: {str(e)}"
        )

