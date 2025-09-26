#!/bin/bash
# Development script to run backend and frontend concurrently

set -e

echo "🚀 Starting req-bot development environment..."

# Check if poetry is installed
if ! command -v poetry &> /dev/null; then
    echo "❌ Poetry not found. Please install Poetry first: https://python-poetry.org/docs/#installation"
    exit 1
fi

# Check if Node.js is installed
if ! command -v node &> /dev/null; then
    echo "❌ Node.js not found. Please install Node.js >= 18.0.0"
    exit 1
fi

# Navigate to project root
cd "$(dirname "$0")/../.."

echo "📦 Installing backend dependencies..."
cd apps/backend && poetry install --no-dev

echo "📦 Installing frontend dependencies (when frontend exists)..."
if [ -d "apps/frontend" ]; then
    cd ../frontend && npm install
fi

cd ../..

echo "🔄 Generating TypeScript types..."
npm run generate:types || echo "⚠️  Type generation skipped (will be available after frontend setup)"

echo "🚀 Starting development servers..."
npm run dev