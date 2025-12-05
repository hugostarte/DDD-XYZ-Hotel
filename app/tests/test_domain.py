import pytest
from decimal import Decimal
from datetime import date, datetime, timedelta

from src.domain.main import (
    Money, Currency, CustomerId, Email, FullName, PhoneNumber
)
from src.domain.wallet_management.money import WalletId, TransactionId
from src.domain.booking_management.booking import (
    Booking, BookingId, BookingStatus, Payment, PaymentType, PaymentId,
    CheckInDate, NumberOfNights, Stay
)
from src.domain.room_management.room_types import RoomTypeEnum
from src.domain.customer_management.customer import Customer
from src.domain.wallet_management.wallet import Wallet, Transaction


class TestMoney:
    def test_creation_money_valid(self):
        money = Money(Decimal("100.50"), Currency.EUR)
        assert money.amount == Decimal("100.50")
        assert money.currency == Currency.EUR
    
    def test_creation_money_zero(self):
        money = Money(Decimal("0"), Currency.EUR)
        assert money.amount == Decimal("0")
    
    def test_creation_money_negative_raises_error(self):
        with pytest.raises(ValueError):
            Money(Decimal("-10"), Currency.EUR)
    
    def test_addition_money(self):
        money1 = Money(Decimal("100"), Currency.EUR)
        money2 = Money(Decimal("50"), Currency.EUR)
        result = money1.add(money2)
        assert result.amount == Decimal("150")
        assert result.currency == Currency.EUR
    
    def test_subtraction_money(self):
        money1 = Money(Decimal("100"), Currency.EUR)
        money2 = Money(Decimal("30"), Currency.EUR)
        result = money1.subtract(money2)
        assert result.amount == Decimal("70")
    
    def test_subtraction_insufficient_funds_raises_error(self):
        money1 = Money(Decimal("50"), Currency.EUR)
        money2 = Money(Decimal("100"), Currency.EUR)
        with pytest.raises(ValueError):
            money1.subtract(money2)
    
    def test_multiplication_money(self):
        money = Money(Decimal("25"), Currency.EUR)
        result = money.multiply(Decimal("4"))
        assert result.amount == Decimal("100")
    
    def test_money_equality(self):
        money1 = Money(Decimal("100"), Currency.EUR)
        money2 = Money(Decimal("100"), Currency.EUR)
        assert money1 == money2


class TestCustomerId:
    def test_creation_valid_id(self):
        customer_id = CustomerId("123")
        assert customer_id.value == "123"
    
    def test_creation_empty_id_raises_error(self):
        with pytest.raises(ValueError):
            CustomerId("")
    
    def test_equality(self):
        id1 = CustomerId("123")
        id2 = CustomerId("123")
        id3 = CustomerId("456")
        
        assert id1 == id2
        assert id1 != id3
    
    def test_hashing(self):
        id1 = CustomerId("123")
        id2 = CustomerId("123")
        assert hash(id1) == hash(id2)


class TestCheckInDate:
    def test_creation_future_date(self):
        tomorrow = date.today() + timedelta(days=1)
        check_in = CheckInDate(tomorrow)
        assert check_in.value == tomorrow
    
    def test_creation_today_date(self):
        today = date.today()
        check_in = CheckInDate(today)
        assert check_in.value == today
    
    def test_creation_past_date_raises_error(self):
        yesterday = date.today() - timedelta(days=1)
        with pytest.raises(ValueError):
            CheckInDate(yesterday)


class TestNumberOfNights:
    def test_creation_valid_nights(self):
        nights = NumberOfNights(5)
        assert nights.value == 5
    
    def test_creation_one_night(self):
        nights = NumberOfNights(1)
        assert nights.value == 1
    
    def test_creation_zero_nights_raises_error(self):
        with pytest.raises(ValueError):
            NumberOfNights(0)
    
    def test_creation_negative_nights_raises_error(self):
        with pytest.raises(ValueError):
            NumberOfNights(-1)
    
    def test_creation_too_many_nights_raises_error(self):
        with pytest.raises(ValueError):
            NumberOfNights(366)


class TestStay:
    def test_creation_stay(self):
        tomorrow = date.today() + timedelta(days=1)
        check_in = CheckInDate(tomorrow)
        nights = NumberOfNights(3)
        stay = Stay(check_in, nights)
        
        assert stay.check_in == check_in
        assert stay.nights == nights
    
    def test_checkout_date_calculation(self):
        tomorrow = date.today() + timedelta(days=1)
        check_in = CheckInDate(tomorrow)
        nights = NumberOfNights(3)
        stay = Stay(check_in, nights)
        
        expected_checkout = tomorrow + timedelta(days=3)
        assert stay.check_out == expected_checkout


