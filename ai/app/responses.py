from __future__ import annotations

from typing import Any


SUCCESS = "SUCCESS"
MISSING_REQUIRED_FIELD = "MISSING_REQUIRED_FIELD"
INVALID_ARRAY_LENGTH = "INVALID_ARRAY_LENGTH"
INVALID_DATE_FORMAT = "INVALID_DATE_FORMAT"
INVALID_INPUT_VALUE = "INVALID_INPUT_VALUE"
INSUFFICIENT_INPUT_DATA = "INSUFFICIENT_INPUT_DATA"
MODEL_INFERENCE_FAILED = "MODEL_INFERENCE_FAILED"
POST_PROCESSING_FAILED = "POST_PROCESSING_FAILED"
INTERNAL_SERVER_ERROR = "INTERNAL_SERVER_ERROR"


def ok(request_id: str | None, data: dict[str, Any], message: str = "success") -> dict[str, Any]:
    return {
        "request_id": request_id,
        "code": SUCCESS,
        "message": message,
        "data": data,
    }


def error(request_id: str | None, code: str, message: str) -> dict[str, Any]:
    return {
        "request_id": request_id,
        "code": code,
        "message": message,
        "data": None,
    }

