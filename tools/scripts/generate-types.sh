#!/bin/bash
# Script to generate TypeScript types from FastAPI OpenAPI spec

set -e

echo "🔄 Generating TypeScript types from FastAPI backend..."

# Get absolute project root path
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

echo "📁 Project root: $PROJECT_ROOT"

# Navigate to backend directory
BACKEND_DIR="$PROJECT_ROOT/apps/backend"
cd "$BACKEND_DIR"

echo "🚀 Starting FastAPI server for type generation..."

# Initialize conda if available (for conda environments)
if command -v conda &> /dev/null; then
    echo "🐍 Conda detected, initializing..."
    # Source conda initialization if it exists
    if [ -f "$HOME/anaconda3/etc/profile.d/conda.sh" ]; then
        source "$HOME/anaconda3/etc/profile.d/conda.sh"
    elif [ -f "$HOME/miniconda3/etc/profile.d/conda.sh" ]; then
        source "$HOME/miniconda3/etc/profile.d/conda.sh"
    elif [ -f "/opt/conda/etc/profile.d/conda.sh" ]; then
        source "/opt/conda/etc/profile.d/conda.sh"
    fi
fi

# Ensure Poetry environment exists and dependencies are installed
echo "📦 Ensuring backend dependencies are installed..."
if ! poetry env info &> /dev/null; then
    echo "🔧 Creating Poetry environment..."
    poetry install --no-interaction
else
    echo "✅ Poetry environment found"
    # Reinstall to ensure all dependencies are available
    echo "🔄 Refreshing dependencies..."
    poetry install --no-interaction --sync
fi

# Set minimal environment variables for type generation
export JWT_SECRET_KEY="type-generation-secret-key-for-openapi-generation-32-chars-minimum"
export DATABASE_URL="sqlite:///memory:"
export OAUTH_CLIENT_ID="dummy"
export OAUTH_CLIENT_SECRET="dummy"

# Get Poetry environment path to ensure proper Python execution
POETRY_ENV=$(poetry env info --path)
echo "🐍 Using Poetry environment: $POETRY_ENV"

# Test Poetry environment by checking if uvicorn is available
echo "🔍 Testing Poetry environment..."
if ! poetry run python -c "import uvicorn; print('✅ uvicorn available')" 2>/dev/null; then
    echo "❌ uvicorn not available in Poetry environment"
    echo "🔄 Attempting to reinstall dependencies..."
    poetry install --no-interaction --sync
fi

# Start server in background and capture PID
echo "▶️  Starting FastAPI server..."
poetry run python requirements_bot/api_server.py &
BACKEND_PID=$!

# Wait for server to start
echo "⏳ Waiting for server to start..."
sleep 5

# Check if server is running
if ! curl -s http://localhost:8000/health > /dev/null; then
    echo "❌ Backend server failed to start"
    kill $BACKEND_PID 2>/dev/null || true
    exit 1
fi

echo "✅ Backend server started successfully"

# Generate types
TYPES_DIR="$PROJECT_ROOT/packages/shared-types"
cd "$TYPES_DIR"
echo "📝 Generating TypeScript types in $TYPES_DIR..."

# Use openapi-typescript to generate types
if npx openapi-typescript http://localhost:8000/openapi.json -o api.ts; then
    echo "✅ TypeScript types generated successfully"
else
    echo "❌ Failed to generate TypeScript types"
    # Stop backend server on failure
    kill $BACKEND_PID 2>/dev/null || true
    exit 1
fi

# Stop backend server
echo "🛑 Stopping backend server..."
kill $BACKEND_PID 2>/dev/null || true

# Wait a moment for server to stop
sleep 2

echo "✅ TypeScript types generated successfully in packages/shared-types/api.ts"