"""
API principale de l'application XYZ Hôtel.
Point d'entrée pour l'infrastructure HTTP.
"""

from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Dict, Optional
from decimal import Decimal
import uuid
from datetime import datetime, date
from sqlalchemy.orm import Session

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

from ..database.connection import get_database_session
from ..database.models import (
    CustomerModel, WalletModel, TransactionModel, 
    BookingModel, PaymentModel
)

app = FastAPI(
    title="XYZ Hotel API",
    description="reservation de nuits",
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


def model_to_domain_customer(customer_model: CustomerModel) -> Customer:
    """Convertit un modèle CustomerModel en entité domaine Customer."""
    return Customer(
        id=CustomerId(str(customer_model.id)),
        full_name=FullName(customer_model.full_name),
        email=Email(customer_model.email),
        phone_number=PhoneNumber(customer_model.phone_number)
    )

def model_to_domain_wallet(wallet_model: WalletModel) -> Wallet:
    """Convertit un modèle WalletModel en entité domaine Wallet."""
    return Wallet(
        id=WalletId(wallet_model.id),
        customer_id=CustomerId(str(wallet_model.customer_id)),
        balance=Money(wallet_model.balance_amount, Currency(wallet_model.balance_currency))
    )

def get_or_create_wallet(customer_id: str, db: Session) -> Wallet:
    """Récupère ou crée le wallet d'un client."""
    wallet_model = db.query(WalletModel).filter(WalletModel.customer_id == int(customer_id)).first()
    
    if wallet_model:
        return model_to_domain_wallet(wallet_model)
    
    new_wallet_model = WalletModel(
        customer_id=int(customer_id),
        balance_amount=Decimal("0.00"),
        balance_currency="EUR"
    )
    
    db.add(new_wallet_model)
    db.commit()
    db.refresh(new_wallet_model)
    
    return model_to_domain_wallet(new_wallet_model)

def save_wallet_transaction(wallet: Wallet, transaction: Transaction, db: Session):
    """Sauvegarde une transaction wallet en base."""
    transaction_model = TransactionModel(
        wallet_id=int(wallet.id.value),
        amount=transaction.amount.amount,
        currency=transaction.amount.currency.value,
        transaction_type=transaction.transaction_type,
        reason=transaction.reason,
        processed_at=transaction.processed_at,
        created_at=transaction.created_at
    )
    
    db.add(transaction_model)
    
    wallet_model = db.query(WalletModel).filter(WalletModel.id == int(wallet.id.value)).first()
    if wallet_model:
        wallet_model.balance_amount = wallet.balance.amount
        wallet_model.updated_at = datetime.now()
    
    db.commit()

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
            "wallets": "/customers/{id}/wallet",
            "bookings": "/bookings",
            "health": "/health"
        }
    }

@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "domain_objects": "functional"
    }


@app.post("/customers", response_model=CustomerResponse, status_code=201)
async def create_customer(customer_data: CustomerCreateRequest, db: Session = Depends(get_database_session)):
    try:
        existing_customer = db.query(CustomerModel).filter(CustomerModel.email == customer_data.email).first()
        if existing_customer:
            raise HTTPException(status_code=400, detail="Email déjà utilisé")
        
        customer_model = CustomerModel(
            full_name=customer_data.full_name,
            email=customer_data.email,
            phone_number=customer_data.phone_number,
            is_active=True
        )
        
        db.add(customer_model)
        db.commit()
        db.refresh(customer_model)
        
        customer = model_to_domain_customer(customer_model)
        
        return CustomerResponse(
            id=customer.id.value,
            full_name=customer.full_name.value,
            email=customer.email.value,
            phone_number=customer.phone_number.value,
            is_active=customer.is_active,
            created_at=customer_model.created_at.isoformat()
        )
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/customers", response_model=List[CustomerResponse])
async def list_customers(db: Session = Depends(get_database_session)):
    customers = db.query(CustomerModel).all()
    return [
        CustomerResponse(
            id=str(customer.id),
            full_name=customer.full_name,
            email=customer.email,
            phone_number=customer.phone_number,
            is_active=customer.is_active,
            created_at=customer.created_at.isoformat()
        )
        for customer in customers
    ]

