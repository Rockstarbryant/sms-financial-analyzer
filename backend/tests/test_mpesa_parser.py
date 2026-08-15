from datetime import datetime

from app.models.transaction import Category, Confidence, Direction, TransactionType
from app.parsers.base import RawSms
from app.parsers.mpesa import MpesaParser

parser = MpesaParser()


def _sms(body: str) -> RawSms:
    return RawSms(sender="MPESA", body=body, timestamp=datetime(2026, 8, 1, 9, 0, 0))


def test_sent_transaction():
    result = parser.parse(
        _sms(
            "QGH7X1A2B1 Confirmed. Ksh20.00 sent to JOHN KAMAU 0722111222 on 1/8/26 at 9:12 AM. "
            "New M-PESA balance is Ksh4,530.00. Transaction cost, Ksh0.00."
        )
    )
    assert result.direction == Direction.OUT
    assert result.transaction_type == TransactionType.SENT
    assert result.category == Category.TRANSFER
    assert result.confidence == Confidence.HIGH
    assert result.amount == 20.00
    assert result.balance == 4530.00
    assert result.fee == 0.00
    assert result.counterparty == "JOHN KAMAU"
    assert result.counterparty_phone == "0722111222"
    assert result.transaction_id == "QGH7X1A2B1"


def test_received_transaction():
    result = parser.parse(
        _sms(
            "QGH7X1A2B2 Confirmed. You have received Ksh1,500.00 from MARY WANJIRU 0733222333 "
            "on 1/8/26 at 10:05 AM. New M-PESA balance is Ksh6,030.00."
        )
    )
    assert result.direction == Direction.IN
    assert result.transaction_type == TransactionType.RECEIVED
    assert result.amount == 1500.00
    assert result.balance == 6030.00
    assert result.counterparty_phone == "0733222333"


def test_payment_transaction():
    result = parser.parse(
        _sms(
            "QGH7X1A2B3 Confirmed. Ksh450.00 paid to GREEN VALLEY SUPERMARKET on 1/8/26 at 6:32 PM. "
            "New M-PESA balance is Ksh5,580.00. Transaction cost, Ksh0.00."
        )
    )
    assert result.transaction_type == TransactionType.PAYMENT
    assert result.category == Category.PAYMENT
    assert result.amount == 450.00


def test_bundle_detected_by_counterparty_context():
    result = parser.parse(
        _sms(
            "QGH7X1A2B4 Confirmed. Ksh99.00 sent to SAFARICOM POSTPAID BUNDLES for account 0722111222 "
            "on 2/8/26 at 8:00 AM. New M-PESA balance is Ksh5,481.00."
        )
    )
    assert result.transaction_type == TransactionType.BUNDLE
    assert result.category == Category.BUNDLE
    assert result.amount == 99.00


def test_word_data_does_not_trigger_bundle_classification():
    """A counterparty containing 'DATA' but not 'BUNDLE' must not be miscategorized."""
    result = parser.parse(
        _sms(
            "QGH7X1A2C2 Confirmed. Ksh80.00 sent to DATA CENTER CAFE 0722999888 on 7/8/26 at 2:00 PM. "
            "New M-PESA balance is Ksh5,072.00. Transaction cost, Ksh0.00."
        )
    )
    assert result.transaction_type == TransactionType.SENT
    assert result.category == Category.TRANSFER
    assert result.transaction_type != TransactionType.BUNDLE
    assert result.counterparty == "DATA CENTER CAFE"
    assert result.counterparty_phone == "0722999888"


def test_airtime_transaction():
    result = parser.parse(
        _sms(
            "QGH7X1A2B5 Confirmed. You bought Ksh50.00 of airtime on 2/8/26 at 8:15 AM. "
            "New M-PESA balance is Ksh5,431.00."
        )
    )
    assert result.transaction_type == TransactionType.AIRTIME
    assert result.category == Category.AIRTIME
    assert result.amount == 50.00


def test_withdrawal_with_fee_and_balance_kept_separate():
    result = parser.parse(
        _sms(
            "QGH7X1A2B6 Confirmed. Ksh2,000.00 withdrawn from Agent 774411 - RIVERSIDE SHOP on 2/8/26 "
            "at 1:20 PM. New M-PESA balance is Ksh3,402.00. Withdrawal charge Ksh29.00."
        )
    )
    assert result.transaction_type == TransactionType.WITHDRAWAL
    assert result.amount == 2000.00
    assert result.fee == 29.00
    assert result.balance == 3402.00
    # amount, fee, and balance must all be distinct fields, not derived from each other
    assert len({result.amount, result.fee, result.balance}) == 3


def test_deposit_transaction():
    result = parser.parse(
        _sms(
            "QGH7X1A2B7 Confirmed. Ksh3,000.00 deposited to your account with M-PESA agent 774411 "
            "on 3/8/26 at 4:45 PM. New M-PESA balance is Ksh6,402.00."
        )
    )
    assert result.direction == Direction.IN
    assert result.transaction_type == TransactionType.DEPOSIT
    assert result.amount == 3000.00


def test_reversal_transaction():
    result = parser.parse(
        _sms(
            "QGH7X1A2B8 Confirmed. Ksh100.00 sent to PETER OTIENO has been reversed. "
            "Your M-PESA balance is now Ksh6,502.00."
        )
    )
    assert result.transaction_type == TransactionType.REVERSAL
    assert result.amount == 100.00
    assert result.balance == 6502.00


def test_balance_only_message_is_unknown_and_amount_not_used_as_transaction():
    result = parser.parse(_sms("Dear customer, your M-PESA balance as at 6/8/26 08:00 AM is Ksh5,152.00."))
    assert result.confidence == Confidence.UNKNOWN
    assert result.amount is None


def test_promotional_message_is_unknown():
    result = parser.parse(
        _sms("Congratulations! You have been selected to win a free prize. Reply YES to claim your reward now!")
    )
    assert result.confidence == Confidence.UNKNOWN
    assert result.amount is None


def test_malformed_message_does_not_raise_and_is_unknown():
    result = parser.parse(_sms("asdkj a slkdj laksjd a;lksjd data corrupted %%%% ??? unreadable"))
    assert result.confidence == Confidence.UNKNOWN
    assert result.amount is None


def test_empty_body_does_not_raise():
    result = parser.parse(_sms(""))
    assert result.confidence == Confidence.UNKNOWN
