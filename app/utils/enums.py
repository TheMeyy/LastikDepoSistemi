from enum import Enum


class MevsimEnum(str, Enum):
    """Tire season enum"""
    YAZ = "Yaz"
    KIS = "Kış"
    DORT_MEVSIM = "4 Mevsim"


class DisDurumuEnum(str, Enum):
    """Tire condition enum"""
    IYI = "İyi"
    ORTA = "Orta"
    KOTU = "Kötü"


class TireDurumEnum(str, Enum):
    """Tire status enum"""
    DEPODA = "Depoda"
    CIKTI = "Çıkmış"


class RackDurumEnum(str, Enum):
    """Rack status enum"""
    BOS = "Boş"
    DOLU = "Dolu"


# Predefined brand list
BRAND_LIST = [
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

# Predefined tire sizes list
TIRE_SIZES = [
    "195/55 R16",
    "205/55 R16",
    "205/60 R15",
    "215/65 R16"
]

