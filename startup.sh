#!/bin/bash

# Startup script for Azure App Service
echo "Starting Cloud-ASTRA application..."

# Navigate to wwwroot
cd /home/site/wwwroot

# Set Python path to include current directory
export PYTHONPATH=/home/site/wwwroot:$PYTHONPATH

# Start Gunicorn server
echo "Starting Gunicorn server on port 8000..."
gunicorn --bind=0.0.0.0:8000 --timeout=600 --workers=2 --access-logfile - --error-logfile - webapp.app:app
