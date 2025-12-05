"""
Contexte Booking Management - Cœur du système de réservation.
Contient les entities et value objects pour la gestion des réservations.
"""

from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from enum import Enum
from decimal import Decimal
from typing import List, Optional
from ..main import CustomerId, Money, Currency
from ..room_management.room_types import RoomTypeEnum, RoomId


class BookingStatus(Enum):
    PENDING = "PENDING"
    CONFIRMED = "CONFIRMED" 
    CANCELLED = "CANCELLED"


class PaymentType(Enum):
    DEPOSIT = "DEPOSIT"
    BALANCE = "BALANCE"


@dataclass(frozen=True)
class BookingId:
    value: str
    
    def __post_init__(self):
        if not self.value:
            raise ValueError("L'identifiant de réservation ne peut pas etre vide")


@dataclass(frozen=True)
class CheckInDate:
    value: date
    
    def __post_init__(self):
        if self.value < date.today():
            raise ValueError("La date de check-in ne peut pas etre dans le passé")


@dataclass(frozen=True)
class NumberOfNights:
    value: int
    
    def __post_init__(self):
        if self.value <= 0:
            raise ValueError('Le nombre de jours doit etre superieur a 0')
        if self.value > 365:
            raise ValueError('le nombre de jours reservés ne peut pas etre superieur a 365')



@dataclass(frozen=True)
class Stay:
    check_in: CheckInDate
    nights: NumberOfNights
    
    @property
    def check_out(self) -> date:
        return self.check_in.value + timedelta(days=self.nights.value)
    
    def overlaps_with(self, other: "Stay") -> bool:
        return not (self.check_out <= other.check_in.value or 
                   other.check_out <= self.check_in.value)


@dataclass(frozen=True)
class PaymentId:
    value: str
    
    def __post_init__(self):
        if not self.value:
            raise ValueError("Pas d'identifiant de paiement")



@dataclass
class Payment:
    id: PaymentId
    
    booking_id: BookingId
    amount: Money
    payment_type: PaymentType

    is_processed: bool = field(default=False)
    processed_at: Optional[datetime] = field(default=None)
    created_at: datetime = field(default_factory=datetime.now)
    
    def process(self) -> None:
        if self.is_processed:
            raise ValueError("Paiement deja traité")
        
        self.is_processed = True
        self.processed_at = datetime.now()
    
    def __eq__(self, other) -> bool:
        if not isinstance(other, Payment):
            return False
        return self.id == other.id
    
    def __hash__(self) -> int:
        return hash(self.id.value)


@dataclass
class Booking:
    id: BookingId
    
    customer_id: CustomerId
    
    room_type: RoomTypeEnum
    room_quantity: int
    stay: Stay
    
    total_amount: Money
    
    status: BookingStatus = field(default=BookingStatus.PENDING)
    reserved_rooms: List[RoomId] = field(default_factory=list)
    
    payments: List[Payment] = field(default_factory=list)
    
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    
    def __post_init__(self):
        if self.room_quantity <= 0:
            raise ValueError("La quantite de chambres doit etre positive")
        
        if self.total_amount.currency != Currency.EUR:
            raise ValueError("Le montant total doit etre en euros")
    
    @property
    def deposit_amount(self) -> Money:
        return self.total_amount.multiply(Decimal("0.5"))
    
    @property
    def balance_amount(self) -> Money:
        return self.total_amount.multiply(Decimal("0.5"))
    
    def pay_deposit(self) -> Payment:
        if self.status != BookingStatus.PENDING:
            raise ValueError("L'acompte ne peut etre payé que pour une reservation en attente")
        
        deposit_payment = Payment(
            id=PaymentId(f"PAY_{self.id.value}_DEPOSIT_{datetime.now().isoformat()}"),
            booking_id=self.id,
            amount=self.deposit_amount,
            payment_type=PaymentType.DEPOSIT
        )
        
        self.payments.append(deposit_payment)
        deposit_payment.process()
        self.updated_at = datetime.now()
        
        return deposit_payment
    
    def confirm_booking(self) -> Payment:
        if self.status != BookingStatus.PENDING:
            raise ValueError("Seule une reservation en attente peut etre confirmée")
        
        if not self._has_deposit_payment():
            raise ValueError("L'acompte doit etre paye avant la confirmation")
        
        balance_payment = Payment(
            id=PaymentId(f"PAY_{self.id.value}_BALANCE_{datetime.now().isoformat()}"),
            booking_id=self.id,
            amount=self.balance_amount,
            payment_type=PaymentType.BALANCE
        )
        
        self.payments.append(balance_payment)
        balance_payment.process()
        self.status = BookingStatus.CONFIRMED
        self.updated_at = datetime.now()
        
        return balance_payment
    
    def cancel(self) -> None:
        if self.status == BookingStatus.CANCELLED:
            raise ValueError("La reservation est deja annulée")
        
        self.status = BookingStatus.CANCELLED
        self.updated_at = datetime.now()
    
    def assign_rooms(self, room_ids: List[RoomId]) -> None:
        if len(room_ids) != self.room_quantity:
            raise ValueError(f"Nombre de chambres incorrect. Attendu: {self.room_quantity}, Reçu: {len(room_ids)}")
        
        self.reserved_rooms = room_ids.copy()
        self.updated_at = datetime.now()
    
    def _has_deposit_payment(self) -> bool:
        return any(
            payment.payment_type == PaymentType.DEPOSIT and payment.is_processed
            for payment in self.payments
        )
    
    def get_total_paid(self) -> Money:
        total = Money(Decimal("0"), Currency.EUR)
        for payment in self.payments:
            if payment.is_processed:
                total = total.add(payment.amount)
        return total
    
    def __eq__(self, other) -> bool:
        if not isinstance(other, Booking):
            return False
        return self.id == other.id
    
    def __hash__(self) -> int:
        return hash(self.id.value)