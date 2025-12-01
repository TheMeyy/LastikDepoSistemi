from pydantic import BaseModel, Field, field_validator
from typing import Optional
from datetime import datetime
from app.utils.enums import MevsimEnum, DisDurumuEnum, TireDurumEnum, BRAND_LIST


class TireCreate(BaseModel):
    """Schema for creating a tire"""
    musteri_id: int = Field(..., description="Customer ID")
    brand: str = Field(..., description="Tire brand (from predefined list)")
    ebat: str = Field(..., description="Tire size (e.g., 205/55 R16)")
    mevsim: MevsimEnum = Field(..., description="Season")
    dis_durumu: DisDurumuEnum = Field(..., description="Tire condition")
    not_: Optional[str] = Field(None, alias="not", description="Optional note")
    raf_id: int = Field(..., description="Rack ID")
    giris_tarihi: Optional[datetime] = Field(None, description="Entry date (defaults to now)")
    cikis_tarihi: Optional[datetime] = Field(None, description="Exit date")
    durum: TireDurumEnum = Field(default=TireDurumEnum.DEPODA, description="Tire status")
    
    @field_validator("durum", mode="before")
    @classmethod
    def validate_durum(cls, v):
        if v is None:
            return TireDurumEnum.DEPODA
        if isinstance(v, str):
            # Convert string to enum
            v_clean = v.strip()
            if v_clean == "Çıkmış" or v_clean == "CIKTI":
                return TireDurumEnum.CIKTI
            elif v_clean == "Depoda" or v_clean == "DEPODA":
                return TireDurumEnum.DEPODA
            else:
                # Try to convert directly using enum value
                try:
                    # Try by value first
                    for enum_item in TireDurumEnum:
                        if enum_item.value == v_clean:
                            return enum_item
                    # If not found, try by name
                    return TireDurumEnum[v_clean]
                except (ValueError, KeyError):
                    raise ValueError(f"Invalid tire status: '{v}'. Must be 'Depoda', 'Çıkmış', 'DEPODA', or 'CIKTI'")
        elif isinstance(v, TireDurumEnum):
            return v
        return v

    @field_validator("brand")
    @classmethod
    def validate_brand(cls, v):
        if v not in BRAND_LIST:
            raise ValueError(f"Brand must be one of: {', '.join(BRAND_LIST)}")
        return v

    class Config:
        populate_by_name = True
        json_schema_extra = {
            "example": {
                "musteri_id": 1,
                "brand": "Michelin",
                "ebat": "205/55 R16",
                "mevsim": "Yaz",
                "dis_durumu": "İyi",
                "not": "Yeni lastik",
                "raf_id": 1,
                "durum": "Depoda"
            }
        }


class TireRead(BaseModel):
    """Schema for reading a tire"""
    id: int
    musteri_id: int
    brand: str  # Will be populated from Brand relationship
    ebat: str
    mevsim: MevsimEnum
    dis_durumu: DisDurumuEnum
    not_: Optional[str] = Field(None, alias="not")
    raf_id: int
    rack_code: str  # Will be populated from Rack relationship
    giris_tarihi: datetime
    cikis_tarihi: Optional[datetime]
    durum: TireDurumEnum
    customer_name: str  # Will be populated from Customer relationship
    customer_plate: str  # Will be populated from Customer relationship

    class Config:
        from_attributes = True
        populate_by_name = True

