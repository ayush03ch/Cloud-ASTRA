#!/bin/bash

# Startup script for Azure App Service
echo "Starting Cloud-ASTRA application..."

# Navigate to webapp directory
cd /home/site/wwwroot

# Install dependencies if not already installed
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi

source venv/bin/activate

echo "Installing/Updating dependencies..."
pip install --upgrade pip
pip install -r requirements.txt

# Start Gunicorn server
echo "Starting Gunicorn server..."
cd webapp
gunicorn --bind=0.0.0.0:8000 --timeout 600 --workers 4 app:app
