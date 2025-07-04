#!/bin/bash

# Start Django services script
# This script starts the Django development server, Telegram bot, and Celery worker

echo "Starting Django services..."

# Function to handle cleanup on script exit
cleanup() {
    echo "Stopping all services..."
    kill $(jobs -p) 2>/dev/null
    exit 0
}

# Set up signal handlers for graceful shutdown
trap cleanup SIGINT SIGTERM

# Start Django development server
echo "Starting Django development server..."
python manage.py runserver &
SERVER_PID=$!

# Wait a moment for server to start
sleep 2

# Start Telegram bot
echo "Starting Telegram bot..."
python manage.py telegrambot &
BOT_PID=$!

# Wait a moment for bot to start
sleep 2

# Start Celery worker
echo "Starting Celery worker..."
python manage.py startcelery &
CELERY_PID=$!

echo "All services started successfully!"
echo "Django server: PID $SERVER_PID"
echo "Telegram bot: PID $BOT_PID"
echo "Celery worker: PID $CELERY_PID"
echo ""
echo "Press Ctrl+C to stop all services"

# Wait for all background processes
wait
