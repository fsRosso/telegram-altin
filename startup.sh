#!/bin/bash

echo "Starting Telegram Bot..."

# Clean old PID files
echo "Cleaning old PID files..."
rm -f bot_*.pid

# Check and kill old processes
echo "Checking old processes..."
pkill -f "python.*main.py" || true

# Wait a bit
sleep 2

echo "Cleanup completed, starting bot..."

# Start the bot
exec python main.py
