# RAG Smart Folder - Quick Start Guide

## Super Quick Start (30 seconds)
```bash
./start-all.sh
```
Starts backend + desktop app automatically!

## Manual Setup (5 minutes)
### 1. Setup Backend
```bash
cd devops
./setup.sh
```

### 2. Setup Desktop App
```bash
cd desktop-app
./setup.sh
```

### 3. Start Services
- Backend (Terminal 1):
  ```bash
  cd backend
  python -m uvicorn app.main:app --reload
  ```
- Desktop App (Terminal 2):
  ```bash
  cd desktop-app
  npm start
  ```

### 4. Test
```bash
python demo.py
```

## What's Working
- File scanning with metadata extraction.
- Duplicate detection via SHA256 hashing.
- Basic image similarity with perceptual hashing.