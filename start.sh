#!/bin/bash
echo "🚀 Starting VISU..."
echo ""

DIR="$(cd "$(dirname "$0")" && pwd)"

# Start frontend server in background
echo "📱 Starting frontend server..."
uv run python "$DIR/frontend/server.py" &
FRONTEND_PID=$!

# Wait for frontend to boot
sleep 3

# Start agent
echo "🤖 Starting VISU agent..."
uv run python "$DIR/main.py" console &
AGENT_PID=$!

echo ""
echo "✅ Both processes launched!"
echo "   - Frontend (PID $FRONTEND_PID): http://localhost:8000"
echo "   - Agent (PID $AGENT_PID): running in console mode"
echo ""
echo "Press Ctrl+C to stop both."

# Trap Ctrl+C to kill both
trap "echo '👋 Stopping...'; kill $FRONTEND_PID $AGENT_PID 2>/dev/null; exit" SIGINT SIGTERM

# Wait for both
wait
