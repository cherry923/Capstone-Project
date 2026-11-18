from __future__ import annotations

from datetime import datetime
from typing import Any

from app import responses


def missing(payload: dict[str, Any], fields: list[str]) -> str | None:
    for field in fields:
        if field not in payload or payload[field] is None:
            return field
    return None


def parse_yyyy_mm_dd(value: Any) -> datetime | None:
    if not isinstance(value, str):
        return None
    try:
        return datetime.strptime(value, "%Y-%m-%d")
    except ValueError:
        return None


def as_number(value: Any) -> float | None:
    if isinstance(value, bool) or value is None:
        return None
    try:
        converted = float(value)
    except (TypeError, ValueError):
        return None
    if converted != converted:
        return None
    return converted


def require_number(payload: dict[str, Any], field: str) -> tuple[float | None, str | None]:
    if field not in payload or payload[field] is None:
        return None, responses.MISSING_REQUIRED_FIELD
    value = as_number(payload[field])
    if value is None:
        return None, responses.INVALID_INPUT_VALUE
    return value, None


def get_number_with_aliases(payload: dict[str, Any], aliases: list[str]) -> float | None:
    for key in aliases:
        if key in payload:
            return as_number(payload[key])
    return None

