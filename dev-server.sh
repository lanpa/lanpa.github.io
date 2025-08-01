#!/bin/bash

# Hugo Development Server Script
# Clears cache and starts server with local configuration

echo "🧹 Clearing Hugo cache..."

# Stop any running Hugo servers
pkill -f "hugo server" 2>/dev/null || true

# Clear Hugo cache and build artifacts
echo "Cleaning build artifacts..."
hugo --gc --cleanDestinationDir 2>/dev/null || true

# Remove generated resources cache
echo "Removing resources cache..."
rm -rf resources/_gen/ 2>/dev/null || true

# Remove public directory for fresh build
echo "Removing public directory..."
rm -rf public/ 2>/dev/null || true

echo "✅ Cache cleared!"
echo ""
echo "🚀 Starting Hugo development server..."

# Start Hugo server with development configuration
hugo server -D --buildFuture --config hugo.dev.toml --bind 0.0.0.0 --port 1313 --disableFastRender

echo "🛑 Hugo server stopped."
