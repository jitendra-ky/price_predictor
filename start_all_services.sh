#!/bin/bash

# Start all services script for Docker container
echo "Starting all services in Docker container..."

# Function to handle cleanup on script exit
cleanup() {
    echo "Stopping all services..."
    supervisorctl stop all
    kill $(jobs -p) 2>/dev/null
    exit 0
}

# Set up signal handlers for graceful shutdown
trap cleanup SIGINT SIGTERM

# Ensure Redis data directory exists
mkdir -p /var/lib/redis

# Run database migrations
echo "Running database migrations..."
python manage.py makemigrations
python manage.py migrate

# Start supervisor to manage all services
echo "Starting supervisor to manage all services..."
exec /usr/bin/supervisord -c /etc/supervisor/conf.d/supervisord.conf
