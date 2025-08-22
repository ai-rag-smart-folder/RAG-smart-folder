#!/bin/bash

# RAG Smart Folder Desktop App Setup Script

echo "🚀 Setting up RAG Smart Folder Desktop App..."

# Check if Node.js is installed
if ! command -v node &> /dev/null; then
    echo "❌ Node.js is not installed. Please install Node.js first."
    echo "Visit: https://nodejs.org/"
    exit 1
fi

# Check if npm is installed
if ! command -v npm &> /dev/null; then
    echo "❌ npm is not installed. Please install npm first."
    exit 1
fi

echo "✅ Node.js and npm found"

# Install dependencies
echo "📦 Installing dependencies..."
npm install

if [ $? -eq 0 ]; then
    echo "✅ Dependencies installed successfully"
else
    echo "❌ Failed to install dependencies"
    exit 1
fi

echo ""
echo "🎉 Setup complete!"
echo ""
echo "To run the desktop app:"
echo "  npm start"
echo ""
echo "To build the app for distribution:"
echo "  npm run build        # Build for current platform"
echo "  npm run build-mac    # Build for macOS"
echo "  npm run build-win    # Build for Windows"
echo "  npm run build-linux  # Build for Linux"
echo ""
echo "⚠️  Make sure your backend server is running on http://127.0.0.1:8000"
echo "   Your Docker container should already be running!"
echo "   If not, run: docker-compose up -d"