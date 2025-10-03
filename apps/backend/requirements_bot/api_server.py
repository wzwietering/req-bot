#!/usr/bin/env python3
"""
API Server entry point for Requirements Bot.

This script starts the FastAPI server using uvicorn.
"""

import argparse
import sys
from pathlib import Path

import uvicorn
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Add the project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


def main():
    parser = argparse.ArgumentParser(description="Requirements Bot API Server")
    parser.add_argument("--host", default="127.0.0.1", help="Host to bind the server to (default: 127.0.0.1)")
    parser.add_argument("--port", type=int, default=8080, help="Port to bind the server to (default: 8080)")
    parser.add_argument("--reload", action="store_true", help="Enable auto-reload for development")
    parser.add_argument(
        "--log-level",
        default="info",
        choices=["critical", "error", "warning", "info", "debug", "trace"],
        help="Log level (default: info)",
    )

    args = parser.parse_args()

    print(f"Starting Requirements Bot API server on {args.host}:{args.port}")
    print(f"API Documentation: http://{args.host}:{args.port}/docs")
    print(f"OpenAPI JSON: http://{args.host}:{args.port}/openapi.json")

    uvicorn.run(
        "requirements_bot.api.main:app", host=args.host, port=args.port, reload=args.reload, log_level=args.log_level
    )


if __name__ == "__main__":
    main()
