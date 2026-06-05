
from flask import Flask


def create_app():
    """
    Creates and configures the Flask application.
    Returns the app object.
    """
    app = Flask(__name__)

    # Register our routes (Blueprint) with the app.
    # This connects app/routes.py to the Flask app.
    from app.routes import payment_bp
    app.register_blueprint(payment_bp)

    return app
