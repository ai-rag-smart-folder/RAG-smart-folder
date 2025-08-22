# 🚀 Quick Start Guide

## Super Quick Start (30 seconds)

### Everything at Once
```bash
./start-all.sh
```
Starts backend + desktop app automatically!

### Individual Components
```bash
./start-docker.sh     # Backend only (for development)
./stop-all.sh         # Stop everything
```

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
```bash
# Backend (terminal 1)
cd backend
python -m uvicorn app.main:app --reload

# Desktop App (terminal 2)
cd desktop-app
npm start
```

### 4. Test Everything
```bash
# In another terminal (with venv activated)
python demo.py
```

## What's Working Now

✅ **File Scanner**: Recursively scans folders, extracts metadata, computes SHA256 hashes  
✅ **Duplicate Detection**: Finds exact duplicates based on file content  
✅ **Database**: SQLite with proper schema for files, duplicates, quarantine  
✅ **API**: FastAPI with endpoints for files, duplicates, health check  
✅ **Metadata Extraction**: File size, dates, MIME types, EXIF data for images  
✅ **Perceptual Hashing**: Image similarity detection (basic)  

## Current Features

- **Scan any folder** and extract comprehensive metadata
- **Detect exact duplicates** using SHA256 hashing
- **Web API** with interactive documentation at `/docs`
- **Database storage** with proper indexing
- **Logging** and error handling
- **Configuration** via environment variables

## Next Steps (Week 2)

- [ ] Add quarantine functionality (move duplicates to quarantine folder)
- [ ] Implement undo/recovery system
- [ ] Add web UI for file management
- [ ] Enhance perceptual hashing with configurable thresholds
- [ ] Add file preview capabilities

## Troubleshooting

### Common Issues

1. **Permission Denied**: Make sure you have read access to the folder you want to scan
2. **Dependencies Missing**: Run `pip install -r requirements.txt` manually
3. **Database Errors**: Delete `data/dev.db` and run setup again
4. **Port Already in Use**: Change port in `backend/app/core/config.py` or kill existing process

### Getting Help

- Check logs in `logs/app.log`
- Use `--dry-run` flag with scanner to test without changes
- API documentation at `http://127.0.0.1:8000/docs`

## Development Commands

```bash
# Activate environment
source .venv/bin/activate

# Run tests
python -m pytest tests/

# Format code
black backend/ scripts/

# Lint code
flake8 backend/ scripts/

# Start development server
cd backend && python -m uvicorn app.main:app --reload
```

Happy coding! 🎉
