#!/bin/bash

# RAG Smart Folder - Quick Start Docker Backend

echo "🐳 Starting RAG Smart Folder with Docker..."

cd devops

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo "❌ Docker is not running. Please start Docker first."
    exit 1
fi

# Start the backend
echo "🚀 Starting backend services..."
docker-compose up -d

# Show status
echo ""
echo "✅ Backend started successfully!"
echo ""
echo "📊 Status:"
docker-compose ps

echo ""
echo "📝 To view logs:"
echo "  cd devops && docker-compose logs -f"
echo ""
echo "🛑 To stop:"
echo "  cd devops && docker-compose down"