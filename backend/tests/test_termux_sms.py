import json
import subprocess
from unittest.mock import patch

import pytest

from app.services.termux_sms import (
    SmsPermissionDeniedError,
    TermuxApiUnavailableError,
    list_device_sms,
)


def _completed(stdout: str = "[]", stderr: str = "", returncode: int = 0):
    return subprocess.CompletedProcess(
        args=["termux-sms-list"], returncode=returncode, stdout=stdout, stderr=stderr
    )


def test_parses_valid_sms_list():
    payload = [
        {
            "number": "MPESA",
            "body": "QGH7X1 Confirmed. Ksh20.00 sent to JOHN 0722111222 on 1/8/26. New M-PESA balance is Ksh100.00.",
            "received": "2026-08-01 09:12:00",
        },
        {
            "number": "AirtelMoney",
            "body": "You have received Ksh600.00 from JANE(0733555666). Transaction ID CI1. Balance: Ksh900.00.",
            "received": "2026-08-01 10:00:00",
        },
    ]
    with patch("subprocess.run", return_value=_completed(stdout=json.dumps(payload))):
        messages = list_device_sms()

    assert len(messages) == 2
    assert messages[0].sender == "MPESA"
    assert "sent to JOHN" in messages[0].body
    assert messages[0].timestamp.year == 2026


def test_uses_argument_list_never_shell_true():
    """Never invoke termux-sms-list via a shell -- command-injection guard."""
    with patch("subprocess.run", return_value=_completed()) as mock_run:
        list_device_sms()
    _, kwargs = mock_run.call_args
    assert kwargs.get("shell", False) is False
    call_args = mock_run.call_args[0][0]
    assert isinstance(call_args, list)
    assert call_args[0] == "termux-sms-list"


def test_termux_api_not_installed_raises_clear_error():
    with patch("subprocess.run", side_effect=FileNotFoundError()):
        with pytest.raises(TermuxApiUnavailableError, match="Termux:API is not available"):
            list_device_sms()


def test_permission_denied_raises_specific_error():
    with patch(
        "subprocess.run",
        return_value=_completed(returncode=1, stderr="Error: Permission denied"),
    ):
        with pytest.raises(SmsPermissionDeniedError):
            list_device_sms()


def test_other_nonzero_exit_raises_unavailable_error():
    with patch(
        "subprocess.run",
        return_value=_completed(returncode=1, stderr="unexpected failure"),
    ):
        with pytest.raises(TermuxApiUnavailableError):
            list_device_sms()


def test_timeout_raises_unavailable_error():
    with patch("subprocess.run", side_effect=subprocess.TimeoutExpired(cmd="termux-sms-list", timeout=60)):
        with pytest.raises(TermuxApiUnavailableError):
            list_device_sms()


def test_malformed_json_raises_unavailable_error():
    with patch("subprocess.run", return_value=_completed(stdout="not json")):
        with pytest.raises(TermuxApiUnavailableError):
            list_device_sms()


def test_one_malformed_entry_does_not_abort_whole_list():
    payload = [
        {"number": "MPESA", "body": "ok message", "received": "2026-08-01 09:12:00"},
        {"number": "MPESA", "body": "missing received field"},  # malformed
        {"number": "MPESA", "body": "ok message 2", "received": "2026-08-01 10:00:00"},
    ]
    with patch("subprocess.run", return_value=_completed(stdout=json.dumps(payload))):
        messages = list_device_sms()
    assert len(messages) == 2


def test_epoch_millis_timestamp_supported():
    payload = [{"number": "MPESA", "body": "test", "received": 1785000000000}]
    with patch("subprocess.run", return_value=_completed(stdout=json.dumps(payload))):
        messages = list_device_sms()
    assert len(messages) == 1
