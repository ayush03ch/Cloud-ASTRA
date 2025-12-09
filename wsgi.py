#!/usr/bin/env python3
"""
WSGI Entry Point for Azure App Service
This file is placed at the root of the deployment package
"""
import sys
import os

# Add current directory to Python path so all modules are importable
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)

# Now import the Flask app from webapp module
from webapp.app import app

# This is what Gunicorn will look for
application = app

if __name__ == "__main__":
    # For local testing
    app.run(host='0.0.0.0', port=8000, debug=False)
