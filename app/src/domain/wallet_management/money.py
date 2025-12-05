from dataclasses import dataclass
from decimal import Decimal
from datetime import datetime
from ..main import Money, Currency

@dataclass(frozen=True)
class ExchangeRate:
    from_currency: Currency
    to_currency: Currency
    rate: Decimal
    
    def __post_init__(self):
        if self.to_currency != Currency.EUR:
            raise ValueError("Les conversions ne sont supportées que vers l'euro")
        if self.rate <= 0:
            raise ValueError("Le taux de change doit être positif")
    
    def convert(self, money: Money) -> Money:
        if money.currency != self.from_currency:
            raise ValueError(f"Ce taux est pour {self.from_currency}, pas {money.currency}")
        return money.to_euros(self.rate)

@dataclass(frozen=True)
class WalletId:
    value: str
    def __post_init__(self):
        if not self.value:
            raise ValueError("L'identifiant de portefeuille ne peut pas être vide")

@dataclass(frozen=True)
class TransactionId:
    value: str
    def __post_init__(self):
        if not self.value:
            raise ValueError("L'identifiant de transaction ne peut pas être vide")

@dataclass(frozen=True)
class TransactionReason:
    value: str
    def __post_init__(self):
        if not self.value.strip():
            raise ValueError("La raison de la transaction ne peut pas être vide")
        object.__setattr__(self, 'value', self.value.strip())