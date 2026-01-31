from fastapi import FastAPI, HTTPException, Depends
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from pydantic import BaseModel
import uvicorn
import subprocess
import os
from pathlib import Path
from datetime import datetime

from .db.database import get_db, init_db
from .core.config import settings
from .core.logging import logger

def translate_path_to_host(container_path: str) -> str:
    """Translate container path back to host path for desktop app."""
    if not container_path:
        return container_path
    
    # Handle Docker container path translation
    if container_path.startswith('/app/host_home/'):
        # Get the user's home directory from environment or use default
        import os
        user_home = os.environ.get('HOST_HOME_PATH', '/Users/shankaraswal/')
        if not user_home.endswith('/'):
            user_home += '/'
        return container_path.replace('/app/host_home/', user_home)
    
    # If it's already a host path, return as-is
    return container_path

def translate_path_to_container(host_path: str) -> str:
    """Translate host path to container path for scanning."""
    if not host_path:
        return host_path
    
    # Only translate if we're clearly in a Docker environment and the path needs translation
    # Be more conservative to avoid breaking existing functionality
    if host_path.startswith('/Users/shankaraswal/'):
        return host_path.replace('/Users/shankaraswal/', '/app/host_home/')
    
    # If it's already a container path or doesn't match our pattern, return as-is
    return host_path

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
        # Apply pending migrations to keep DB schema up-to-date
        try:
            from .db.migrations import MigrationManager
            db_path = settings.database_url.replace('sqlite:///','') if settings.database_url.startswith('sqlite') else 'data/dev.db'
            manager = MigrationManager(db_path)
            manager.apply_all_pending_migrations()
            logger.info("Database migrations applied (if any)")
        except Exception as e:
            logger.warning(f"Could not apply database migrations automatically: {e}")
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
                    "path": translate_path_to_host(f.file_path),
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
    scan_mode: str = "duplicates"  # "duplicates" or "similarity"
    similarity_threshold: float = 80.0

