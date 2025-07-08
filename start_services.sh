#!/bin/bash

# Start Django services script
# This script starts the Django development server, Telegram bot, and Celery worker

echo "Starting Django services..."

# Function to handle cleanup on script exit
cleanup() {
    echo "Stopping all services..."
    kill $(jobs -p) 2>/dev/null
    
    # Stop Redis gracefully
    echo "Stopping Redis server..."
    redis-cli shutdown 2>/dev/null
    
    exit 0
}

# Set up signal handlers for graceful shutdown
trap cleanup SIGINT SIGTERM

# Check if Redis is installed
if ! command -v redis-server &> /dev/null; then
    echo "Redis is not installed. Please install it first:"
    echo "sudo apt update && sudo apt install redis-server"
    exit 1
fi

# Start Redis server
echo "Starting Redis server..."
redis-server --daemonize yes
REDIS_PID=$!

# Wait a moment for Redis to start
sleep 2

# Test Redis connection
if ! redis-cli ping &> /dev/null; then
    echo "Error: Redis failed to start or is not responding"
    exit 1
fi

echo "Redis started successfully!"

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
echo "Redis server: Running as daemon"
echo "Django server: PID $SERVER_PID"
echo "Telegram bot: PID $BOT_PID"
echo "Celery worker: PID $CELERY_PID"
echo ""
echo "Press Ctrl+C to stop all services"

# Wait for all background processes
wait
