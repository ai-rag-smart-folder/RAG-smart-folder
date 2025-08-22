# RAG Smart Folder - Quick Start Guide

## Super Quick Start (30 seconds)
```bash
make start    # Start backend
make desktop  # Start desktop app
```
Starts everything with simple commands!

## Alternative Quick Start
```bash
# Using Docker Compose
docker-compose up -d

# Start desktop app
cd desktop
npm start
```

## Manual Setup (5 minutes)

### Prerequisites
- Docker and Docker Compose
- Node.js (for desktop app)

### 1. Setup Backend
```bash
cd backend
docker-compose up -d
```

### 2. Setup Desktop App
```bash
cd desktop
npm install
npm start
```

### 3. Verify Setup
- Backend API: http://localhost:8003/health
- Desktop app should open automatically

## Available Commands

### Make Commands (Recommended)
```bash
make help     # Show all available commands
make start    # Start backend services
make desktop  # Start desktop app
make logs     # View backend logs
make stop     # Stop all services
make build    # Build services
make clean    # Clean up containers
make status   # Show service status
```

### Docker Commands
```bash
docker-compose up -d        # Start backend
docker-compose logs -f      # View logs
docker-compose down         # Stop services
docker-compose ps           # Show status
```

### Development Commands
```bash
# Backend development
cd backend
docker-compose up          # With logs

# Desktop development
cd desktop
npm run dev                # Development mode
```

## What's Working
- ✅ File scanning with metadata extraction
- ✅ Duplicate detection via SHA256 hashing
- ✅ Basic image similarity with perceptual hashing
- ✅ Desktop app with native folder selection
- ✅ Real-time scan progress updates
- ✅ Docker containerization
- ✅ Clean separated architecture

## Troubleshooting
- **Backend not starting**: Check if Docker is running
- **Desktop app not opening**: Run `npm install` in desktop folder
- **Port conflicts**: Backend uses port 8003, make sure it's available
- **Permission issues**: Make sure Docker has proper permissions