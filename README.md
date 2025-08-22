# RAG Smart Folder

A RAG-based application for intelligent file management, duplicate detection, and content analysis.

## Features (Planned)

- File scanning and metadata extraction
- Exact and near-duplicate file detection
- ML-based image similarity analysis
- RAG-powered content search and insights
- Safe duplicate removal with quarantine system

## 🚀 Quick Start

### Option 1: Everything at Once (Recommended)
```bash
./start-all.sh
```
This starts both backend (Docker) and desktop app automatically!

### Option 2: Backend Only (Development)
```bash
./start-docker.sh
```

### Option 3: Development Setup
```bash
# Setup Python environment
cd devops
./setup.sh

# Start backend manually
cd ../backend
python -m uvicorn app.main:app --reload
```
   pip install -r requirements.txt
   ```

3. Initialize database:
   ```bash
   sqlite3 data/dev.db < backend/sql/schema.sql
   ```

4. Test the scanner:
   ```bash
   python scripts/test_scanner.py
   python scripts/scan_folder.py --path "/path/to/folder" --db "data/dev.db" --duplicates
   ```

5. Start the API server:
   ```bash
   cd backend && python -m uvicorn app.main:app --reload
   ```

## Project Structure
```
RAG-smart-folder/
├── backend/           # Python FastAPI backend + scripts
├── desktop-app/       # Electron desktop application
├── devops/           # Docker & infrastructure setup
├── data/             # Database and data files
├── logs/             # Application logs
└── quarantine/       # Quarantined duplicate files
```

See [PROJECT-STRUCTURE.md](PROJECT-STRUCTURE.md) for detailed documentation.

## Current Features ✅

- [x] **Desktop App**: Clean Electron app with native folder selection
- [x] **FastAPI Backend**: RESTful API with Docker support
- [x] **Database**: SQLite with proper schema and indexing
- [x] **File Scanner**: Recursive scanning with metadata extraction
- [x] **Duplicate Detection**: SHA256 hashing for exact duplicates
- [x] **Perceptual Hashing**: Image similarity detection
- [x] **Real-time Updates**: Live scan progress and status
- [x] **Clean Architecture**: Organized 3-folder structure

## Quick Demo

1. **Start the app**: `python start_server.py`
2. **Open browser**: Go to `http://127.0.0.1:8000`
3. **Select folder**: Click "Choose Folder" and enter a folder path
4. **Scan**: Click "Start Scan" and watch the results!