@app.post("/scan")
async def scan_folder(request: ScanRequest):
    """Scan a folder for files and detect duplicates with enhanced error reporting."""
    try:
        # Translate host path to container path
        container_path = translate_path_to_container(request.folder_path)
        logger.info(f"Original path: {request.folder_path}")
        logger.info(f"Container path: {container_path}")
        logger.info(f"Path translation occurred: {container_path != request.folder_path}")
        
        # Validate folder path
        logger.info(f"Checking if path exists: {container_path}")
        path_exists = os.path.exists(container_path)
        logger.info(f"Path exists: {path_exists}")
        
        if not path_exists:
            # Try the original path as fallback
            logger.info(f"Container path doesn't exist, trying original path: {request.folder_path}")
            if os.path.exists(request.folder_path):
                logger.info("Original path exists, using it instead")
                container_path = request.folder_path
            else:
                logger.error(f"Neither container path nor original path exists")
                raise HTTPException(status_code=400, detail=f"Folder path does not exist: {container_path} (original: {request.folder_path})")
        
        if not os.path.isdir(container_path):
            raise HTTPException(status_code=400, detail=f"Path is not a directory: {container_path} (original: {request.folder_path})")
        
        logger.info(f"Starting {request.scan_mode} scan of folder: {container_path} (original: {request.folder_path})")
        
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
        
        # Build enhanced scanner command with verbose output and error reporting
        script_path = os.path.join(os.path.dirname(__file__), "..", "scripts", "scan_folder.py")
        cmd = [
            "python", script_path,
            "--path", container_path,
            "--db", "data/dev.db",
            "--mode", request.scan_mode,
            "--verbose",  # Enable verbose logging
            "--show-errors",  # Show detailed error summary
            "--progress", "50"  # Show progress every 50 files
        ]
        
        if request.recursive:
            cmd.append("--recursive")
        
        if request.find_duplicates:
            cmd.append("--duplicates")
        
        if request.scan_mode == "similarity":
            cmd.extend(["--similarity-threshold", str(request.similarity_threshold)])
        
        # Run scanner with enhanced output capture
        logger.info(f"Running enhanced scanner command: {' '.join(cmd)}")
        logger.info(f"Working directory: {os.getcwd()}")
        logger.info(f"Script path exists: {os.path.exists(script_path)}")
        
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)  # 10 minute timeout for large folders
        
        # Parse scanner output for statistics and errors
        scan_output = result.stdout
        scan_errors = result.stderr
        
        logger.info(f"Scanner return code: {result.returncode}")
        logger.info(f"Scanner stdout length: {len(scan_output) if scan_output else 0}")
        logger.info(f"Scanner stderr length: {len(scan_errors) if scan_errors else 0}")
        
        if scan_output:
            logger.info(f"Scanner stdout (first 500 chars): {scan_output[:500]}")
        if scan_errors:
            logger.info(f"Scanner stderr (first 500 chars): {scan_errors[:500]}")
        
        # Extract statistics from output (basic parsing)
        stats = {
            "total_files": 0,
            "processed_files": 0,
            "skipped_files": 0,
            "errors": 0,
            "success_rate": 0.0,
            "scan_duration": 0.0
        }
        
        # Simple parsing of scan summary
        if "Total files found:" in scan_output:
            try:
                for line in scan_output.split('\n'):
                    if "Total files found:" in line:
                        stats["total_files"] = int(line.split(':')[1].strip().replace(',', ''))
                    elif "Successfully processed:" in line:
                        stats["processed_files"] = int(line.split(':')[1].strip().replace(',', ''))
                    elif "Files skipped:" in line or "Total skipped:" in line:
                        stats["skipped_files"] = int(line.split(':')[1].strip().replace(',', ''))
                    elif "Errors encountered:" in line:
                        stats["errors"] = int(line.split(':')[1].strip().replace(',', ''))
                    elif "Success Rate:" in line:
                        stats["success_rate"] = float(line.split(':')[1].strip().replace('%', ''))
                    elif "Scan duration:" in line or "scan completed in" in line:
                        # Extract duration from various formats
                        if "seconds" in line:
                            duration_str = line.split('seconds')[0].split()[-1]
                            stats["scan_duration"] = float(duration_str.replace('s', ''))
            except (ValueError, IndexError) as e:
                logger.warning(f"Could not parse scan statistics: {e}")
        
        if result.returncode != 0:
            error_msg = scan_errors or scan_output or "Unknown scanner error"
            logger.error(f"Scanner failed with return code {result.returncode}: {error_msg}")
            
            # Return detailed error information
            return {
                "status": "error",
                "message": "Scanner completed with errors",
                "error_details": error_msg,
                "output": scan_output,
                "statistics": stats,
                "folder_path": request.folder_path,
                "recursive": request.recursive,
                "scan_mode": request.scan_mode
            }
        
        logger.info("Folder scan completed successfully")
        
        return {
            "status": "success",
            "message": "Folder scanned successfully",
            "output": scan_output,
            "statistics": stats,
            "folder_path": request.folder_path,
            "recursive": request.recursive,
            "find_duplicates": request.find_duplicates,
            "scan_mode": request.scan_mode,
            "similarity_threshold": request.similarity_threshold if request.scan_mode == "similarity" else None
        }
        
    except subprocess.TimeoutExpired:
        logger.error("Scanner timeout - folder may be too large")
        raise HTTPException(status_code=408, detail="Scanner timeout - folder too large or contains many files")
    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        logger.error(f"Error scanning folder: {e}")
        logger.error(f"Full traceback: {error_details}")
        raise HTTPException(status_code=500, detail=f"Failed to scan folder: {str(e)}")


