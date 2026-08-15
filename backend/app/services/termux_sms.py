"""Adapter around the `termux-sms-list` CLI (part of Termux:API).

Kept as a thin, isolated module so:
  - the parsing pipeline never has to know how SMS was retrieved (demo
    fixtures vs real device SMS use the exact same downstream code)
  - tests can mock `list_device_sms` without needing a real device
  - the one place that shells out is small enough to audit closely

Security: invokes subprocess with an argument list, never shell=True, so
there is no shell injection surface here.
"""
from __future__ import annotations

import json
import subprocess
from datetime import datetime

from app.parsers.base import RawSms
from app.utils.logging import get_logger

logger = get_logger(__name__)


class TermuxApiUnavailableError(Exception):
    """Raised when termux-sms-list is missing or Termux:API isn't installed."""


class SmsPermissionDeniedError(Exception):
    """Raised when Android has denied the SMS read permission."""


def _parse_timestamp(raw: int | str) -> datetime:
    """Parse the `received` field from termux-sms-list.

    termux-sms-list reports `received` as a formatted string, e.g.
    "2026-08-01 09:12:00". Some Termux:API versions have been observed to
    report epoch milliseconds instead, so both are supported defensively.
    """
    if isinstance(raw, (int, float)):
        return datetime.fromtimestamp(raw / 1000.0)

    text = str(raw).strip()
    if text.isdigit():
        return datetime.fromtimestamp(int(text) / 1000.0)

    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S", "%a %b %d %H:%M:%S %Z %Y"):
        try:
            return datetime.strptime(text, fmt)
        except ValueError:
            continue

    raise ValueError(f"Unrecognized timestamp format: {text!r}")


def list_device_sms(limit: int = 2000) -> list[RawSms]:
    """Retrieve SMS messages from the device via Termux:API.

    Never returns raw SMS bodies to a caller outside this process in any
    logged form -- callers pass RawSms straight into the parsing pipeline.
    """
    try:
        result = subprocess.run(
            ["termux-sms-list", "-l", str(limit)],
            capture_output=True,
            text=True,
            timeout=60,
            check=False,
        )
    except FileNotFoundError as exc:
        raise TermuxApiUnavailableError(
            "Termux:API is not available. Install Termux:API and ensure "
            "the Termux:API application is installed."
        ) from exc
    except subprocess.TimeoutExpired as exc:
        raise TermuxApiUnavailableError(
            "termux-sms-list timed out. Check that the Termux:API app is "
            "installed and SMS permission is granted."
        ) from exc

    if result.returncode != 0:
        stderr_lower = (result.stderr or "").lower()
        if "permission" in stderr_lower:
            raise SmsPermissionDeniedError(
                "SMS permission was denied. Grant SMS access to Termux:API "
                "in Android settings, then try again."
            )
        raise TermuxApiUnavailableError(
            "Termux:API is not available. Install Termux:API and ensure "
            "the Termux:API application is installed."
        )

    try:
        raw_items = json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        raise TermuxApiUnavailableError(
            "termux-sms-list returned an unexpected response. Is "
            "Termux:API installed and up to date?"
        ) from exc

    messages: list[RawSms] = []
    for item in raw_items:
        try:
            sender = str(item.get("number") or item.get("address") or "").strip()
            body = str(item.get("body") or "")
            timestamp = _parse_timestamp(item["received"])
        except (KeyError, ValueError, TypeError):
            # One malformed entry from the device must never abort the
            # whole retrieval -- skip it and keep going.
            logger.warning("Skipped a malformed SMS entry from termux-sms-list.")
            continue
        messages.append(RawSms(sender=sender, body=body, timestamp=timestamp))

    return messages