@app.get("/customers/{customer_id}", response_model=CustomerResponse)
async def get_customer(customer_id: str, db: Session = Depends(get_database_session)):
    customer = db.query(CustomerModel).filter(CustomerModel.id == int(customer_id)).first()
    if not customer:
        raise HTTPException(status_code=404, detail="Client non trouvé")
    
    return CustomerResponse(
        id=str(customer.id),
        full_name=customer.full_name,
        email=customer.email,
        phone_number=customer.phone_number,
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
async def get_customer_wallet_info(customer_id: str, db: Session = Depends(get_database_session)):
    """Récupère les informations du wallet d'un client."""
    customer = db.query(CustomerModel).filter(CustomerModel.id == int(customer_id)).first()
    if not customer:
        raise HTTPException(status_code=404, detail="Client non trouvé")
    
    wallet = get_or_create_wallet(customer_id, db)
    wallet_model = db.query(WalletModel).filter(WalletModel.id == int(wallet.id.value)).first()
    
    return WalletResponse(
        id=str(wallet.id.value),
        customer_id=wallet.customer_id.value,
        balance=float(wallet.balance.amount),
        currency=wallet.balance.currency.value,
        last_updated=wallet_model.updated_at.isoformat()
    )

@app.post("/customers/{customer_id}/wallet/credit")
async def credit_wallet(customer_id: str, credit_request: WalletCreditRequest, db: Session = Depends(get_database_session)):
    """Crédite le wallet d'un client."""
    customer = db.query(CustomerModel).filter(CustomerModel.id == int(customer_id)).first()
    if not customer:
        raise HTTPException(status_code=404, detail="Client non trouvé")
    
    if credit_request.amount <= 0:
        raise HTTPException(status_code=400, detail="Le montant doit être positif")
    
    wallet = get_or_create_wallet(customer_id, db)
    
    try:
        transaction = wallet.credit(
            amount=Money(Decimal(str(credit_request.amount)), Currency.EUR),
            reason=credit_request.reason
        )
        
        save_wallet_transaction(wallet, transaction, db)
        
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

@app.get("/wallets/{wallet_id}/transactions")
async def get_wallet_transactions(wallet_id: str, db: Session = Depends(get_database_session)):
    """Récupère l'historique des transactions d'un wallet."""
    wallet_model = db.query(WalletModel).filter(WalletModel.id == int(wallet_id)).first()
    if not wallet_model:
        raise HTTPException(status_code=404, detail="Wallet non trouvé")
    
    transactions = db.query(TransactionModel).filter(TransactionModel.wallet_id == int(wallet_id)).all()
    
    return {
        "wallet_id": wallet_id,
        "transactions": [
            {
                "id": str(t.id),
                "type": t.transaction_type,
                "amount": float(t.amount),
                "reason": t.reason,
                "processed_at": t.created_at.isoformat()
            }
            for t in transactions
        ]
    }


@app.post("/bookings", response_model=BookingResponse, status_code=201)
async def create_booking(booking_request: BookingCreateRequest, db: Session = Depends(get_database_session)):
    """Crée une nouvelle réservation."""
    customer = db.query(CustomerModel).filter(CustomerModel.id == int(booking_request.customer_id)).first()
    if not customer:
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
    
    booking_model = BookingModel(
        customer_id=int(booking_request.customer_id),
        room_type=booking.room_type.value,
        room_quantity=booking.room_quantity,
        check_in_date=booking.stay.check_in.value,
        check_out_date=booking.stay.check_out,
        total_amount=float(booking.total_amount.amount),
        deposit_amount=float(booking.deposit_amount.amount),
        balance_amount=float(booking.balance_amount.amount),
        status=booking.status.value
    )
    db.add(booking_model)
    db.commit()
    db.refresh(booking_model)
    
    return BookingResponse(
        id=str(booking_model.id),
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
        created_at=booking_model.created_at.isoformat()
    )

@app.get("/bookings", response_model=List[BookingResponse])
async def list_bookings(db: Session = Depends(get_database_session)):
    """Liste toutes les réservations."""
    bookings_models = db.query(BookingModel).all()
    return [
        BookingResponse(
            id=str(booking_model.id),
            customer_id=str(booking_model.customer_id),
            room_type=booking_model.room_type,
            room_quantity=booking_model.room_quantity,
            check_in_date=booking_model.check_in_date.isoformat(),
            check_out_date=booking_model.check_out_date.isoformat(),
            total_amount=float(booking_model.total_amount),
            deposit_amount=float(booking_model.deposit_amount),
            balance_amount=float(booking_model.balance_amount),
            status=booking_model.status,
            total_paid=0.0,  # TODO: Calculer depuis les paiements
            created_at=booking_model.created_at.isoformat()
        )
        for booking_model in bookings_models
    ]

@app.get("/customers/{customer_id}/bookings", response_model=List[BookingResponse])
async def get_customer_bookings(customer_id: str, db: Session = Depends(get_database_session)):
    """Récupère les réservations d'un client."""
    customer = db.query(CustomerModel).filter(CustomerModel.id == int(customer_id)).first()
    if not customer:
        raise HTTPException(status_code=404, detail="Client non trouvé")
    
    bookings_models = db.query(BookingModel).filter(BookingModel.customer_id == int(customer_id)).all()
    
    return [
        BookingResponse(
            id=str(booking_model.id),
            customer_id=str(booking_model.customer_id),
            room_type=booking_model.room_type,
            room_quantity=booking_model.room_quantity,
            check_in_date=booking_model.check_in_date.isoformat(),
            check_out_date=booking_model.check_out_date.isoformat(),
            total_amount=float(booking_model.total_amount),
            deposit_amount=float(booking_model.deposit_amount),
            balance_amount=float(booking_model.balance_amount),
            status=booking_model.status,
            total_paid=0.0,  # TODO: Calculer depuis les paiements
            created_at=booking_model.created_at.isoformat()
        )
        for booking_model in bookings_models
    ]

@app.post("/bookings/{booking_id}/pay-deposit")
async def pay_deposit(booking_id: str, db: Session = Depends(get_database_session)):
    """Paye l'acompte d'une réservation avec le wallet du client."""
    booking_model = db.query(BookingModel).filter(BookingModel.id == int(booking_id)).first()
    if not booking_model:
        raise HTTPException(status_code=404, detail="Réservation non trouvée")
    
    wallet = get_or_create_wallet(str(booking_model.customer_id), db)
    deposit_amount = Money(Decimal(str(booking_model.deposit_amount)), Currency.EUR)
    
    if not wallet.has_sufficient_funds(deposit_amount):
        return {
            "success": False,
            "message": f"Fonds insuffisants. Solde: {wallet.balance.amount}€, Requis: {deposit_amount.amount}€",
            "required_amount": float(deposit_amount.amount),
            "current_balance": float(wallet.balance.amount),
            "shortfall": float(deposit_amount.amount - wallet.balance.amount)
        }
    
    try:
        transaction = wallet.debit(
            amount=deposit_amount,
            reason=f"Acompte réservation {booking_id}"
        )
        
        save_wallet_transaction(wallet, transaction, db)
        
        payment_model = PaymentModel(
            booking_id=int(booking_id),
            amount=float(deposit_amount.amount),
            payment_type="DEPOSIT"
        )
        db.add(payment_model)
        db.commit()
        
        return {
            "success": True,
            "message": "Acompte payé avec succès",
            "payment": {
                "id": str(payment_model.id),
                "amount": float(deposit_amount.amount),
                "type": "DEPOSIT"
            },
            "booking_status": "CONFIRMED",
            "remaining_balance": float(wallet.balance.amount)
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/bookings/{booking_id}/pay-balance")
async def pay_balance(booking_id: str, db: Session = Depends(get_database_session)):
    """Paye le solde d'une réservation avec le wallet du client."""
    booking_model = db.query(BookingModel).filter(BookingModel.id == int(booking_id)).first()
    if not booking_model:
        raise HTTPException(status_code=404, detail="Réservation non trouvée")
    
    wallet = get_or_create_wallet(str(booking_model.customer_id), db)
    balance_amount = Money(Decimal(str(booking_model.balance_amount)), Currency.EUR)
    
    if not wallet.has_sufficient_funds(balance_amount):
        return {
            "success": False,
            "message": f"Fonds insuffisants. Solde: {wallet.balance.amount}€, Requis: {balance_amount.amount}€",
            "required_amount": float(balance_amount.amount),
            "current_balance": float(wallet.balance.amount),
            "shortfall": float(balance_amount.amount - wallet.balance.amount)
        }
    
    try:
        transaction = wallet.debit(
            amount=balance_amount,
            reason=f"Solde réservation {booking_id}"
        )
        
        save_wallet_transaction(wallet, transaction, db)
        
        payment_model = PaymentModel(
            booking_id=int(booking_id),
            amount=float(balance_amount.amount),
            payment_type="BALANCE"
        )
        db.add(payment_model)
        
        booking_model.status = "CONFIRMED"
        db.commit()
        
        return {
            "success": True,
            "message": "Réservation confirmée avec succès",
            "payment": {
                "id": str(payment_model.id),
                "amount": float(balance_amount.amount),
                "type": "BALANCE"
            },
            "booking_status": "CONFIRMED",
            "remaining_balance": float(wallet.balance.amount)
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/admin/stats")
async def get_admin_stats(db: Session = Depends(get_database_session)):
    """Statistiques temporaires pour l'admin."""
    customers_count = db.query(CustomerModel).count()
    active_customers = db.query(CustomerModel).filter(CustomerModel.is_active == True).count()
    wallets_count = db.query(WalletModel).count()
    bookings_count = db.query(BookingModel).count()
    confirmed_bookings = db.query(BookingModel).filter(BookingModel.status == "CONFIRMED").count()
    
    return {
        "customers_count": customers_count,
        "active_customers": active_customers,
        "wallets_count": wallets_count,
        "bookings_count": bookings_count,
        "confirmed_bookings": confirmed_bookings,
        "room_types_available": 3,
        "api_status": "functional_with_database"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)