@app.get("/duplicates")
async def find_duplicates(
    mode: str = "exact",
    confidence_threshold: float = 80.0,
    similarity_threshold: float = 80.0,
    db: Session = Depends(get_db)
):
    """Find duplicate files using basic database queries."""
    try:
        from .models.file import File
        from sqlalchemy import func
        
        # Get duplicate files using basic SHA256 grouping
        duplicates_query = db.query(
            File.sha256,
            func.count(File.id).label('count'),
            func.group_concat(File.id).label('file_ids')
        ).filter(
            File.sha256.isnot(None)
        ).group_by(
            File.sha256
        ).having(
            func.count(File.id) > 1
        ).all()
        
        duplicate_groups = []
        total_duplicates = 0
        
        for i, (sha256, count, file_ids_str) in enumerate(duplicates_query):
            file_ids = [int(fid) for fid in file_ids_str.split(',')]
            
            # Get file details for this group
            files = db.query(File).filter(File.id.in_(file_ids)).all()
            
            group_files = []
            for file in files:
                group_files.append({
                    "id": file.id,
                    "path": translate_path_to_host(file.file_path),
                    "name": file.file_name,
                    "size": file.file_size,
                    "type": file.file_type,
                    "is_original": False,  # Basic detection doesn't determine original
                    "confidence_score": 100.0,  # SHA256 matches are 100% confident
                    "detection_reasons": ["sha256_match"]
                })
            
            # Mark smallest file as original
            if group_files:
                smallest_file = min(group_files, key=lambda f: f["size"] or 0)
                smallest_file["is_original"] = True
                smallest_file["detection_reasons"].append("smallest_file")
            
            duplicate_groups.append({
                "id": f"group_{i+1}_{sha256[:8]}",
                "detection_method": "sha256",
                "confidence_score": 100.0,
                "similarity_percentage": 100.0,
                "file_count": count,
                "total_size": sum(f["size"] for f in group_files if f["size"]),
                "files": group_files
            })
            
            total_duplicates += count
        
        return {
            "session_id": f"basic_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            "detection_mode": "basic",
            "summary": {
                "total_files_scanned": db.query(File).count(),
                "total_groups_found": len(duplicate_groups),
                "total_duplicates_found": total_duplicates,
                "detection_time_ms": 0,
                "success_rate": 100.0,
                "duplicate_percentage": (total_duplicates / db.query(File).count() * 100) if db.query(File).count() > 0 else 0
            },
            "configuration": {
                "confidence_threshold": confidence_threshold,
                "similarity_threshold": similarity_threshold,
                "detection_mode": "basic"
            },
            "algorithm_performance": {"basic_sha256": {"files_processed": db.query(File).count()}},
            "duplicate_groups": duplicate_groups,
            "errors": []
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error finding duplicates: {e}")
        raise HTTPException(status_code=500, detail="Failed to find duplicates")


@app.get("/images/cosine-similarity")
async def get_cosine_similar_images(similarity_threshold: float = 80.0):
    """Get similar images using cosine similarity analysis."""
    try:
        import subprocess
        
        # Run cosine similarity analysis
        script_path = os.path.join(os.path.dirname(__file__), "..", "scripts", "scan_folder.py")
        cmd = [
            "python", script_path,
            "--path", "/tmp",  # Dummy path since we're analyzing existing data
            "--db", "data/dev.db",
            "--mode", "similarity",
            "--similarity-threshold", str(similarity_threshold)
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        
        if result.returncode != 0:
            error_msg = result.stderr or result.stdout or "Cosine similarity analysis failed"
            logger.error(f"Cosine similarity failed: {error_msg}")
            raise HTTPException(status_code=500, detail=f"Analysis failed: {error_msg}")
        
        # Parse the output to extract similar groups
        # For now, return a simple response
        return {
            "status": "success",
            "message": "Cosine similarity analysis completed",
            "threshold": similarity_threshold,
            "output": result.stdout
        }
        
    except subprocess.TimeoutExpired:
        logger.error("Cosine similarity analysis timeout")
        raise HTTPException(status_code=408, detail="Analysis timeout")
    except Exception as e:
        logger.error(f"Error in cosine similarity analysis: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to analyze similarity: {str(e)}")


@app.get("/images")
async def get_images(
    similarity_threshold: float = 80.0, 
    detection_mode: str = "similar",
    db: Session = Depends(get_db)
):
    """Get all image files with enhanced similarity analysis."""
    try:
        from .models.file import File
        from .services.duplicate_detection_service import DuplicateDetectionService
        from .core.detection.models import DetectionConfig
        from sqlalchemy import func
        
        # Get all image files
        image_extensions = ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff', '.webp']
        images = db.query(File).filter(
            func.lower(File.file_type).in_(image_extensions)
        ).all()
        
        # Create detection service and run similarity detection
        detection_service = DuplicateDetectionService(db)
        
        # Filter to only image files
        file_filters = {
            'file_types': image_extensions
        }
        
        if detection_mode == "similar":
            results = detection_service.detect_duplicates_similar(
                similarity_threshold=similarity_threshold,
                file_filters=file_filters
            )
        elif detection_mode == "exact":
            results = detection_service.detect_duplicates_exact(file_filters=file_filters)
        elif detection_mode == "comprehensive":
            config = DetectionConfig(
                perceptual_threshold=similarity_threshold,
                min_confidence_threshold=similarity_threshold
            )
            results = detection_service.detect_duplicates_comprehensive(
                config=config,
                file_filters=file_filters
            )
        else:
            raise HTTPException(status_code=400, detail=f"Invalid detection mode: {detection_mode}")
        
        # Format similar groups
        similar_groups = []
        for group in results.groups:
            group_data = {
                "id": group.id,
                "detection_method": group.detection_method.value,
                "type": "exact" if group.confidence_score == 100.0 else "similar",
                "confidence_score": group.confidence_score,
                "avg_similarity": group.similarity_percentage,
                "min_similarity": min(f.confidence_score for f in group.files),
                "max_similarity": max(f.confidence_score for f in group.files),
                "count": len(group.files),
                "total_size": sum(f.file_size for f in group.files if f.file_size),
                "images": [
                    {
                        "id": f.file_id,
                        "name": f.file_name,
                        "path": translate_path_to_host(f.file_path),
                        "size": f.file_size,
                        "dimensions": f"{f.width}x{f.height}" if f.width and f.height else None,
                        "perceptual_hash": f.perceptual_hash,
                        "similarity": f.confidence_score,
                        "is_original": f.is_original,
                        "detection_reasons": f.detection_reasons
                    }
                    for f in group.files
                ]
            }
            similar_groups.append(group_data)
        
        return {
            "session_id": results.session_id,
            "detection_mode": results.detection_mode.value,
            "total_images": len(images),
            "images_analyzed": results.total_files_scanned,
            "similar_groups": len(similar_groups),
            "similarity_threshold": similarity_threshold,
            "detection_time_ms": results.detection_time_ms,
            "algorithm_performance": results.algorithm_performance,
            "images": [
                {
                    "id": img.id,
                    "name": img.file_name,
                    "path": translate_path_to_host(img.file_path),
                    "size": img.file_size,
                    "type": img.file_type,
                    "dimensions": f"{img.width}x{img.height}" if img.width and img.height else None,
                    "perceptual_hash": img.perceptual_hash,
                    "added_at": img.added_at.isoformat() if img.added_at else None
                }
                for img in images
            ],
            "similar_images": similar_groups,
            "errors": results.errors
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting images: {e}")
        raise HTTPException(status_code=500, detail="Failed to get images")


@app.get("/scan/statistics")
async def get_scan_statistics(db: Session = Depends(get_db)):
    """Get detailed scan statistics and database information."""
    try:
        from .models.file import File
        from sqlalchemy import func
        
        # Get basic file counts
        total_files = db.query(File).count()
        
        # Get file type distribution
        file_types = db.query(
            File.file_type,
            func.count(File.id).label('count')
        ).group_by(File.file_type).all()
        
        # Get size statistics
        size_stats = db.query(
            func.sum(File.file_size).label('total_size'),
            func.avg(File.file_size).label('avg_size'),
            func.max(File.file_size).label('max_size'),
            func.min(File.file_size).label('min_size')
        ).first()
        
        # Get duplicate statistics
        duplicates = db.query(
            File.sha256,
            func.count(File.id).label('count')
        ).filter(
            File.sha256.isnot(None)
        ).group_by(
            File.sha256
        ).having(
            func.count(File.id) > 1
        ).all()
        
        # Get image statistics
        image_extensions = ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff', '.webp']
        image_count = db.query(File).filter(
            func.lower(File.file_type).in_(image_extensions)
        ).count()
        
        images_with_hash = db.query(File).filter(
            func.lower(File.file_type).in_(image_extensions),
            File.perceptual_hash.isnot(None)
        ).count()
        
        return {
            "database_statistics": {
                "total_files": total_files,
                "total_duplicates": len(duplicates),
                "duplicate_files": sum(d.count for d in duplicates),
                "total_images": image_count,
                "images_with_perceptual_hash": images_with_hash
            },
            "size_statistics": {
                "total_size": int(size_stats.total_size or 0),
                "average_size": int(size_stats.avg_size or 0),
                "largest_file": int(size_stats.max_size or 0),
                "smallest_file": int(size_stats.min_size or 0)
            },
            "file_type_distribution": [
                {
                    "extension": ft.file_type or "unknown",
                    "count": ft.count
                }
                for ft in file_types
            ]
        }
        
    except Exception as e:
        logger.error(f"Error getting scan statistics: {e}")
        raise HTTPException(status_code=500, detail="Failed to get scan statistics")


@app.get("/scan/test-connection")
async def test_scanner_connection():
    """Test scanner script connection and dependencies."""
    try:
        script_path = os.path.join(os.path.dirname(__file__), "..", "scripts", "scan_folder.py")
        
        # Test database connection
        cmd = [
            "python", script_path,
            "--test-db",
            "--db", "data/dev.db"
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        
        return {
            "status": "success" if result.returncode == 0 else "error",
            "scanner_available": result.returncode == 0,
            "output": result.stdout,
            "errors": result.stderr,
            "return_code": result.returncode
        }
        
    except subprocess.TimeoutExpired:
        return {
            "status": "error",
            "scanner_available": False,
            "error": "Scanner test timeout"
        }
    except Exception as e:
        logger.error(f"Error testing scanner connection: {e}")
        return {
            "status": "error",
            "scanner_available": False,
            "error": str(e)
        }


@app.get("/debug/paths")
async def debug_paths(db: Session = Depends(get_db)):
    """Debug endpoint to check path translations and sample file paths."""
    try:
        from .models.file import File
        
        # Get a few sample files
        sample_files = db.query(File).limit(5).all()
        
        # Get environment info
        import os
        
        return {
            "environment": {
                "HOST_HOME_PATH": os.environ.get('HOST_HOME_PATH', 'not set'),
                "current_working_directory": os.getcwd(),
                "container_paths_detected": any(f.file_path.startswith('/app/host_home/') for f in sample_files)
            },
            "sample_files": [
                {
                    "id": f.id,
                    "original_path": f.file_path,
                    "translated_path": translate_path_to_host(f.file_path),
                    "file_exists_original": os.path.exists(f.file_path),
                    "file_exists_translated": os.path.exists(translate_path_to_host(f.file_path))
                }
                for f in sample_files
            ],
            "path_translation_test": {
                "container_to_host": {
                    "/app/host_home/Pictures/test.jpg": translate_path_to_host("/app/host_home/Pictures/test.jpg")
                },
                "host_to_container": {
                    "/Users/shankaraswal/Pictures/test.jpg": translate_path_to_container("/Users/shankaraswal/Pictures/test.jpg")
                }
            }
        }
        
    except Exception as e:
        logger.error(f"Error in debug paths: {e}")
        return {
            "error": str(e),
            "environment": {
                "current_working_directory": os.getcwd()
            }
        }


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
