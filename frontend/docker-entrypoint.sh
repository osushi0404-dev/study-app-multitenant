#!/bin/sh
set -e

echo "[entrypoint] Clearing webpack/TypeScript cache..."
rm -rf /app/node_modules/.cache

echo "[entrypoint] Starting development server..."
exec npm start
