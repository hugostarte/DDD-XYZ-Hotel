 
from dataclasses import dataclass
from decimal import Decimal
from enum import Enum
from typing import List
from ..main import Money, Currency


class RoomTypeEnum(Enum):
    STANDARD = "STANDARD"
    SUPERIOR = "SUPERIOR" 
    SUITE = "SUITE"


@dataclass(frozen=True)
class Equipment:
    name: str
    description: str = ""


@dataclass(frozen=True)
class RoomType:
    type: RoomTypeEnum
    price_per_night: Money
    equipment_list: tuple[Equipment, ...]
    
    def __post_init__(self):
        if self.price_per_night.currency != Currency.EUR:
            raise ValueError("Le prix doit être en euros")
        
        if self.price_per_night.amount <= 0:
            raise ValueError("Le prix doit être positif")
    
    @classmethod
    def standard(cls) -> "RoomType":
        equipment = (
            Equipment("Lit 1 place"),
            Equipment("Wifi"),
            Equipment("TV")
        )
        return cls(
            type=RoomTypeEnum.STANDARD,
            price_per_night=Money(Decimal("50"), Currency.EUR),
            equipment_list=equipment
        )
    
    @classmethod
    def superior(cls) -> "RoomType":
        equipment = (
            Equipment("Lit 2 places"),
            Equipment("Wifi"),
            Equipment("TV écran plat"),
            Equipment("Minibar"),
            Equipment("Climatiseur")
        )
        return cls(
            type=RoomTypeEnum.SUPERIOR,
            price_per_night=Money(Decimal("100"), Currency.EUR),
            equipment_list=equipment
        )
    
    @classmethod
    def suite(cls) -> "RoomType":
        equipment = (
            Equipment("Lit 2 places"),
            Equipment("Wifi"),
            Equipment("TV écran plat"),
            Equipment("Minibar"),
            Equipment("Climatiseur"),
            Equipment("Baignoire"),
            Equipment("Terrasse")
        )
        return cls(
            type=RoomTypeEnum.SUITE,
            price_per_night=Money(Decimal("200"), Currency.EUR),
            equipment_list=equipment
        )


@dataclass(frozen=True)
class RoomId:
    value: str
    
    def __post_init__(self):
        if not self.value:
            raise ValueError("L'identifiant de chambre ne peut pas être vide")


@dataclass(frozen=True)
class RoomNumber:
    value: str
    
    def __post_init__(self):
        if not self.value:
            raise ValueError("Le numéro de chambre ne peut pas être vide")