class TestCustomer:
    def test_creation_customer_valid(self):
        customer = Customer(
            id=CustomerId("1"),
            full_name=FullName("John Doe"),
            email=Email("john@example.com"),
            phone_number=PhoneNumber("+33123456789")
        )
        
        assert customer.id.value == "1"
        assert customer.full_name.value == "John Doe"
        assert customer.email.value == "john@example.com"
    
    def test_customer_update_contact_info(self):
        customer = Customer(
            id=CustomerId("1"),
            full_name=FullName("John Doe"),
            email=Email("john@example.com"),
            phone_number=PhoneNumber("+33123456789")
        )
        
        new_email = Email("newemail@example.com")
        new_phone = PhoneNumber("+33987654321")
        customer.update_contact_info(new_email, new_phone)
        
        assert customer.email == new_email
        assert customer.phone_number == new_phone
    
    def test_customer_suspend_reactivate(self):
        customer = Customer(
            id=CustomerId("1"),
            full_name=FullName("John Doe"),
            email=Email("john@example.com"),
            phone_number=PhoneNumber("+33123456789")
        )
        
        assert customer.is_active is True
        customer.suspend()
        assert customer.is_active is False
        customer.reactivate()
        assert customer.is_active is True


class TestWallet:
    def test_creation_wallet(self):
        wallet = Wallet(
            id=WalletId("wallet1"),
            customer_id=CustomerId("customer1")
        )
        
        assert wallet.id.value == "wallet1"
        assert wallet.customer_id.value == "customer1"
        assert wallet.balance.amount == Decimal("0")
    
    def test_wallet_credit(self):
        wallet = Wallet(
            id=WalletId("wallet1"),
            customer_id=CustomerId("customer1")
        )
        
        amount = Money(Decimal("100"), Currency.EUR)
        transaction = wallet.credit(amount, "Test credit")
        
        assert wallet.balance.amount == Decimal("100")
        assert transaction.amount.amount == Decimal("100")
        assert transaction.transaction_type == "CREDIT"
    
    def test_wallet_debit(self):
        wallet = Wallet(
            id=WalletId("wallet1"),
            customer_id=CustomerId("customer1")
        )
        
        credit_amount = Money(Decimal("100"), Currency.EUR)
        wallet.credit(credit_amount, "Initial credit")
        
        debit_amount = Money(Decimal("30"), Currency.EUR)
        transaction = wallet.debit(debit_amount, "Test debit")
        
        assert wallet.balance.amount == Decimal("70")
        assert transaction.amount.amount == Decimal("30")
        assert transaction.transaction_type == "DEBIT"
    
    def test_wallet_debit_insufficient_funds_raises_error(self):
        wallet = Wallet(
            id=WalletId("wallet1"),
            customer_id=CustomerId("customer1")
        )
        
        credit_amount = Money(Decimal("50"), Currency.EUR)
        wallet.credit(credit_amount, "Initial credit")
        
        debit_amount = Money(Decimal("100"), Currency.EUR)
        with pytest.raises(ValueError):
            wallet.debit(debit_amount, "Test debit")
    
    def test_wallet_has_sufficient_funds(self):
        wallet = Wallet(
            id=WalletId("wallet1"),
            customer_id=CustomerId("customer1")
        )
        
        credit_amount = Money(Decimal("100"), Currency.EUR)
        wallet.credit(credit_amount, "Initial credit")
        
        required_amount = Money(Decimal("50"), Currency.EUR)
        assert wallet.has_sufficient_funds(required_amount) is True
        
        required_amount_high = Money(Decimal("200"), Currency.EUR)
        assert wallet.has_sufficient_funds(required_amount_high) is False


