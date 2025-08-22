from fastapi import FastAPI, HTTPException, Depends
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from pydantic import BaseModel
import uvicorn
import subprocess
import os
from pathlib import Path

from .db.database import get_db, init_db
from .core.config import settings
from .core.logging import logger

# Create FastAPI app
app = FastAPI(
    title="RAG Smart Folder",
    description="Intelligent file management with duplicate detection and RAG capabilities",
    version="0.1.0"
)

# Add CORS middleware for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify your frontend domain
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Static files removed - using desktop app instead


@app.on_event("startup")
async def startup_event():
    """Initialize application on startup."""
    logger.info("Starting RAG Smart Folder application...")
    try:
        init_db()
        logger.info("Database initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        raise


@app.get("/", response_class=HTMLResponse)
async def root():
    """API status page."""
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>RAG Smart Folder API</title>
        <style>
            body { font-family: Arial, sans-serif; margin: 40px; }
            .container { max-width: 800px; margin: 0 auto; }
            .status { padding: 20px; background: #f0f0f0; border-radius: 5px; }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🚀 RAG Smart Folder API</h1>
            <div class="status">
                <h2>Status: Running ✅</h2>
                <p>Backend API is operational and ready for file processing.</p>
                <p><strong>Desktop App:</strong> Use the Electron desktop application to interact with this API</p>
                <p><strong>API Documentation:</strong> <a href="/docs">/docs</a></p>
                <p><strong>Health Check:</strong> <a href="/health">/health</a></p>
            </div>
        </div>
    </body>
    </html>
    """


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "service": "RAG Smart Folder"}


@app.get("/files")
async def list_files(db: Session = Depends(get_db)):
    """List all scanned files."""
    try:
        from .models.file import File
        files = db.query(File).all()
        return {
            "total_files": len(files),
            "files": [
                {
                    "id": f.id,
                    "name": f.file_name,
                    "path": f.file_path,
                    "size": f.file_size,
                    "type": f.file_type,
                    "added_at": f.added_at.isoformat() if f.added_at else None
                }
                for f in files
            ]
        }
    except Exception as e:
        logger.error(f"Error listing files: {e}")
        raise HTTPException(status_code=500, detail="Failed to list files")


class ScanRequest(BaseModel):
    folder_path: str
    recursive: bool = True
    find_duplicates: bool = True
    clear_previous: bool = True

@app.post("/scan")
async def scan_folder(request: ScanRequest):
    """Scan a folder for files and detect duplicates."""
    try:
        # Translate host path to container path
        container_path = request.folder_path
        if request.folder_path.startswith('/Users/shankaraswal/'):
            # Replace host home path with container mount point
            container_path = request.folder_path.replace('/Users/shankaraswal/', '/app/host_home/')
            logger.info(f"Translated path: {request.folder_path} -> {container_path}")
        
        # Validate folder path
        if not os.path.exists(container_path):
            raise HTTPException(status_code=400, detail=f"Folder path does not exist: {container_path} (original: {request.folder_path})")
        
        if not os.path.isdir(container_path):
            raise HTTPException(status_code=400, detail=f"Path is not a directory: {container_path} (original: {request.folder_path})")
        
        logger.info(f"Starting scan of folder: {container_path} (original: {request.folder_path})")
        
        # Clear previous data if requested
        if request.clear_previous:
            try:
                from .models.file import File
                db = next(get_db())
                db.query(File).delete()
                db.commit()
                db.close()
                logger.info("Previous scan data cleared")
            except Exception as e:
                logger.warning(f"Failed to clear previous data: {e}")
        
        # Build scanner command
        script_path = os.path.join(os.path.dirname(__file__), "..", "scripts", "scan_folder.py")
        cmd = [
            "python", script_path,
            "--path", container_path,
            "--db", "data/dev.db"
        ]
        
        if not request.recursive:
            cmd.append("--no-recursive")
        
        if request.find_duplicates:
            cmd.append("--duplicates")
        
        # Run scanner
        logger.info(f"Running command: {' '.join(cmd)}")
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)  # 5 minute timeout
        
        if result.returncode != 0:
            error_msg = result.stderr or result.stdout or "Unknown error"
            logger.error(f"Scanner failed with return code {result.returncode}: {error_msg}")
            raise HTTPException(status_code=500, detail=f"Scanner failed: {error_msg}")
        
        logger.info("Folder scan completed successfully")
        
        return {
            "status": "success",
            "message": "Folder scanned successfully",
            "output": result.stdout,
            "folder_path": request.folder_path,
            "recursive": request.recursive,
            "find_duplicates": request.find_duplicates
        }
        
    except subprocess.TimeoutExpired:
        logger.error("Scanner timeout")
        raise HTTPException(status_code=408, detail="Scanner timeout - folder too large")
    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        logger.error(f"Error scanning folder: {e}")
        logger.error(f"Full traceback: {error_details}")
        raise HTTPException(status_code=500, detail=f"Failed to scan folder: {str(e)}")


@app.get("/duplicates")
async def find_duplicates(db: Session = Depends(get_db)):
    """Find duplicate files based on SHA256 hash."""
    try:
        from .models.file import File
        from sqlalchemy import func
        
        # Find files with same SHA256 hash
        duplicates = db.query(
            File.sha256,
            func.count(File.id).label('count'),
            func.group_concat(File.file_path).label('paths')
        ).filter(
            File.sha256.isnot(None)
        ).group_by(
            File.sha256
        ).having(
            func.count(File.id) > 1
        ).all()
        
        return {
            "total_duplicate_groups": len(duplicates),
            "duplicates": [
                {
                    "hash": d.sha256,
                    "count": d.count,
                    "files": d.paths.split(',') if d.paths else []
                }
                for d in duplicates
            ]
        }
    except Exception as e:
        logger.error(f"Error finding duplicates: {e}")
        raise HTTPException(status_code=500, detail="Failed to find duplicates")


@app.delete("/clear")
async def clear_database(db: Session = Depends(get_db)):
    """Clear all scanned files from the database."""
    try:
        from .models.file import File
        
        # Count files before deletion
        file_count = db.query(File).count()
        
        # Delete all files
        db.query(File).delete()
        db.commit()
        
        logger.info(f"Cleared {file_count} files from database")
        
        return {
            "status": "success",
            "message": f"Database cleared successfully",
            "files_removed": file_count
        }
        
    except Exception as e:
        logger.error(f"Error clearing database: {e}")
        raise HTTPException(status_code=500, detail="Failed to clear database")


if __name__ == "__main__":
    uvicorn.run(
        "backend.app.main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=settings.debug
    )
