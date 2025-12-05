#!/usr/bin/env python3

import sys
import os
from datetime import datetime, date, timedelta
from decimal import Decimal

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.domain.main import Money, Currency, CustomerId, Email, FullName, PhoneNumber
from src.domain.customer_management.customer import Customer
from src.domain.wallet_management.wallet import Wallet, Transaction
from src.domain.wallet_management.money import WalletId, TransactionId
from src.domain.booking_management.booking import (
    Booking, BookingId, BookingStatus, Payment, PaymentType, PaymentId,
    Stay, CheckInDate, NumberOfNights
)
from src.domain.room_management.room_types import RoomTypeEnum, RoomId

from src.infrastructure.database.connection import SessionLocal
from src.infrastructure.database.models import (
    CustomerModel, WalletModel, BookingModel, TransactionModel, PaymentModel
)


class HotelDomainService:

    def __init__(self):
        self.db = SessionLocal()

    def create_customer_entity(self, full_name: str, email: str, phone_number: str):
        try:
            customer_model = CustomerModel(
                full_name=full_name,
                email=email,
                phone_number=phone_number
            )
            self.db.add(customer_model)
            self.db.commit()
            self.db.refresh(customer_model)

            customer = Customer(
                id=CustomerId(str(customer_model.id)),
                full_name=FullName(full_name),
                email=Email(email),
                phone_number=PhoneNumber(phone_number)
            )

            return customer, customer_model
        except Exception as e:
            self.db.rollback()
            raise e

    def get_customer_entity(self, customer_id: int):
        customer_model = self.db.query(CustomerModel).filter(
            CustomerModel.id == customer_id
        ).first()

        if not customer_model:
            raise ValueError(f"Client {customer_id} non trouvé")

        return Customer(
            id=CustomerId(str(customer_model.id)),
            full_name=FullName(customer_model.full_name),
            email=Email(customer_model.email),
            phone_number=PhoneNumber(customer_model.phone_number)
        ), customer_model

    def get_or_create_wallet_entity(self, customer_id: int):
        wallet_model = self.db.query(WalletModel).filter(
            WalletModel.customer_id == customer_id
        ).first()

        if not wallet_model:
            wallet_model = WalletModel(customer_id=customer_id)
            self.db.add(wallet_model)
            self.db.commit()
            self.db.refresh(wallet_model)

        transactions = self.db.query(TransactionModel).filter(
            TransactionModel.wallet_id == wallet_model.id
        ).all()

        transaction_entities = [
            Transaction(
                id=TransactionId(str(t.id)),
                wallet_id=WalletId(str(wallet_model.id)),
                amount=Money(Decimal(str(t.amount)), Currency.EUR),
                reason=t.reason,
                transaction_type=t.transaction_type,
                created_at=t.created_at
            )
            for t in transactions
        ]

        wallet = Wallet(
            id=WalletId(str(wallet_model.id)),
            customer_id=CustomerId(str(customer_id)),
            balance=Money(Decimal(str(wallet_model.balance_amount)), Currency.EUR),
            transactions=transaction_entities
        )

        return wallet, wallet_model

    def credit_wallet_entity(self, customer_id: int, amount: float, reason: str):
        wallet_entity, wallet_model = self.get_or_create_wallet_entity(customer_id)

        money = Money(Decimal(str(amount)), Currency.EUR)
        transaction = wallet_entity.credit(money, reason)

        wallet_model.balance_amount = float(wallet_entity.balance.amount)

        transaction_model = TransactionModel(
            wallet_id=wallet_model.id,
            amount=float(transaction.amount.amount),
            reason=transaction.reason,
            transaction_type=transaction.transaction_type
        )
        self.db.add(transaction_model)
        self.db.commit()
        
        wallet_model.balance_amount = float(wallet_entity.balance.amount)
        self.db.commit()

        return transaction, transaction_model

    def create_booking_entity(self, customer_id: int, room_type: str, room_quantity: int,
                             check_in_date: str, number_of_nights: int):
        check_in_obj = datetime.strptime(check_in_date, "%Y-%m-%d").date()
        check_in_vo = CheckInDate(check_in_obj)
        stay = Stay(check_in_vo, NumberOfNights(number_of_nights))

        room_type_upper = room_type.upper()
        room_type_enum = RoomTypeEnum(room_type_upper)
        price = {
            "STANDARD": 50,
            "SUPERIOR": 100,
            "SUITE": 200
        }.get(room_type_upper, 50)

        total_amount = Decimal(str(price * room_quantity * number_of_nights))
        deposit = total_amount * Decimal("0.5")
        balance = total_amount * Decimal("0.5")

        booking_model = BookingModel(
            customer_id=customer_id,
            room_type=room_type_upper,
            room_quantity=room_quantity,
            check_in_date=check_in_obj,
            check_out_date=check_in_obj + timedelta(days=number_of_nights),
            total_amount=float(total_amount),
            deposit_amount=float(deposit),
            balance_amount=float(balance),
            status="PENDING"
        )
        self.db.add(booking_model)
        self.db.commit()
        self.db.refresh(booking_model)

        booking = Booking(
            id=BookingId(str(booking_model.id)),
            customer_id=CustomerId(str(customer_id)),
            room_type=room_type_enum,
            room_quantity=room_quantity,
            stay=stay,
            total_amount=Money(total_amount, Currency.EUR),
            status=BookingStatus(booking_model.status)
        )

        return booking, booking_model

    def pay_deposit_entity(self, booking_id: int):
        booking_model = self.db.query(BookingModel).filter(
            BookingModel.id == booking_id
        ).first()

        if not booking_model:
            raise ValueError(f"Réservation {booking_id} non trouvée")

        check_in_obj = datetime.combine(booking_model.check_in_date, datetime.min.time()).date()
        check_out_obj = datetime.combine(booking_model.check_out_date, datetime.min.time()).date()
        number_of_nights = (check_out_obj - check_in_obj).days
        
        check_in_vo = CheckInDate(check_in_obj)
        stay = Stay(check_in_vo, NumberOfNights(number_of_nights))

        payments_models = self.db.query(PaymentModel).filter(
            PaymentModel.booking_id == booking_id
        ).all()
        
        payments = [
            Payment(
                id=PaymentId(str(p.id)),
                booking_id=BookingId(str(p.booking_id)),
                amount=Money(Decimal(str(p.amount)), Currency.EUR),
                payment_type=PaymentType(p.payment_type),
                is_processed=p.is_processed,
                processed_at=p.processed_at,
                created_at=p.created_at
            )
            for p in payments_models
        ]

        booking = Booking(
            id=BookingId(str(booking_model.id)),
            customer_id=CustomerId(str(booking_model.customer_id)),
            room_type=RoomTypeEnum(booking_model.room_type),
            room_quantity=booking_model.room_quantity,
            stay=stay,
            total_amount=Money(Decimal(str(booking_model.total_amount)), Currency.EUR),
            status=BookingStatus(booking_model.status),
            payments=payments
        )

        payment = booking.pay_deposit()

        wallet, wallet_model = self.get_or_create_wallet_entity(booking_model.customer_id)
        debit_transaction = wallet.debit(payment.amount, f"Acompte reservation {booking_id}")

        payment_model = PaymentModel(
            booking_id=booking_id,
            amount=float(payment.amount.amount),
            payment_type=payment.payment_type.value,
            is_processed=payment.is_processed,
            processed_at=payment.processed_at
        )
        self.db.add(payment_model)

        transaction_model = TransactionModel(
            wallet_id=wallet_model.id,
            amount=float(debit_transaction.amount.amount),
            reason=debit_transaction.reason,
            transaction_type=debit_transaction.transaction_type
        )
        self.db.add(transaction_model)

        booking_model.status = booking.status.value
        wallet_model.balance_amount = float(wallet.balance.amount)

        self.db.commit()

        return payment, payment_model

    def pay_balance_entity(self, booking_id: int):
        booking_model = self.db.query(BookingModel).filter(
            BookingModel.id == booking_id
        ).first()

        if not booking_model:
            raise ValueError(f"Réservation {booking_id} non trouvée")

        check_in_obj = datetime.combine(booking_model.check_in_date, datetime.min.time()).date()
        check_out_obj = datetime.combine(booking_model.check_out_date, datetime.min.time()).date()
        number_of_nights = (check_out_obj - check_in_obj).days
        
        check_in_vo = CheckInDate(check_in_obj)
        stay = Stay(check_in_vo, NumberOfNights(number_of_nights))

        payments_models = self.db.query(PaymentModel).filter(
            PaymentModel.booking_id == booking_id
        ).all()
        
        payments = [
            Payment(
                id=PaymentId(str(p.id)),
                booking_id=BookingId(str(p.booking_id)),
                amount=Money(Decimal(str(p.amount)), Currency.EUR),
                payment_type=PaymentType(p.payment_type),
                is_processed=p.is_processed,
                processed_at=p.processed_at,
                created_at=p.created_at
            )
            for p in payments_models
        ]

        booking = Booking(
            id=BookingId(str(booking_model.id)),
            customer_id=CustomerId(str(booking_model.customer_id)),
            room_type=RoomTypeEnum(booking_model.room_type),
            room_quantity=booking_model.room_quantity,
            stay=stay,
            total_amount=Money(Decimal(str(booking_model.total_amount)), Currency.EUR),
            status=BookingStatus(booking_model.status),
            payments=payments
        )

        payment = booking.confirm_booking()

        wallet, wallet_model = self.get_or_create_wallet_entity(booking_model.customer_id)
        debit_transaction = wallet.debit(payment.amount, f"Solde reservation {booking_id}")

        payment_model = PaymentModel(
            booking_id=booking_id,
            amount=float(payment.amount.amount),
            payment_type=payment.payment_type.value,
            is_processed=payment.is_processed,
            processed_at=payment.processed_at
        )
        self.db.add(payment_model)

        transaction_model = TransactionModel(
            wallet_id=wallet_model.id,
            amount=float(debit_transaction.amount.amount),
            reason=debit_transaction.reason,
            transaction_type=debit_transaction.transaction_type
        )
        self.db.add(transaction_model)

        booking_model.status = booking.status.value
        wallet_model.balance_amount = float(wallet.balance.amount)

        self.db.commit()

        return payment, payment_model

    def get_stats(self):
        customers_count = self.db.query(CustomerModel).count()
        active_customers = self.db.query(CustomerModel).filter(CustomerModel.is_active == True).count()
        wallets_count = self.db.query(WalletModel).count()
        bookings_count = self.db.query(BookingModel).count()
        confirmed_bookings = self.db.query(BookingModel).filter(BookingModel.status == "CONFIRMED").count()

        return {
            "customers_count": customers_count,
            "active_customers": active_customers,
            "wallets_count": wallets_count,
            "bookings_count": bookings_count,
            "confirmed_bookings": confirmed_bookings
        }

    def list_customers(self):
        customers = self.db.query(CustomerModel).all()
        return customers

    def list_bookings(self):
        bookings = self.db.query(BookingModel).all()
        return bookings


