#!/bin/bash

# Startup script for Azure App Service
echo "Starting Cloud-ASTRA application..."

# Navigate to wwwroot (all deps pre-installed)
cd /home/site/wwwroot

# Start Gunicorn server directly (no build needed)
echo "Starting Gunicorn server..."
gunicorn --bind=0.0.0.0:8000 --timeout=600 --workers=2 webapp.app:app
