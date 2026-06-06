
from flask import Blueprint, request, jsonify, render_template

from app.payment_service import process_payment

payment_bp = Blueprint("payment", __name__)

@payment_bp.route("/", methods=["GET"])
def root():
    return render_template("index.html")


@payment_bp.route("/health", methods=["GET"])
def health_check():
    """
    A simple health check endpoint.
    Useful to confirm the server is running.
    GET /health --> 200 OK
    """
    return jsonify({"status": "ok", "message": "Idempotency Gateway is running."}), 200


@payment_bp.route("/process-payment", methods=["GET", "POST"])
def handle_payment():
    """
    Main payment endpoint.
    POST /process-payment handles payment requests with idempotency.
    GET /process-payment returns a helpful message for browser users.

    Required Header for POST:
        Idempotency-Key: <some-unique-string>

    Required Body for POST (JSON):
        {
            "amount": 100,
            "currency": "GHS"
        }
    """

    if request.method == "GET":
        return jsonify({
            "status": "ok",
            "message": "Use POST /process-payment with Idempotency-Key and JSON body to process a payment."
        }), 200

    # --- Step 1: Read the Idempotency-Key from the request headers ---
    idempotency_key = request.headers.get("Idempotency-Key")

    if not idempotency_key:
        return jsonify({
            "error": "Missing required header: Idempotency-Key"
        }), 400

    if len(idempotency_key.strip()) == 0:
        return jsonify({
            "error": "Idempotency-Key header cannot be empty."
        }), 400

    # --- Step 2: Read the JSON body ---
    body = request.get_json(silent=True)  # silent=True prevents crash on bad JSON

    if body is None:
        return jsonify({
            "error": "Request body must be valid JSON with Content-Type: application/json"
        }), 400

    # --- Step 3: Call our business logic ---
    response_body, status_code, extra_headers = process_payment(
        idempotency_key=idempotency_key.strip(),
        body=body
    )

    # --- Step 4: Build and return the HTTP response ---
    response = jsonify(response_body)
    response.status_code = status_code

    # Attach any extra headers (like X-Cache-Hit: true)
    for header_name, header_value in extra_headers.items():
        response.headers[header_name] = header_value

    return response