domain_service = HotelDomainService()


def clear_screen():
    os.system('clear' if os.name == 'posix' else 'cls')


def print_header(title):
    print("\n" + "=" * 60)
    print(f"{title}")
    print("=" * 60)


def main_menu():
    while True:
        clear_screen()
        print_header("XYZ HOTEL - MENU PRINCIPAL")
        print("""
  1. Gestion des Clients
  2. Gestion du Portefeuille
  3. Gestion des Réservations
  4. Admin - Statistiques
  5. Démo Complète
  0. Quitter
        """)
        choice = input("Choisissez une option (0-5): ").strip()

        if choice == "1":
            clients_menu()
        elif choice == "2":
            wallets_menu()
        elif choice == "3":
            reservations_menu()
        elif choice == "4":
            admin_menu()
        elif choice == "5":
            run_demo()
        elif choice == "0":
            print("\nAu revoir !\n")
            break
        else:
            print("Option invalide !")
            input("Appuyez sur Entrée pour continuer...")


def clients_menu():
    while True:
        clear_screen()
        print_header("GESTION DES CLIENTS")
        print("""
  1. Créer un nouveau client
  2. Lister tous les clients
  0. Retour au menu principal
        """)
        choice = input("Choisissez une option: ").strip()

        if choice == "1":
            print_header("CREATION D'UN CLIENT")
            name = input("Nom complet: ").strip()
            email = input("Email: ").strip()
            phone = input("Téléphone: ").strip()

            try:
                customer, model = domain_service.create_customer_entity(name, email, phone)
                print(f"\nClient créé avec succès !")
                print(f"ID: {model.id}")
                print(f"Nom: {customer.full_name.value}")
                print(f"Email: {customer.email.value}")
            except Exception as e:
                print(f"\n✗ Erreur: {e}")

            input("\nAppuyez sur Entrée pour continuer...")

        elif choice == "2":
            print_header("LISTE DES CLIENTS")
            customers = domain_service.list_customers()
            if not customers:
                print("Aucun client enregistré.")
            else:
                for c in customers:
                    status = "Actif" if c.is_active else "Inactif"
                    print(f"ID: {c.id} | {c.full_name} | {c.email} | {status}")
            input("\nAppuyez sur Entrée pour continuer...")

        elif choice == "0":
            break
        else:
            print("Option invalide !")
            input("Appuyez sur Entrée pour continuer...")


