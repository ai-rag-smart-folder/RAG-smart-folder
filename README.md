# RAG Smart Folder

A RAG-based application for intelligent file management, duplicate detection, and content analysis.

## Features

- File scanning and metadata extraction
- Exact and near-duplicate file detection
- ML-based image similarity analysis
- RAG-powered content search and insights
- Safe duplicate removal with quarantine system
- Clean desktop interface with Electron
- Dockerized backend for easy deployment

## 🚀 Quick Start

### Option 1: Using Make (Recommended)
```bash
# Start backend services
make start

# Start desktop app
make desktop

# View logs
make logs

# Stop everything
make stop

# See all commands
make help
```

### Option 2: Using Docker Compose
```bash
# Start backend
docker-compose up -d

# View logs
docker-compose logs -f

# Stop
docker-compose down
```

### Option 3: Manual Development
```bash
# Backend
cd backend
docker-compose up -d

# Desktop App
cd desktop
npm install
npm start
```

## Project Structure
```
RAG-smart-folder/
├── repos/                    # Clean separated codebases
│   ├── backend/    # Python FastAPI backend
│   └── desktop/    # Electron desktop app
├── data/                     # Database and data files
├── logs/                     # Application logs
├── quarantine/               # Quarantined duplicate files
├── docs/                     # Documentation
├── docker-compose.yml        # Container orchestration
├── Makefile                  # Easy commands
└── README.md                 # This file
```

See [docs/Project_Structure_and_Architecture.markdown](docs/Project_Structure_and_Architecture.markdown) for detailed documentation.

## Current Features ✅

- [x] **Desktop App**: Clean Electron app with native folder selection
- [x] **FastAPI Backend**: RESTful API with Docker support
- [x] **Database**: SQLite with proper schema and indexing
- [x] **File Scanner**: Recursive scanning with metadata extraction
- [x] **Duplicate Detection**: SHA256 hashing for exact duplicates
- [x] **Perceptual Hashing**: Image similarity detection
- [x] **Real-time Updates**: Live scan progress and status
- [x] **Clean Architecture**: Separated codebases for better maintainability
- [x] **Docker Support**: Containerized backend with easy deployment
- [x] **Make Commands**: Simple commands for development workflow

## Quick Demo

1. **Start the backend**: `make start`
2. **Start desktop app**: `make desktop`
3. **Select folder**: Use the desktop app to choose a folder
4. **Scan**: Click "Start Scan" and watch the results!

## API Endpoints

- `GET /health` - Health check
- `POST /scan` - Start folder scan
- `GET /files` - List scanned files
- `GET /duplicates` - Get duplicate files
- `DELETE /files/{file_id}` - Delete file

Backend runs on: `http://localhost:8003`

## Development

Each codebase is independent and can be developed separately:

- **Backend**: `backend/`
- **Desktop**: `desktop/`

See individual README files in each repo for specific development instructions.
