"""Provider detection configuration.

Provider identification is driven primarily by the SMS sender/address
(more reliable than scanning the body for keywords), with a small set of
known sender aliases per provider. New providers can be added here without
touching parser internals or the detection logic elsewhere.
"""
from __future__ import annotations

from dataclasses import dataclass

from app.models.transaction import Provider


@dataclass(frozen=True)
class ProviderConfig:
    provider: Provider
    # Sender/address aliases are matched case-insensitively, and matched
    # as "contains" against the normalized sender field, since real-world
    # SMS gateways often prefix/suffix the sender ID inconsistently.
    sender_aliases: tuple[str, ...]


PROVIDER_CONFIGS: tuple[ProviderConfig, ...] = (
    ProviderConfig(
        provider=Provider.MPESA,
        sender_aliases=("mpesa", "m-pesa", "m-pesa app", "mpesaapp", "safaricom"),
    ),
    ProviderConfig(
        provider=Provider.AIRTEL_MONEY,
        # Include "airtelmoney" contact labels and common short-code forms.
        # Prefer longer aliases first via ordering in the tuple of configs;
        # within Airtel, longer strings are checked before bare "airtel".
        sender_aliases=(
            "airtel money",
            "airtelmoney",
            "airtel-money",
            "airtelmny",
            "airtel",
        ),
    ),
)


def normalize_sender(sender: str) -> str:
    return sender.strip().lower().replace("_", " ").replace(".", " ")


def detect_provider(sender: str) -> Provider:
    """Identify the provider from an SMS sender/address.

    Falls back to Provider.UNKNOWN when no configured alias matches -- the
    message will still flow through the pipeline but end up UNKNOWN
    confidence rather than being silently dropped or misattributed.
    """
    normalized = normalize_sender(sender)
    for config in PROVIDER_CONFIGS:
        for alias in config.sender_aliases:
            if alias in normalized:
                return config.provider
    return Provider.UNKNOWN