def wallets_menu():
    while True:
        clear_screen()
        print_header("GESTION DU PORTEFEUILLE")
        print("""
  1. Créditer un portefeuille
  2. Voir le solde d'un portefeuille
  0. Retour au menu principal
        """)
        choice = input("Choisissez une option: ").strip()

        if choice == "1":
            print_header("CREDITER UN PORTEFEUILLE")
            customer_id = input("ID du client: ").strip()
            amount = input("Montant à créditer (EUR): ").strip()

            try:
                transaction, _ = domain_service.credit_wallet_entity(int(customer_id), float(amount), "Credit manuel")
                wallet, _ = domain_service.get_or_create_wallet_entity(int(customer_id))
                print(f"\nCrédit effectué !")
                print(f"Montant: {transaction.amount.amount} EUR")
                print(f"Nouveau solde: {wallet.balance.amount} EUR")
            except Exception as e:
                print(f"\n✗ Erreur: {e}")

            input("\nAppuyez sur Entrée pour continuer...")

        elif choice == "2":
            print_header("SOLDE DU PORTEFEUILLE")
            customer_id = input("ID du client: ").strip()

            try:
                wallet, _ = domain_service.get_or_create_wallet_entity(int(customer_id))
                print(f"\nSolde du portefeuille:")
                print(f"Client ID: {customer_id}")
                print(f"Solde: {wallet.balance.amount} EUR")
                print(f"Nombre de transactions: {len(wallet.transactions)}")
            except Exception as e:
                print(f"\n✗ Erreur: {e}")

            input("\nAppuyez sur Entrée pour continuer...")

        elif choice == "0":
            break
        else:
            print("Option invalide !")
            input("Appuyez sur Entrée pour continuer...")


