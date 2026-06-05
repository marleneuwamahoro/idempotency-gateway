# app/__init__.py
# ------------------------------------------------------------------
# This is the "factory" function that creates and configures
# the Flask application.
#
# Using a factory function (create_app) is a best practice
# because it makes the app easier to test.
# ------------------------------------------------------------------

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
