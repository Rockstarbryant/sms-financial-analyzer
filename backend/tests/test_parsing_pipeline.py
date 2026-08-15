from datetime import datetime

from app.models.transaction import Transaction
from app.parsers.base import RawSms
from app.services.parsing_pipeline import process_messages


def _sent_sms() -> RawSms:
    return RawSms(
        sender="MPESA",
        body=(
            "QGH7X1A2B1 Confirmed. Ksh20.00 sent to JOHN KAMAU 0722111222 on 1/8/26 at 9:12 AM. "
            "New M-PESA balance is Ksh4,530.00. Transaction cost, Ksh0.00."
        ),
        timestamp=datetime(2026, 8, 1, 9, 12, 0),
    )


def test_inserts_recognized_transaction(db_session):
    stats = process_messages(db_session, [_sent_sms()])
    assert stats.scanned == 1
    assert stats.recognized == 1
    assert stats.inserted == 1
    assert stats.duplicates == 0
    assert stats.unknown == 0
    assert db_session.query(Transaction).count() == 1


def test_reimporting_same_message_never_creates_duplicate(db_session):
    process_messages(db_session, [_sent_sms()])
    stats_second_run = process_messages(db_session, [_sent_sms()])

    assert stats_second_run.inserted == 0
    assert stats_second_run.duplicates == 1
    assert db_session.query(Transaction).count() == 1


def test_repeated_sync_ten_times_creates_no_duplicates(db_session):
    for _ in range(10):
        process_messages(db_session, [_sent_sms()])
    assert db_session.query(Transaction).count() == 1


def test_ambiguous_message_excluded_from_totals(db_session):
    ambiguous = RawSms(
        sender="MPESA",
        body="Congratulations! You have been selected to win a free prize.",
        timestamp=datetime(2026, 8, 1, 9, 0, 0),
    )
    stats = process_messages(db_session, [ambiguous])
    assert stats.unknown == 1
    assert stats.inserted == 0
    assert db_session.query(Transaction).count() == 0


def test_unsupported_sender_counted_unknown_not_dropped_silently(db_session):
    unsupported = RawSms(
        sender="SomeRandomBank",
        body="Your account was credited Ksh500.00.",
        timestamp=datetime(2026, 8, 1, 9, 0, 0),
    )
    stats = process_messages(db_session, [unsupported])
    assert stats.scanned == 1
    assert stats.unknown == 1
    assert stats.recognized == 0


def test_one_malformed_message_does_not_abort_batch(db_session):
    messages = [
        RawSms(sender="MPESA", body="???unreadable garbage!!!", timestamp=datetime(2026, 8, 1, 9, 0, 0)),
        _sent_sms(),
    ]
    stats = process_messages(db_session, messages)
    assert stats.scanned == 2
    assert stats.inserted == 1
    assert stats.unknown == 1


def test_mixed_batch_statistics_add_up(db_session):
    messages = [
        _sent_sms(),
        _sent_sms(),  # will be a duplicate of the first
        RawSms(sender="MPESA", body="Balance is Ksh100.00 only.", timestamp=datetime(2026, 8, 2, 9, 0, 0)),
        RawSms(sender="UnknownBank", body="Some message.", timestamp=datetime(2026, 8, 3, 9, 0, 0)),
    ]
    stats = process_messages(db_session, messages)
    assert stats.scanned == 4
    assert stats.inserted == 1
    assert stats.duplicates == 1
    assert stats.unknown == 2
    assert stats.recognized == 2  # the two m-pesa "sent" messages, one inserted one duplicate
