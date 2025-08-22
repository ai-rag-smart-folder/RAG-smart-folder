#!/bin/bash

# RAG Smart Folder - Start Everything (Backend + Desktop App)

echo "🚀 Starting RAG Smart Folder - Full Stack..."
echo "=============================================="

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo "❌ Docker is not running. Please start Docker first."
    exit 1
fi

# Check if Node.js is available for desktop app
if ! command -v node &> /dev/null; then
    echo "❌ Node.js is not installed. Please install Node.js first."
    exit 1
fi

echo "✅ Docker and Node.js found"
echo ""

# Step 1: Start Backend with Docker
echo "🐳 Starting backend services..."
cd devops
docker-compose up -d

if [ $? -eq 0 ]; then
    echo "✅ Backend started successfully"
else
    echo "❌ Failed to start backend"
    exit 1
fi

cd ..

# Step 2: Setup Desktop App (if needed)
if [ ! -d "desktop-app/node_modules" ]; then
    echo "📦 Setting up desktop app for first time..."
    cd desktop-app
    ./setup.sh
    if [ $? -ne 0 ]; then
        echo "❌ Failed to setup desktop app"
        exit 1
    fi
    cd ..
fi

# Step 3: Wait for backend to be ready
echo "⏳ Waiting for backend to be ready..."
for i in {1..30}; do
    if curl -s http://127.0.0.1:8003/health > /dev/null 2>&1; then
        echo "✅ Backend is ready!"
        break
    fi
    if [ $i -eq 30 ]; then
        echo "⚠️  Backend taking longer than expected, but continuing..."
        break
    fi
    sleep 1
done

# Step 4: Start Desktop App
echo "🖥️  Launching desktop app..."
echo ""
echo "📊 Services Status:"
echo "  Backend:     http://127.0.0.1:8003"
echo "  Desktop App: Starting now..."
echo ""

cd desktop-app
npm start &
DESKTOP_PID=$!

# Wait a moment for desktop app to start
sleep 3

echo ""
echo "🎉 RAG Smart Folder is now running!"
echo ""
echo "📝 Useful commands:"
echo "  View backend logs:  cd devops && docker-compose logs -f"
echo "  Stop backend:       cd devops && docker-compose down"
echo "  Stop desktop app:   Close the desktop window"
echo ""
echo "🛑 To stop everything:"
echo "  Press Ctrl+C to stop this script"
echo "  Then run: cd devops && docker-compose down"
echo ""

# Keep script running and handle cleanup
trap 'echo ""; echo "🛑 Stopping services..."; cd devops && docker-compose down; kill $DESKTOP_PID 2>/dev/null; echo "✅ All services stopped"; exit 0' INT

# Wait for desktop app to finish
wait $DESKTOP_PID