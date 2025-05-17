import os
import logging
from functools import wraps
from flask import request, jsonify

API_KEY = os.getenv("API_KEY")

def require_api_key(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        api_key = request.headers.get("x-api-key")
        if api_key and api_key == API_KEY:
            return func(*args, **kwargs)
        logging.error("Invalid or missing API key")
        return jsonify({"error": "Invalid or missing API key"}), 401
    return wrapper