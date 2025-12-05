from dataclasses import dataclass
from decimal import Decimal
from enum import Enum
from typing import Union
import re


class Currency(Enum):
    EUR = "EUR"
    USD = "USD" 
    GBP = "GBP"
    JPY = "JPY"
    CHF = "CHF"


@dataclass(frozen=True)
class Money:
    amount: Decimal
    currency: Currency
    
    def __post_init__(self):
        if self.amount < 0:
            raise ValueError("Le montant ne peut pas être négatif")
    
    def to_euros(self, exchange_rate: Decimal) -> "Money":
        if self.currency == Currency.EUR:
            return self
        
        euro_amount = self.amount * exchange_rate
        return Money(euro_amount, Currency.EUR)
    
    def add(self, other: "Money") -> "Money":
        if self.currency != other.currency:
            raise ValueError("Impossible d'additionner des devises différentes")
        
        return Money(self.amount + other.amount, self.currency)
    
    def subtract(self, other: "Money") -> "Money":
        if self.currency != other.currency:
            raise ValueError("Impossible de soustraire des devises différentes")
        
        result_amount = self.amount - other.amount
        if result_amount < 0:
            raise ValueError("Le résultat ne peut pas être négatif")
            
        return Money(result_amount, self.currency)
    
    def multiply(self, factor: Union[int, Decimal]) -> "Money":
        return Money(self.amount * Decimal(str(factor)), self.currency)
    
    def is_sufficient_for(self, required: "Money") -> bool:
        if self.currency != required.currency:
            raise ValueError("Impossible de comparer des devises différentes")
        
        return self.amount >= required.amount


@dataclass(frozen=True)
class Email:
    value: str
    
    def __post_init__(self):
        if not self._is_valid_email(self.value):
            raise ValueError(f"Adresse email invalide: {self.value}")
    
    @staticmethod
    def _is_valid_email(email: str) -> bool:
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return re.match(pattern, email) is not None


@dataclass(frozen=True)
class PhoneNumber:
    value: str
    
    def __post_init__(self):
        if not self._is_valid_phone(self.value):
            raise ValueError(f"Numero de telephone invalide: {self.value}")
    
    @staticmethod
    def _is_valid_phone(phone: str) -> bool:
        pattern = r'^\+?[1-9]\d{1,14}$'
        cleaned = re.sub(r'[\s\-\(\)]', '', phone)
        return re.match(pattern, cleaned) is not None


@dataclass(frozen=True)
class CustomerId:
    value: str
    
    def __post_init__(self):
        if not self.value:
            raise ValueError("L'identifiant client ne peut pas être vide")
        if not (self.value.isdigit() or len(self.value) >= 6):
            raise ValueError("L'identifiant client doit être numerique ou contenir au moins 6 caracteres")


@dataclass(frozen=True)
class FullName:
    value: str
    
    def __post_init__(self):
        if not self.value or len(self.value.strip()) < 2:
            raise ValueError("Le nom complet doit contenir au moins 2 caracteres")
        
        object.__setattr__(self, 'value', self.value.strip())