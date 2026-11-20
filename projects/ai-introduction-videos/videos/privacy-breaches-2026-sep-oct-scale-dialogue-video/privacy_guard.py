from __future__ import annotations

import json
import unicodedata
from typing import Any


def normalized_public_text(value: Any) -> str:
    text = value if isinstance(value, str) else json.dumps(value, ensure_ascii=False)
    text = unicodedata.normalize("NFKC", text).casefold()
    text = "".join(chr(ord(c) - 0x60) if "ァ" <= c <= "ヶ" else c for c in text)
    return "".join(c for c in text if c.isalnum())


def assert_company_names_absent(value: Any, context: str) -> None:
    text = normalized_public_text(value)
    forbidden = ("ここなら", "coconala", "そーすねくすと", "そおすねくすと", "sourcenext", "そにー", "そにい", "sony", "大阪市", "おおさかし", "osaka", "きゅーのーと", "くーのーと", "cuenote", "ゆみるりんく", "ymirlink", "手間いらず", "てまいらず", "temairazu", "clipmaster", "くりっぷますたー")
    if any(name in text for name in forbidden):
        raise ValueError(f"company name detected in {context}; public output must remain anonymous")