class TestBooking:
    def test_creation_booking(self):
        tomorrow = date.today() + timedelta(days=1)
        stay = Stay(CheckInDate(tomorrow), NumberOfNights(2))
        
        booking = Booking(
            id=BookingId("booking1"),
            customer_id=CustomerId("customer1"),
            room_type=RoomTypeEnum.STANDARD,
            room_quantity=1,
            stay=stay,
            total_amount=Money(Decimal("100"), Currency.EUR)
        )
        
        assert booking.id.value == "booking1"
        assert booking.total_amount.amount == Decimal("100")
        assert booking.status == BookingStatus.PENDING
    
    def test_booking_deposit_amount(self):
        tomorrow = date.today() + timedelta(days=1)
        stay = Stay(CheckInDate(tomorrow), NumberOfNights(2))
        
        booking = Booking(
            id=BookingId("booking1"),
            customer_id=CustomerId("customer1"),
            room_type=RoomTypeEnum.STANDARD,
            room_quantity=1,
            stay=stay,
            total_amount=Money(Decimal("100"), Currency.EUR)
        )
        
        assert booking.deposit_amount.amount == Decimal("50")
        assert booking.balance_amount.amount == Decimal("50")
    
    def test_booking_pay_deposit(self):
        tomorrow = date.today() + timedelta(days=1)
        stay = Stay(CheckInDate(tomorrow), NumberOfNights(2))
        
        booking = Booking(
            id=BookingId("booking1"),
            customer_id=CustomerId("customer1"),
            room_type=RoomTypeEnum.STANDARD,
            room_quantity=1,
            stay=stay,
            total_amount=Money(Decimal("100"), Currency.EUR)
        )
        
        payment = booking.pay_deposit()
        
        assert payment.amount.amount == Decimal("50")
        assert payment.payment_type == PaymentType.DEPOSIT
        assert payment.is_processed is True
        assert len(booking.payments) == 1
    
    def test_booking_confirm_after_deposit(self):
        tomorrow = date.today() + timedelta(days=1)
        stay = Stay(CheckInDate(tomorrow), NumberOfNights(2))
        
        booking = Booking(
            id=BookingId("booking1"),
            customer_id=CustomerId("customer1"),
            room_type=RoomTypeEnum.STANDARD,
            room_quantity=1,
            stay=stay,
            total_amount=Money(Decimal("100"), Currency.EUR)
        )
        
        booking.pay_deposit()
        payment = booking.confirm_booking()
        
        assert payment.amount.amount == Decimal("50")
        assert payment.payment_type == PaymentType.BALANCE
        assert booking.status == BookingStatus.CONFIRMED
        assert len(booking.payments) == 2
    
    def test_booking_confirm_without_deposit_raises_error(self):
        tomorrow = date.today() + timedelta(days=1)
        stay = Stay(CheckInDate(tomorrow), NumberOfNights(2))
        
        booking = Booking(
            id=BookingId("booking1"),
            customer_id=CustomerId("customer1"),
            room_type=RoomTypeEnum.STANDARD,
            room_quantity=1,
            stay=stay,
            total_amount=Money(Decimal("100"), Currency.EUR)
        )
        
        with pytest.raises(ValueError):
            booking.confirm_booking()
    
    def test_booking_cancel(self):
        tomorrow = date.today() + timedelta(days=1)
        stay = Stay(CheckInDate(tomorrow), NumberOfNights(2))
        
        booking = Booking(
            id=BookingId("booking1"),
            customer_id=CustomerId("customer1"),
            room_type=RoomTypeEnum.STANDARD,
            room_quantity=1,
            stay=stay,
            total_amount=Money(Decimal("100"), Currency.EUR)
        )
        
        booking.cancel()
        assert booking.status == BookingStatus.CANCELLED
    
    def test_booking_room_quantity_validation(self):
        tomorrow = date.today() + timedelta(days=1)
        stay = Stay(CheckInDate(tomorrow), NumberOfNights(1))
        
        with pytest.raises(ValueError):
            Booking(
                id=BookingId("booking1"),
                customer_id=CustomerId("customer1"),
                room_type=RoomTypeEnum.STANDARD,
                room_quantity=0,
                stay=stay,
                total_amount=Money(Decimal("50"), Currency.EUR)
            )


class TestPayment:
    def test_creation_payment(self):
        payment = Payment(
            id=PaymentId("P1"),
            booking_id=BookingId("booking1"),
            amount=Money(Decimal("50"), Currency.EUR),
            payment_type=PaymentType.DEPOSIT
        )
        
        assert payment.is_processed is False
        assert payment.processed_at is None
    
    def test_payment_process(self):
        payment = Payment(
            id=PaymentId("P1"),
            booking_id=BookingId("booking1"),
            amount=Money(Decimal("50"), Currency.EUR),
            payment_type=PaymentType.DEPOSIT
        )
        
        payment.process()
        
        assert payment.is_processed is True
        assert payment.processed_at is not None
    
    def test_payment_process_twice_raises_error(self):
        payment = Payment(
            id=PaymentId("P1"),
            booking_id=BookingId("booking1"),
            amount=Money(Decimal("50"), Currency.EUR),
            payment_type=PaymentType.DEPOSIT
        )
        
        payment.process()
        
        with pytest.raises(ValueError):
            payment.process()