def reservations_menu():
    while True:
        clear_screen()
        print_header("GESTION DES RESERVATIONS")
        print("""
  1. Créer une réservation
  2. Payer l'acompte (50%)
  3. Payer le solde (50%)
  4. Lister les réservations
  0. Retour au menu principal
        """)
        choice = input("Choisissez une option: ").strip()

        if choice == "1":
            print_header("CREATION D'UNE RESERVATION")
            customer_id = input("ID du client: ").strip()
            print("\nTypes de chambres disponibles:")
            print("- standard (50 EUR/nuit)")
            print("- superior (100 EUR/nuit)")
            print("- suite (200 EUR/nuit)")
            room_type = input("Type de chambre: ").strip().lower()
            room_qty = input("Nombre de chambres: ").strip()
            check_in = input("Date de check-in (YYYY-MM-DD): ").strip()
            nights = input("Nombre de nuits: ").strip()

            try:
                booking, model = domain_service.create_booking_entity(
                    int(customer_id), room_type, int(room_qty), check_in, int(nights)
                )
                print(f"\nRéservation créée !")
                print(f"ID: {model.id}")
                print(f"Montant total: {booking.total_amount.amount} EUR")
                print(f"Acompte (50%): {booking.deposit_amount.amount} EUR")
                print(f"Solde (50%): {booking.balance_amount.amount} EUR")
            except Exception as e:
                print(f"\n✗ Erreur: {e}")

            input("\nAppuyez sur Entrée pour continuer...")

        elif choice == "2":
            print_header("PAIEMENT DE L'ACOMPTE")
            booking_id = input("ID de la réservation: ").strip()

            try:
                payment, _ = domain_service.pay_deposit_entity(int(booking_id))
                print(f"\nAcompte payé !")
                print(f"Montant: {payment.amount.amount} EUR")
                print(f"Type: {payment.payment_type.value}")
            except Exception as e:
                print(f"\n✗ Erreur: {e}")

            input("\nAppuyez sur Entrée pour continuer...")

        elif choice == "3":
            print_header("PAIEMENT DU SOLDE")
            booking_id = input("ID de la réservation: ").strip()

            try:
                payment, _ = domain_service.pay_balance_entity(int(booking_id))
                print(f"\nSolde payé - Réservation confirmée !")
                print(f"Montant: {payment.amount.amount} EUR")
                print(f"Type: {payment.payment_type.value}")
            except Exception as e:
                print(f"\n✗ Erreur: {e}")

            input("\nAppuyez sur Entrée pour continuer...")

        elif choice == "4":
            print_header("LISTE DES RESERVATIONS")
            bookings = domain_service.list_bookings()
            if not bookings:
                print("Aucune réservation enregistrée.")
            else:
                for b in bookings:
                    print(f"ID: {b.id} | Client: {b.customer_id} | Montant: {b.total_amount} EUR | Statut: {b.status}")
            input("\nAppuyez sur Entrée pour continuer...")

        elif choice == "0":
            break
        else:
            print("Option invalide !")
            input("Appuyez sur Entrée pour continuer...")


