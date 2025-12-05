
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional
from decimal import Decimal
from ..main import Money, Currency, CustomerId
from .money import WalletId, TransactionId, ExchangeRate


@dataclass
class Transaction:

    id: TransactionId
    
    wallet_id: WalletId
    amount: Money
    reason: str
    transaction_type: str
    
    created_at: datetime = field(default_factory=datetime.now)
    processed_at: Optional[datetime] = field(default=None)
    
    def mark_as_processed(self) -> None:
        if self.processed_at is not None:
            raise ValueError("Transaction déjà traitée")
        
        self.processed_at = datetime.now()
    
    @property
    def is_processed(self) -> bool:
        return self.processed_at is not None
    
    def __eq__(self, other) -> bool:
        if not isinstance(other, Transaction):
            return False
        return self.id == other.id
    
    def __hash__(self) -> int:
        return hash(self.id.value)


@dataclass
class Wallet:
    id: WalletId
    
    customer_id: CustomerId
    
    balance: Money = field(default_factory=lambda: Money(Decimal("0"), Currency.EUR))
    
    transactions: List[Transaction] = field(default_factory=list)
    
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    
    def credit(self, amount: Money, reason: str, 
               exchange_rate: Optional[ExchangeRate] = None) -> Transaction:
        
        euro_amount = amount
        if amount.currency != Currency.EUR and exchange_rate:
            euro_amount = exchange_rate.convert(amount)
        elif amount.currency != Currency.EUR:
            raise ValueError("Taux de change requis pour les devises étrangères")
        
        transaction = Transaction(
            id=TransactionId(f"TXN_{datetime.now().isoformat()}_{len(self.transactions)}"),
            wallet_id=self.id,
            amount=euro_amount,
            reason=reason,
            transaction_type="CREDIT"
        )
        
        self.balance = self.balance.add(euro_amount)
        self.transactions.append(transaction)
        self.updated_at = datetime.now()
        
        transaction.mark_as_processed()
        
        return transaction
    
    def debit(self, amount: Money, reason: str) -> Transaction:
        if amount.currency != Currency.EUR:
            raise ValueError("Les débits ne peuvent se faire qu'en euros")
        
        if not self.balance.is_sufficient_for(amount):
            raise ValueError(f"Fonds insuffisants. Solde: {self.balance.amount}€, Requis: {amount.amount}€")
        
        transaction = Transaction(
            id=TransactionId(f"TXN_{datetime.now().isoformat()}_{len(self.transactions)}"),
            wallet_id=self.id,
            amount=amount,
            reason=reason,
            transaction_type="DEBIT"
        )
        
        self.balance = self.balance.subtract(amount)
        self.transactions.append(transaction)
        self.updated_at = datetime.now()
        
        transaction.mark_as_processed()
        
        return transaction
    
    def has_sufficient_funds(self, required_amount: Money) -> bool:
        return self.balance.is_sufficient_for(required_amount)
    
    def get_transaction_history(self) -> List[Transaction]:
        return sorted(self.transactions, key=lambda t: t.created_at, reverse=True)
    
    def __eq__(self, other) -> bool:
        if not isinstance(other, Wallet):
            return False
        return self.id == other.id
    
    def __hash__(self) -> int:
        return hash(self.id.value)


from typing import Optional
from decimal import Decimal