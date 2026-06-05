# app/payment_service.py
# ------------------------------------------------------------------
# Contains all the business logic for processing payments.
# The route just calls functions from here.
# This separation keeps our code clean and easy to test.
# ------------------------------------------------------------------

import hashlib
import json
import time
import threading

from app.store import idempotency_store, processing_events, store_lock

# Keep cached idempotent responses for a short window.
# In production, this prevents unbounded memory growth and allows
# safe re-use of the same key only for a limited time.
IDEMPOTENCY_KEY_TTL = 900  # 15 minutes


def hash_body(body: dict) -> str:
    """
    Creates a unique fingerprint (hash) of the request body.

    Why? So we can detect if someone sends the SAME key
    but with DIFFERENT data (e.g., changing amount from 100 to 500).

    Example:
        hash_body({"amount": 100, "currency": "GHS"})
        --> "a3f5c2..." (some long string)
    """
    # Sort keys so {"amount":100,"currency":"GHS"} and
    # {"currency":"GHS","amount":100} produce the SAME hash
    serialized = json.dumps(body, sort_keys=True)
    return hashlib.sha256(serialized.encode()).hexdigest()


def validate_request_body(body: dict):
    """
    Makes sure the request has the required fields.
    Returns (True, None) if valid.
    Returns (False, "error message") if invalid.
    """
    if not body:
        return False, "Request body is missing."

    if "amount" not in body:
        return False, "Field 'amount' is required."

    if "currency" not in body:
        return False, "Field 'currency' is required."

    if not isinstance(body["amount"], (int, float)) or body["amount"] <= 0:
        return False, "Field 'amount' must be a positive number."

    return True, None


def _is_record_expired(record: dict) -> bool:
    """Returns True when a stored idempotency record has passed its TTL."""
    expires_at = record.get("expires_at")
    return expires_at is not None and time.time() >= expires_at


def process_payment(idempotency_key: str, body: dict):
    """
    The main function. Handles idempotency, duplicate detection, and racial
    in-flight request handling.

    Returns a tuple: (response_dict, status_code, extra_headers)
    """

    is_valid, error_msg = validate_request_body(body)
    if not is_valid:
        return {
            "error": error_msg
        }, 400, {}

    incoming_hash = hash_body(body)
    return _process_with_lock(idempotency_key, body, incoming_hash)


def _process_with_lock(idempotency_key: str, body: dict, incoming_hash: str):
    """
    Internal helper that handles all scenarios cleanly.
    """
    import threading

    while True:
        with store_lock:
            record = idempotency_store.get(idempotency_key)

            # If the record expired, remove it so the new request is treated
            # as a fresh payment attempt.
            if record and _is_record_expired(record):
                idempotency_store.pop(idempotency_key, None)
                processing_events.pop(idempotency_key, None)
                record = None

            if record is None:
                idempotency_store[idempotency_key] = {
                    "status": "processing",
                    "request_body_hash": incoming_hash,
                    "response_body": None,
                    "response_status": None,
                    "expires_at": time.time() + IDEMPOTENCY_KEY_TTL,
                }
                event = threading.Event()
                processing_events[idempotency_key] = event
                should_process = True
                break

            if record["status"] == "done":
                if record["request_body_hash"] != incoming_hash:
                    return {
                        "error": "Idempotency key already used for a different request body."
                    }, 409, {}

                return record["response_body"], record["response_status"], {
                    "X-Cache-Hit": "true"
                }

            if record["status"] == "processing":
                event = processing_events.get(idempotency_key)
                should_process = False
                break

    if should_process:
        try:
            time.sleep(2)

            amount = body["amount"]
            currency = body["currency"].upper()

            response_body = {
                "message": f"Charged {amount} {currency}",
                "transaction_id": f"TXN-{idempotency_key[:8].upper()}",
                "amount": amount,
                "currency": currency,
                "status": "success",
            }
            response_status = 201

            with store_lock:
                stored = idempotency_store[idempotency_key]
                stored["status"] = "done"
                stored["response_body"] = response_body
                stored["response_status"] = response_status
                stored["expires_at"] = time.time() + IDEMPOTENCY_KEY_TTL

        finally:
            if event:
                event.set()
            with store_lock:
                processing_events.pop(idempotency_key, None)

        return response_body, response_status, {}

    else:
        if event:
            event.wait(timeout=30)

        with store_lock:
            record = idempotency_store.get(idempotency_key)

        if record and record.get("status") == "done":
            if record["request_body_hash"] != incoming_hash:
                return {
                    "error": "Idempotency key already used for a different request body."
                }, 409, {}

            return record["response_body"], record["response_status"], {
                "X-Cache-Hit": "true"
            }

        return {"error": "Processing timed out. Please retry."}, 503, {}
