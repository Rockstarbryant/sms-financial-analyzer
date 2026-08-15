"""Loads synthetic demo SMS fixtures for demo mode.

The fixtures are fully synthetic/anonymized -- never real user SMS data --
and are parsed through the exact same pipeline real device SMS will use in
a later phase, so demo mode is a faithful test of the whole system.
"""
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from app.config import settings
from app.parsers.base import RawSms


def load_demo_messages() -> list[RawSms]:
    messages: list[RawSms] = []
    sample_dir = Path(settings.sample_data_dir)

    for filename in ("sample_mpesa.json", "sample_airtel.json"):
        file_path = sample_dir / filename
        if not file_path.exists():
            continue
        with file_path.open("r", encoding="utf-8") as f:
            raw_items = json.load(f)
        for item in raw_items:
            messages.append(
                RawSms(
                    sender=item["sender"],
                    body=item["body"],
                    timestamp=datetime.fromisoformat(item["timestamp"]),
                )
            )
    return messages
