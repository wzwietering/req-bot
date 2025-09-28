#!/bin/bash
# Script to generate TypeScript types from FastAPI OpenAPI spec

set -e

echo "🔄 Generating TypeScript types from FastAPI backend..."

# Get absolute project root path
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

# Navigate to backend directory
BACKEND_DIR="$PROJECT_ROOT/apps/backend"
cd "$BACKEND_DIR"

# 1. Install dependencies
echo "📦 Installing backend dependencies..."
poetry install --no-interaction

# Set minimal environment variables for type generation
export JWT_SECRET_KEY="type-generation-secret-key-for-openapi-generation-32-chars-minimum"
export DATABASE_URL="sqlite:///memory:"
export OAUTH_CLIENT_ID="dummy"
export OAUTH_CLIENT_SECRET="dummy"

# 2. Start server
echo "🚀 Starting FastAPI server..."
poetry run python requirements_bot/api_server.py &
BACKEND_PID=$!

# 3. Wait for server to be online
echo "⏳ Waiting for server to be ready..."
while ! curl -s http://localhost:8080/health > /dev/null; do
    sleep 1
done
echo "✅ Backend server is ready"

# 4. Generate types
TYPES_DIR="$PROJECT_ROOT/packages/shared-types"
cd "$TYPES_DIR"
echo "📝 Generating TypeScript types..."

if npx openapi-typescript http://localhost:8080/openapi.json -o api.ts; then
    echo "✅ TypeScript types generated successfully"
else
    echo "❌ Failed to generate TypeScript types"
    kill $BACKEND_PID 2>/dev/null || true
    exit 1
fi

# 5. Shutdown server
echo "🛑 Stopping backend server..."
kill $BACKEND_PID 2>/dev/null || true

echo "✅ TypeScript types generated successfully in packages/shared-types/api.ts"