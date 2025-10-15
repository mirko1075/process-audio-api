"""Authentication helpers."""
from __future__ import annotations

from functools import wraps
from typing import Callable, TypeVar, cast

from flask import jsonify, request

from utils.config import get_app_config

F = TypeVar("F", bound=Callable[..., object])


def require_api_key(func: F) -> F:
    @wraps(func)
    def wrapper(*args, **kwargs):
        api_key = request.headers.get("x-api-key")
        if api_key != get_app_config().api_key:
            return jsonify({"error": "Invalid or missing API key"}), 401
        return func(*args, **kwargs)

    return cast(F, wrapper)
