from __future__ import annotations

from typing import Any


KNOWN_CARDS = [
    "RCBC",
    "BDO",
    "Maribank CC",
    "Tiktok PayLater",
    "Shopee PayLater",
]

_CARD_ALIASES = {
    "rcbc": "RCBC",
    "bdo": "BDO",
    "maribank": "Maribank CC",
    "maribankcc": "Maribank CC",
    "tiktokpaylater": "Tiktok PayLater",
    "spaylater": "Shopee PayLater",
    "shopeepaylater": "Shopee PayLater",
}


def normalize_card_tag(value: Any) -> str | None:
    if not isinstance(value, str) or not value.strip():
        return None

    clean_value = value.strip()
    alias_key = "".join(
        character
        for character in clean_value.casefold()
        if character.isalnum()
    )
    return _CARD_ALIASES.get(alias_key, clean_value)
