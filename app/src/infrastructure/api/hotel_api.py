from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Dict
from decimal import Decimal
import uuid
from datetime import datetime, date

from ...domain.main import Money, Currency, CustomerId, Email, FullName, PhoneNumber
from ...domain.customer_management.customer import Customer
from ...domain.room_management.room_types import RoomType, RoomTypeEnum
from ...domain.wallet_management.wallet import Wallet, Transaction
from ...domain.wallet_management.money import WalletId, TransactionId
from ...domain.booking_management.booking import (
    Booking, BookingId, BookingStatus, PaymentType, 
    CheckInDate, NumberOfNights, Stay
)
from ...domain.room_management.room_types import RoomId

app = FastAPI(
    title="XYZ Hôtel API",
    description="API de gestion de réservations hôtelières - Version DDD",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class CustomerCreateRequest(BaseModel):
    full_name: str
    email: str
    phone_number: str

class CustomerResponse(BaseModel):
    id: str
    full_name: str
    email: str
    phone_number: str
    is_active: bool
    created_at: str

class RoomTypeResponse(BaseModel):
    type: str
    price_per_night: float
    equipment_list: List[str]


class WalletCreditRequest(BaseModel):
    amount: float
    reason: str = "Crédit par l'utilisateur"

class WalletResponse(BaseModel):
    id: str
    customer_id: str
    balance: float
    currency: str
    last_updated: str

class TransactionResponse(BaseModel):
    id: str
    amount: float
    reason: str
    transaction_type: str
    created_at: str

class BookingCreateRequest(BaseModel):
    customer_id: str
    room_type: str
    room_quantity: int
    check_in_date: str  # Format YYYY-MM-DD
    number_of_nights: int

class BookingResponse(BaseModel):
    id: str
    customer_id: str
    room_type: str
    room_quantity: int
    check_in_date: str
    check_out_date: str
    total_amount: float
    deposit_amount: float
    balance_amount: float
    status: str
    total_paid: float
    created_at: str

customers_storage: Dict[str, Customer] = {}
wallets_storage: Dict[str, Wallet] = {}
bookings_storage: Dict[str, Booking] = {}

next_customer_id = 0

def get_next_customer_id() -> str:
    """Génère le prochain ID client (incrémentation)."""
    global next_customer_id
    customer_id = str(next_customer_id)
    next_customer_id += 1
    return customer_id

def get_customer_wallet(customer_id: str) -> Wallet:
    """Récupère ou crée le wallet d'un client."""
    for wallet in wallets_storage.values():
        if wallet.customer_id.value == customer_id:
            return wallet
    
    wallet_id = f"WALLET{uuid.uuid4().hex[:8].upper()}"
    wallet = Wallet(
        id=WalletId(wallet_id),
        customer_id=CustomerId(customer_id)
    )
    wallets_storage[wallet_id] = wallet
    return wallet

def calculate_booking_total(room_type: RoomTypeEnum, room_quantity: int, nights: int) -> Money:
    """Calcule le montant total d'une réservation."""
    if room_type == RoomTypeEnum.STANDARD:
        price_per_night = Money(Decimal("50"), Currency.EUR)
    elif room_type == RoomTypeEnum.SUPERIOR:
        price_per_night = Money(Decimal("100"), Currency.EUR)
    elif room_type == RoomTypeEnum.SUITE:
        price_per_night = Money(Decimal("200"), Currency.EUR)
    
    total = price_per_night.multiply(Decimal(str(room_quantity * nights)))
    return total


@app.get("/")
async def root():
    return {
        "message": "XYZ Hôtel API - DDD Implementation",
        "status": "running",
        "version": "1.0.0",
        "endpoints": {
            "customers": "/customers",
            "rooms": "/rooms",
            "health": "/health"
        }
    }

@app.post("/customers", response_model=CustomerResponse, status_code=201)
async def create_customer(customer_data: CustomerCreateRequest):
    try:
        customer_id = get_next_customer_id()
        
        for existing_customer in customers_storage.values():
            if existing_customer.email.value == customer_data.email:
                raise HTTPException(status_code=400, detail="Email déjà utilisé")
        
        customer = Customer(
            id=CustomerId(customer_id),
            full_name=FullName(customer_data.full_name),
            email=Email(customer_data.email),
            phone_number=PhoneNumber(customer_data.phone_number)
        )
        
        customers_storage[customer_id] = customer
        
        return CustomerResponse(
            id=customer.id.value,
            full_name=customer.full_name.value,
            email=customer.email.value,
            phone_number=customer.phone_number.value,
            is_active=customer.is_active,
            created_at=customer.created_at.isoformat()
        )
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/customers", response_model=List[CustomerResponse])
async def list_customers():
    return [
        CustomerResponse(
            id=customer.id.value,
            full_name=customer.full_name.value,
            email=customer.email.value,
            phone_number=customer.phone_number.value,
            is_active=customer.is_active,
            created_at=customer.created_at.isoformat()
        )
        for customer in customers_storage.values()
    ]

@app.get("/customers/{customer_id}", response_model=CustomerResponse)
async def get_customer(customer_id: str):
    if customer_id not in customers_storage:
        raise HTTPException(status_code=404, detail="Client non trouvé")
    
    customer = customers_storage[customer_id]
    return CustomerResponse(
        id=customer.id.value,
        full_name=customer.full_name.value,
        email=customer.email.value,
        phone_number=customer.phone_number.value,
        is_active=customer.is_active,
        created_at=customer.created_at.isoformat()
    )


@app.get("/rooms/types", response_model=List[RoomTypeResponse])
async def get_room_types():
    """Retourne les types de chambres disponibles avec leurs caractéristiques."""
    room_types = [
        RoomType.standard(),
        RoomType.superior(),
        RoomType.suite()
    ]
    
    return [
        RoomTypeResponse(
            type=room_type.type.value,
            price_per_night=float(room_type.price_per_night.amount),
            equipment_list=[eq.name for eq in room_type.equipment_list]
        )
        for room_type in room_types
    ]

@app.get("/rooms/types/{room_type}")
async def get_room_type_details(room_type: str):
    """Retourne les détails d'un type de chambre spécifique."""
    try:
        room_type_enum = RoomTypeEnum(room_type.upper())
    except ValueError:
        raise HTTPException(status_code=400, detail="Type de chambre invalide")
    
    if room_type_enum == RoomTypeEnum.STANDARD:
        room = RoomType.standard()
    elif room_type_enum == RoomTypeEnum.SUPERIOR:
        room = RoomType.superior()
    elif room_type_enum == RoomTypeEnum.SUITE:
        room = RoomType.suite()
    
    return {
        "type": room.type.value,
        "price_per_night": float(room.price_per_night.amount),
        "currency": room.price_per_night.currency.value,
        "equipment": [
            {"name": eq.name, "description": eq.description}
            for eq in room.equipment_list
        ]
    }


@app.get("/customers/{customer_id}/wallet", response_model=WalletResponse)
async def get_customer_wallet_info(customer_id: str):
    """Récupère les informations du wallet d'un client."""
    if customer_id not in customers_storage:
        raise HTTPException(status_code=404, detail="Client non trouvé")
    
    wallet = get_customer_wallet(customer_id)
    return WalletResponse(
        id=wallet.id.value,
        customer_id=wallet.customer_id.value,
        balance=float(wallet.balance.amount),
        currency=wallet.balance.currency.value,
        last_updated=wallet.updated_at.isoformat()
    )

@app.post("/customers/{customer_id}/wallet/credit")
async def credit_wallet(customer_id: str, credit_request: WalletCreditRequest):
    """Crédite le wallet d'un client."""
    if customer_id not in customers_storage:
        raise HTTPException(status_code=404, detail="Client non trouvé")
    
    if credit_request.amount <= 0:
        raise HTTPException(status_code=400, detail="Le montant doit être positif")
    
    wallet = get_customer_wallet(customer_id)
    
    try:
        transaction = wallet.credit(
            amount=Money(Decimal(str(credit_request.amount)), Currency.EUR),
            reason=credit_request.reason
        )
        
        return {
            "message": "Crédit effectué avec succès",
            "transaction": {
                "id": transaction.id.value,
                "amount": float(transaction.amount.amount),
                "reason": transaction.reason,
                "processed_at": transaction.processed_at.isoformat()
            },
            "new_balance": float(wallet.balance.amount)
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/customers/{customer_id}/wallet/transactions", response_model=List[TransactionResponse])
async def get_wallet_transactions(customer_id: str):
    """Récupère l'historique des transactions du wallet."""
    if customer_id not in customers_storage:
        raise HTTPException(status_code=404, detail="Client non trouvé")
    
    wallet = get_customer_wallet(customer_id)
    return [
        TransactionResponse(
            id=txn.id.value,
            amount=float(txn.amount.amount),
            reason=txn.reason,
            transaction_type=txn.transaction_type,
            created_at=txn.created_at.isoformat()
        )
        for txn in wallet.get_transaction_history()
    ]


@app.post("/bookings", response_model=BookingResponse, status_code=201)
async def create_booking(booking_request: BookingCreateRequest):
    """Crée une nouvelle réservation."""
    if booking_request.customer_id not in customers_storage:
        raise HTTPException(status_code=404, detail="Client non trouvé")
    
    try:
        room_type = RoomTypeEnum(booking_request.room_type.upper())
    except ValueError:
        raise HTTPException(status_code=400, detail="Type de chambre invalide")
    
    try:
        check_in = datetime.strptime(booking_request.check_in_date, "%Y-%m-%d").date()
        check_in_obj = CheckInDate(check_in)
        nights_obj = NumberOfNights(booking_request.number_of_nights)
        stay = Stay(check_in_obj, nights_obj)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Erreur de date: {str(e)}")
    
    total_amount = calculate_booking_total(
        room_type, 
        booking_request.room_quantity, 
        booking_request.number_of_nights
    )
    
    booking_id = f"BOOK{uuid.uuid4().hex[:8].upper()}"
    booking = Booking(
        id=BookingId(booking_id),
        customer_id=CustomerId(booking_request.customer_id),
        room_type=room_type,
        room_quantity=booking_request.room_quantity,
        stay=stay,
        total_amount=total_amount
    )
    
    bookings_storage[booking_id] = booking
    
    return BookingResponse(
        id=booking.id.value,
        customer_id=booking.customer_id.value,
        room_type=booking.room_type.value,
        room_quantity=booking.room_quantity,
        check_in_date=booking.stay.check_in.value.isoformat(),
        check_out_date=booking.stay.check_out.isoformat(),
        total_amount=float(booking.total_amount.amount),
        deposit_amount=float(booking.deposit_amount.amount),
        balance_amount=float(booking.balance_amount.amount),
        status=booking.status.value,
        total_paid=float(booking.get_total_paid().amount),
        created_at=booking.created_at.isoformat()
    )

@app.get("/bookings", response_model=List[BookingResponse])
async def list_bookings():
    """Liste toutes les réservations."""
    return [
        BookingResponse(
            id=booking.id.value,
            customer_id=booking.customer_id.value,
            room_type=booking.room_type.value,
            room_quantity=booking.room_quantity,
            check_in_date=booking.stay.check_in.value.isoformat(),
            check_out_date=booking.stay.check_out.isoformat(),
            total_amount=float(booking.total_amount.amount),
            deposit_amount=float(booking.deposit_amount.amount),
            balance_amount=float(booking.balance_amount.amount),
            status=booking.status.value,
            total_paid=float(booking.get_total_paid().amount),
            created_at=booking.created_at.isoformat()
        )
        for booking in bookings_storage.values()
    ]

@app.get("/customers/{customer_id}/bookings", response_model=List[BookingResponse])
async def get_customer_bookings(customer_id: str):
    """Récupère les réservations d'un client."""
    if customer_id not in customers_storage:
        raise HTTPException(status_code=404, detail="Client non trouvé")
    
    customer_bookings = [
        booking for booking in bookings_storage.values()
        if booking.customer_id.value == customer_id
    ]
    
    return [
        BookingResponse(
            id=booking.id.value,
            customer_id=booking.customer_id.value,
            room_type=booking.room_type.value,
            room_quantity=booking.room_quantity,
            check_in_date=booking.stay.check_in.value.isoformat(),
            check_out_date=booking.stay.check_out.isoformat(),
            total_amount=float(booking.total_amount.amount),
            deposit_amount=float(booking.deposit_amount.amount),
            balance_amount=float(booking.balance_amount.amount),
            status=booking.status.value,
            total_paid=float(booking.get_total_paid().amount),
            created_at=booking.created_at.isoformat()
        )
        for booking in customer_bookings
    ]

@app.post("/bookings/{booking_id}/pay-deposit")
async def pay_deposit(booking_id: str):
    """Paye l'acompte d'une réservation avec le wallet du client."""
    if booking_id not in bookings_storage:
        raise HTTPException(status_code=404, detail="Réservation non trouvée")
    
    booking = bookings_storage[booking_id]
    wallet = get_customer_wallet(booking.customer_id.value)
    
    if not wallet.has_sufficient_funds(booking.deposit_amount):
        return {
            "success": False,
            "message": f"Fonds insuffisants. Solde: {wallet.balance.amount}€, Requis: {booking.deposit_amount.amount}€",
            "required_amount": float(booking.deposit_amount.amount),
            "current_balance": float(wallet.balance.amount),
            "shortfall": float(booking.deposit_amount.amount - wallet.balance.amount)
        }
    
    try:
        wallet.debit(
            amount=booking.deposit_amount,
            reason=f"Acompte réservation {booking_id}"
        )
        
        payment = booking.pay_deposit()
        
        return {
            "success": True,
            "message": "Acompte payé avec succès",
            "payment": {
                "id": payment.id.value,
                "amount": float(payment.amount.amount),
                "type": payment.payment_type.value
            },
            "booking_status": booking.status.value,
            "remaining_balance": float(wallet.balance.amount)
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/bookings/{booking_id}/pay-balance")
async def pay_balance(booking_id: str):
    """Paye le solde d'une réservation avec le wallet du client."""
    if booking_id not in bookings_storage:
        raise HTTPException(status_code=404, detail="Réservation non trouvée")
    
    booking = bookings_storage[booking_id]
    wallet = get_customer_wallet(booking.customer_id.value)
    
    if not wallet.has_sufficient_funds(booking.balance_amount):
        return {
            "success": False,
            "message": f"Fonds insuffisants. Solde: {wallet.balance.amount}€, Requis: {booking.balance_amount.amount}€",
            "required_amount": float(booking.balance_amount.amount),
            "current_balance": float(wallet.balance.amount),
            "shortfall": float(booking.balance_amount.amount - wallet.balance.amount)
        }
    
    try:
        wallet.debit(
            amount=booking.balance_amount,
            reason=f"Solde réservation {booking_id}"
        )
        
        payment = booking.confirm_booking()
        
        return {
            "success": True,
            "message": "Réservation confirmée avec succès",
            "payment": {
                "id": payment.id.value,
                "amount": float(payment.amount.amount),
                "type": payment.payment_type.value
            },
            "booking_status": booking.status.value,
            "remaining_balance": float(wallet.balance.amount)
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/admin/stats")
async def get_admin_stats():
    """Statistiques temporaires pour l'admin."""
    return {
        "customers_count": len(customers_storage),
        "active_customers": len([c for c in customers_storage.values() if c.is_active]),
        "wallets_count": len(wallets_storage),
        "bookings_count": len(bookings_storage),
        "confirmed_bookings": len([b for b in bookings_storage.values() if b.status == BookingStatus.CONFIRMED]),
        "room_types_available": 3,
        "api_status": "functional_with_domain_objects"
    }