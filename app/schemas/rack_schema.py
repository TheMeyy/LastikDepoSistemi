from pydantic import BaseModel, Field
from typing import Optional
from app.utils.enums import RackDurumEnum


class RackCreate(BaseModel):
    """Schema for creating a rack"""
    kod: str = Field(..., description="Rack code")
    durum: RackDurumEnum = Field(default=RackDurumEnum.BOS, description="Rack status")
    not_: Optional[str] = Field(None, alias="not", description="Optional note")

    class Config:
        populate_by_name = True
        json_schema_extra = {
            "example": {
                "kod": "A-01",
                "durum": "Boş",
                "not": "Üst raf"
            }
        }


class RackRead(BaseModel):
    """Schema for reading a rack"""
    id: int
    kod: str
    durum: RackDurumEnum
    not_: Optional[str] = Field(None, alias="not")

    class Config:
        from_attributes = True
        populate_by_name = True








