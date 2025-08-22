#!/bin/bash

# RAG Smart Folder - Stop Everything

echo "🛑 Stopping RAG Smart Folder services..."

# Stop Docker backend
echo "🐳 Stopping backend..."
cd devops
docker-compose down

if [ $? -eq 0 ]; then
    echo "✅ Backend stopped"
else
    echo "⚠️  Backend stop had issues (may already be stopped)"
fi

cd ..

# Kill any running desktop app processes
echo "🖥️  Stopping desktop app..."
pkill -f "electron.*desktop-app" 2>/dev/null
pkill -f "npm.*start" 2>/dev/null

echo ""
echo "✅ All services stopped!"
echo ""
echo "🚀 To start again: ./start-all.sh"