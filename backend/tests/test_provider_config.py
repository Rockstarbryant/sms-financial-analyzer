from app.models.transaction import Provider
from app.parsers.provider_config import detect_provider


def test_detects_mpesa_variants():
    assert detect_provider("MPESA") == Provider.MPESA
    assert detect_provider("M-PESA") == Provider.MPESA
    assert detect_provider("mpesa") == Provider.MPESA


def test_detects_airtel_money_variants():
    assert detect_provider("AirtelMoney") == Provider.AIRTEL_MONEY
    assert detect_provider("Airtel Money") == Provider.AIRTEL_MONEY
    assert detect_provider("AIRTELMONEY") == Provider.AIRTEL_MONEY


def test_unknown_sender_returns_unknown_provider():
    assert detect_provider("RandomBank") == Provider.UNKNOWN
    assert detect_provider("+1234567890") == Provider.UNKNOWN