def admin_menu():
    clear_screen()
    print_header("ADMIN - STATISTIQUES")
    try:
        stats = domain_service.get_stats()
        print(f"\n  Clients total: {stats['customers_count']}")
        print(f"Clients actifs: {stats['active_customers']}")
        print(f"Portefeuilles: {stats['wallets_count']}")
        print(f"Réservations total: {stats['bookings_count']}")
        print(f"Réservations confirmées: {stats['confirmed_bookings']}")
    except Exception as e:
        print(f"Erreur: {e}")

    input("\nAppuyez sur Entrée pour continuer...")


def run_demo():
    clear_screen()
    print_header("DEMONSTRATION COMPLÈTE")
    print("\nExécution du workflow de démonstration...\n")

    try:
        print("1. Création d'un client...")
        customer, customer_model = domain_service.create_customer_entity(
            "Demo User",
            f"demo_{datetime.now().strftime('%H%M%S')}@example.com",
            "+33123456789"
        )
        client_id = customer_model.id
        print(f"Client créé: #{client_id} - {customer.full_name.value}\n")

        print("2. Crédit du portefeuille...")
        transaction, _ = domain_service.credit_wallet_entity(client_id, 500.0, "Demonstration")
        wallet, _ = domain_service.get_or_create_wallet_entity(client_id)
        print(f"Portefeuille crédité: {wallet.balance.amount} EUR\n")

        print("3. Création d'une réservation...")
        booking, booking_model = domain_service.create_booking_entity(
            client_id, "standard", 1, "2025-12-20", 2
        )
        booking_id = booking_model.id
        print(f"Réservation créée: #{booking_id}")
        print(f"   Montant total: {booking.total_amount.amount} EUR")
        print(f"   Acompte: {booking.deposit_amount.amount} EUR\n")

        print("4. Paiement de l'acompte...")
        payment_deposit, _ = domain_service.pay_deposit_entity(booking_id)
        wallet, _ = domain_service.get_or_create_wallet_entity(client_id)
        print(f"Acompte payé: {payment_deposit.amount.amount} EUR")
        print(f"   Solde restant: {wallet.balance.amount} EUR\n")

        print("5. Paiement du solde...")
        payment_balance, _ = domain_service.pay_balance_entity(booking_id)
        wallet, _ = domain_service.get_or_create_wallet_entity(client_id)
        print(f"Solde payé: {payment_balance.amount.amount} EUR")
        print(f"   Réservation confirmée !\n")

        print(f"Récapitulatif final:")
        print(f"Solde wallet final: {wallet.balance.amount} EUR\n")
        print("Démonstration terminée avec succès !")

    except Exception as e:
        print(f"✗ Erreur pendant la démo: {e}")

    input("\nAppuyez sur Entrée pour continuer...")


if __name__ == "__main__":
    try:
        main_menu()
    except KeyboardInterrupt:
        print("\n\nAu revoir !")
        sys.exit(0)
