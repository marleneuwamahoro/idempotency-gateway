# run.py
# ------------------------------------------------------------------
# This is the main entry point for the application.
# Run this file to start the Flask development server:
#     python run.py
# ------------------------------------------------------------------

from app import create_app

# Create the Flask app using our factory function
app = create_app()

if __name__ == "__main__":
    # threaded=True is CRUCIAL for this project!
    # It allows Flask to handle multiple requests at the same time,
    # which is necessary for our race condition (in-flight) test.
    app.run(debug=True, threaded=True, port=5000)
# source venv/bin/activate