from __future__ import annotations

from typing import Any

from dateutil import parser


def unwrap_data(payload: Any) -> Any:
    if isinstance(payload, dict) and "data" in payload and (
        "status" in payload or "message" in payload
    ):
        return payload.get("data")
    return payload


def ensure_list(value: Any) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]


def coalesce(*values: Any) -> Any:
    for value in values:
        if value not in (None, "", "NA", "null"):
            return value
    return None


def clean_text(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def parse_float(value: Any) -> float | None:
    if value in (None, "", "NA", "null"):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    text = str(value).replace(",", "").strip()
    if not text:
        return None
    try:
        return float(text)
    except ValueError:
        return None


def parse_int(value: Any) -> int | None:
    number = parse_float(value)
    if number is None:
        return None
    return int(number)


def normalize_date(value: Any) -> str | None:
    if value in (None, "", "NA", "Date Not Found", "Date Not Exist"):
        return None
    text = str(value).strip()
    try:
        return parser.parse(text, dayfirst=True).date().isoformat()
    except Exception:
        return text


def normalize_datetime(value: Any) -> str | None:
    if value in (None, "", "NA", "Date Not Found", "Date Not Exist"):
        return None
    text = str(value).strip()
    try:
        return parser.parse(text, dayfirst=True).isoformat()
    except Exception:
        return text


def normalize_payment_status(value: Any) -> str | None:
    text = clean_text(value)
    if text is None:
        return None
    upper = text.upper()
    if upper in {"PAID", "SUCCESS"}:
        return "PAID"
    if upper in {"SAVED", "PENDING"}:
        return "PENDING"
    return upper


def map_coordinates(coordinates: Any) -> list[dict[str, float]]:
    mapped: list[dict[str, float]] = []
    for item in ensure_list(coordinates):
        lat = parse_float(item.get("lat")) if isinstance(item, dict) else None
        lng = (
            parse_float(item.get("lang"))
            if isinstance(item, dict)
            else None
        )
        if lat is None or lng is None:
            continue
        mapped.append({"lat": lat, "lng": lng})
    return mapped


def download_url(base_url: str, uid: str | None) -> str | None:
    if not uid:
        return None
    return f"{base_url.rstrip('/')}/download/{uid}"
