#!/bin/bash
# Script to generate TypeScript types from FastAPI OpenAPI spec

set -e

echo "🔄 Generating TypeScript types from FastAPI backend..."

# Navigate to project root
cd "$(dirname "$0")/../.."

# Start backend server in background
echo "🚀 Starting FastAPI server for type generation..."
cd apps/backend

# Check if poetry environment exists
if ! poetry env info &> /dev/null; then
    echo "📦 Installing backend dependencies..."
    poetry install
fi

# Set minimal environment variables for type generation
export JWT_SECRET_KEY="type-generation-secret-key-for-openapi-generation-32-chars-minimum"
export DATABASE_URL="sqlite:///memory:"
export OAUTH_CLIENT_ID="dummy"
export OAUTH_CLIENT_SECRET="dummy"

# Start server in background and capture PID
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
cd ../../packages/shared-types
echo "📝 Generating TypeScript types..."

# Use openapi-typescript to generate types
npx openapi-typescript http://localhost:8000/openapi.json -o api.ts

# Stop backend server
echo "🛑 Stopping backend server..."
kill $BACKEND_PID

echo "✅ TypeScript types generated successfully in packages/shared-types/api.ts"