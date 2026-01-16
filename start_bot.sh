#!/bin/bash

# Gym Automation Bot Startup Script - Production Edition
echo "🛡️  Ensuring a clean state for the bot..."

# 1. Kill any process that looks like our bot
# We target the module name 'app.main' and the script itself
pkill -9 -f "app.main" || true
pkill -9 -f "start_bot.sh" --exclude-pid $$ || true

# 2. Hard sleep to let the network connections clear
echo "⏳ Waiting for old connections to close..."
sleep 2

# 3. Double check (forced cleanup)
CLEAN_COUNT=$(ps aux | grep -i "app.main" | grep -v grep | wc -l)
if [ $CLEAN_COUNT -gt 0 ]; then
    echo "⚠️  Found $CLEAN_COUNT lingering processes. Force killing..."
    ps aux | grep -i "app.main" | grep -v grep | awk '{print $2}' | xargs kill -9 || true
fi

echo "� Starting Gym Automation Bot..."
export PYTHONPATH=$PYTHONPATH:.
export ENABLE_SHEETS="true"

# 4. Check for .env and bot token
if [ -f .env ]; then
    export $(grep -v '^#' .env | xargs)
fi

# 5. Run the Bot
echo "🏋️‍♂️ Bot is now running and connected to Google Sheets!"
python3 -m app.main
