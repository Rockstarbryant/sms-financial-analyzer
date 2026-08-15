from datetime import datetime

from app.models.transaction import Category, Confidence, Direction, TransactionType
from app.parsers.airtel_money import AirtelMoneyParser
from app.parsers.base import RawSms

parser = AirtelMoneyParser()


def _sms(body: str) -> RawSms:
    return RawSms(sender="AirtelMoney", body=body, timestamp=datetime(2026, 8, 1, 9, 0, 0))


def test_sent_transaction():
    result = parser.parse(
        _sms(
            "You have sent Ksh200.00 to BRIAN OUMA(0733444555). Transaction ID CI10001A. "
            "Fee: Ksh10.00. Balance: Ksh2,300.00."
        )
    )
    assert result.direction == Direction.OUT
    assert result.transaction_type == TransactionType.SENT
    assert result.amount == 200.00
    assert result.fee == 10.00
    assert result.balance == 2300.00
    assert result.transaction_id == "CI10001A"
    assert result.counterparty is not None and "BRIAN OUMA" in result.counterparty
    assert result.counterparty_phone == "0733444555"


def test_received_transaction():
    result = parser.parse(
        _sms("You have received Ksh600.00 from FAITH ACHIENG(0733555666). Transaction ID CI10002B. Balance: Ksh2,900.00.")
    )
    assert result.direction == Direction.IN
    assert result.transaction_type == TransactionType.RECEIVED
    assert result.amount == 600.00


def test_payment_transaction():
    result = parser.parse(
        _sms("Payment of Ksh350.00 to QUICKMART LTD successful. Transaction ID CI10003C. Fee: Ksh0.00. Balance: Ksh2,550.00.")
    )
    assert result.transaction_type == TransactionType.PAYMENT
    assert result.category == Category.PAYMENT
    assert result.amount == 350.00


def test_bundle_transaction():
    result = parser.parse(
        _sms("You have purchased Internet Bundle worth Ksh99.00. Transaction ID CI10004D. Balance: Ksh2,451.00.")
    )
    assert result.transaction_type == TransactionType.BUNDLE
    assert result.category == Category.BUNDLE
    assert result.amount == 99.00


def test_airtime_transaction():
    result = parser.parse(
        _sms("You have purchased Airtime worth Ksh100.00. Transaction ID CI10005E. Balance: Ksh2,351.00.")
    )
    assert result.transaction_type == TransactionType.AIRTIME
    assert result.amount == 100.00


def test_withdrawal_transaction_fields_independent():
    result = parser.parse(
        _sms("You have withdrawn Ksh1,500.00 from Agent SHOP992. Fee: Ksh27.00. Transaction ID CI10006F. Balance: Ksh824.00.")
    )
    assert result.transaction_type == TransactionType.WITHDRAWAL
    assert result.amount == 1500.00
    assert result.fee == 27.00
    assert result.balance == 824.00
    assert len({result.amount, result.fee, result.balance}) == 3


def test_deposit_transaction():
    result = parser.parse(
        _sms("You have deposited Ksh2,000.00 via Agent SHOP992. Transaction ID CI10007G. Balance: Ksh2,824.00.")
    )
    assert result.direction == Direction.IN
    assert result.transaction_type == TransactionType.DEPOSIT
    assert result.amount == 2000.00


def test_payment_with_data_word_not_classified_as_bundle():
    result = parser.parse(
        _sms("Payment of Ksh220.00 to DATA WORLD CYBER successful. Transaction ID CI1000AJ. Fee: Ksh0.00. Balance: Ksh3,139.00.")
    )
    assert result.transaction_type == TransactionType.PAYMENT
    assert result.transaction_type != TransactionType.BUNDLE


def test_balance_only_message_is_unknown():
    result = parser.parse(_sms("Dear Customer, your Airtel Money balance is Ksh3,359.00 as of today. Thank you for using our services."))
    assert result.confidence == Confidence.UNKNOWN
    assert result.amount is None


def test_promotional_message_is_unknown():
    result = parser.parse(_sms("Win big with Airtel! Stand a chance to win amazing prizes this week. Terms and conditions apply."))
    assert result.confidence == Confidence.UNKNOWN


def test_malformed_message_does_not_raise():
    result = parser.parse(_sms("###corrupted### message !! unreadable content @@@ 12903u4"))
    assert result.confidence == Confidence.UNKNOWN
    assert result.amount is None
