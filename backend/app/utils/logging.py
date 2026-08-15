"""Structured, PII-safe logging setup.

Hard rule: never log full SMS bodies, phone numbers, transaction IDs,
personal/business names, or balances, unless settings.debug is explicitly
enabled by the user for local troubleshooting. Even then, prefer logging
counts and classifications over raw values.
"""
from __future__ import annotations

import logging

from app.config import settings


def get_logger(name: str) -> logging.Logger:
    logger = logging.getLogger(name)
    if not logger.handlers:
        handler = logging.StreamHandler()
        formatter = logging.Formatter(
            "%(asctime)s | %(levelname)s | %(name)s | %(message)s"
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        logger.setLevel(logging.DEBUG if settings.debug else logging.INFO)
    return logger
