# RAG Smart Folder - Backend API

A FastAPI-based backend service for intelligent file management with duplicate detection and RAG capabilities.

## Features

- 🔍 **File Scanning**: Recursively scan folders and extract metadata
- 🔗 **Duplicate Detection**: SHA256-based exact duplicate detection
- 🖼️ **Image Analysis**: Perceptual hashing and EXIF data extraction
- 📊 **RESTful API**: Complete REST API for file management
- 🗄️ **SQLite Database**: Lightweight database for file metadata
- 🐳 **Docker Ready**: Containerized deployment support

## Supported File Types

**All file types are supported** including:
- Archives: `.zip`, `.tar`, `.rar`, `.7z`
- Documents: `.pdf`, `.doc`, `.docx`, `.txt`
- Images: `.jpg`, `.png`, `.gif`, `.bmp`
- Videos: `.mp4`, `.mov`, `.avi`, `.mkv`
- Audio: `.mp3`, `.wav`, `.flac`
- Code: `.py`, `.js`, `.html`, `.css`
- And any other file format!

## Quick Start

### Local Development

1. **Install Dependencies**
   ```bash
   pip install -r requirements.txt
   ```

2. **Run the Server**
   ```bash
   uvicorn app.main:app --host 0.0.0.0 --port 8003 --reload
   ```

3. **Access API Documentation**
   - Swagger UI: http://localhost:8003/docs
   - ReDoc: http://localhost:8003/redoc

### Docker Deployment

```bash
docker build -t rag-backend .
docker run -p 8003:8003 -v $(pwd)/data:/app/data rag-backend
```

## API Endpoints

### Core Endpoints
- `GET /` - API status page
- `GET /health` - Health check
- `GET /docs` - API documentation

### File Management
- `POST /scan` - Scan folder for files
- `GET /files` - List all scanned files
- `GET /duplicates` - Find duplicate files
- `DELETE /clear` - Clear database

### Scan Request Example

```json
{
  "folder_path": "/path/to/scan",
  "recursive": true,
  "find_duplicates": true,
  "clear_previous": true
}
```

## Configuration

Environment variables:
- `API_HOST` - Server host (default: 0.0.0.0)
- `API_PORT` - Server port (default: 8003)
- `DATABASE_URL` - Database connection string
- `LOG_LEVEL` - Logging level (INFO, DEBUG, ERROR)
- `DEBUG` - Enable debug mode (true/false)

## Integration

This backend is designed to work with multiple frontends:
- **Desktop App**: Electron-based desktop application
- **Web App**: React/Vue/Angular web applications
- **Mobile App**: React Native/Flutter mobile applications
- **CLI Tools**: Command-line interfaces

## API Client Examples

### Python
```python
import requests

# Scan a folder
response = requests.post('http://localhost:8003/scan', json={
    'folder_path': '/path/to/scan',
    'recursive': True,
    'find_duplicates': True
})
print(response.json())
```

### JavaScript
```javascript
// Scan a folder
const response = await fetch('http://localhost:8003/scan', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
        folder_path: '/path/to/scan',
        recursive: true,
        find_duplicates: true
    })
});
const result = await response.json();
```

### cURL
```bash
curl -X POST "http://localhost:8003/scan" \
  -H "Content-Type: application/json" \
  -d '{
    "folder_path": "/path/to/scan",
    "recursive": true,
    "find_duplicates": true
  }'
```

## License

MIT License - see LICENSE file for details.