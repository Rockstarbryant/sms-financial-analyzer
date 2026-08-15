"""Deterministic fingerprinting for SMS messages.

Used to prevent the same SMS from ever creating multiple transaction rows,
whether it's re-imported via demo mode or re-synced from the device
repeatedly.
"""
from __future__ import annotations

import hashlib


def sms_fingerprint(sender: str, timestamp_iso: str, body: str) -> str:
    """Return a stable SHA-256 hex digest identifying this exact SMS.

    The hash is derived only from sender + timestamp + body, never from
    parsed fields, so two different parse attempts at the same raw message
    always produce the same fingerprint.
    """
    raw = f"{sender.strip().lower()}|{timestamp_iso.strip()}|{body.strip()}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()
