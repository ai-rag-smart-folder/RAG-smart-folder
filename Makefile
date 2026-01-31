.PHONY: help all start stop restart logs build clean desktop status

# Default target
help:
	@echo "RAG Smart Folder - Available Commands:"
	@echo "======================================"
	@echo "make all       - Start everything (backend + desktop)"
	@echo "make start     - Start backend services only"
	@echo "make desktop   - Start desktop app only"
	@echo "make stop      - Stop all services"
	@echo "make restart   - Restart all services"
	@echo "make logs      - View backend logs"
	@echo "make build     - Build all services"
	@echo "make clean     - Clean up containers and images"
	@echo "make status    - Show service status"

# Start everything (backend + desktop)
all:
	@echo "🚀 Starting RAG Smart Folder - Full Stack..."
	@echo "=============================================="
	@echo "📋 Step 1: Starting backend services..."
	docker-compose up -d
	@echo "✅ Backend started!"
	@echo ""
	@echo "⏳ Step 2: Waiting for backend to be ready..."
	@sleep 3
	@echo "📋 Step 3: Setting up desktop app..."
	@if [ ! -d "desktop/node_modules" ]; then \
		echo "📦 Installing desktop app dependencies..."; \
		cd desktop && npm install; \
	fi
	@echo "🖥️  Step 4: Launching desktop app..."
	@echo ""
	@echo "🎉 RAG Smart Folder is starting!"
	@echo "📊 Services:"
	@echo "  Backend:     http://localhost:8003"
	@echo "  Desktop App: Opening now..."
	@echo ""
	@echo "💡 To stop everything: make stop"
	@echo "💡 To view logs: make logs"
	@echo ""
	cd desktop && npm start

# Start backend services only
start:
	@echo "🚀 Starting RAG Smart Folder Backend..."
	docker-compose up -d
	@echo "✅ Backend started! Visit: http://localhost:8003"

# Stop all services
stop:
	@echo "🛑 Stopping all services..."
	docker-compose down
	@echo "✅ All services stopped"

# Restart services
restart: stop start

# View logs
logs:
	docker-compose logs -f backend

# Build services
build:
	@echo "🔨 Building services..."
	docker-compose build

# Clean up
clean:
	@echo "🧹 Cleaning up..."
	docker-compose down -v --rmi all
	docker system prune -f

# Start desktop app natively
desktop:
	@echo "🖥️  Starting desktop app..."
	@if [ ! -d "desktop/node_modules" ]; then \
		echo "📦 Installing desktop app dependencies..."; \
		cd desktop && npm install; \
	fi
	cd desktop && npm start

# Show status
status:
	@echo "📊 Service Status:"
	docker-compose ps