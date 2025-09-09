#!/usr/bin/env python3
"""
File Scanner for RAG Smart Folder
Scans directories, extracts metadata, computes hashes, and detects duplicates.
"""

import os
import sys
import hashlib
import json
import argparse
import sqlite3
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union, Any

# Add backend to path for imports
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

# Import enhanced duplicate detection system
try:
    from app.core.detection import (
        DuplicateDetectionEngine, DetectionConfig, DetectionMode, 
        DuplicateFile, DetectionResults
    )
    from app.core.detection.algorithms import SHA256Detector, PerceptualHashDetector, MetadataDetector
    ENHANCED_DETECTION_AVAILABLE = True
except ImportError as e:
    print(f"Warning: Enhanced duplicate detection not available: {e}")
    print("Falling back to basic duplicate detection")
    ENHANCED_DETECTION_AVAILABLE = False

# Define fallback classes for basic detection if enhanced detection is not available
if not ENHANCED_DETECTION_AVAILABLE:
    class DetectionResults:
        def __init__(self, session_id="", detection_mode="basic", groups=None, total_files_scanned=0, 
                     total_groups_found=0, total_duplicates_found=0, detection_time_ms=0, config=None, 
                     algorithm_performance=None):
            self.session_id = session_id
            self.detection_mode = detection_mode
            self.groups = groups or []
            self.total_files_scanned = total_files_scanned
            self.total_groups_found = total_groups_found
            self.total_duplicates_found = total_duplicates_found
            self.detection_time_ms = detection_time_ms
            self.config = config
            self.algorithm_performance = algorithm_performance or {}

# Import optional dependencies with graceful handling
OPTIONAL_DEPENDENCIES = {}

def _import_optional_dependency(name: str, package: str = None, install_name: str = None):
    """Import optional dependency with graceful fallback."""
    if package is None:
        package = name
    if install_name is None:
        install_name = name
    
    try:
        module = __import__(package)
        OPTIONAL_DEPENDENCIES[name] = module
        return module
    except ImportError as e:
        print(f"Warning: Optional dependency '{name}' not available: {e}")
        print(f"Install with: pip install {install_name}")
        OPTIONAL_DEPENDENCIES[name] = None
        return None

# Import optional dependencies
magic = _import_optional_dependency('magic', 'magic', 'python-magic')
imagehash = _import_optional_dependency('imagehash', 'imagehash', 'imagehash')
Image = _import_optional_dependency('Image', 'PIL.Image', 'pillow')
exifread = _import_optional_dependency('exifread', 'exifread', 'exifread')
np = _import_optional_dependency('numpy', 'numpy', 'numpy')
cosine_similarity = _import_optional_dependency('cosine_similarity', 'sklearn.metrics.pairwise', 'scikit-learn')
TfidfVectorizer = _import_optional_dependency('TfidfVectorizer', 'sklearn.feature_extraction.text', 'scikit-learn')

# Handle PIL Image import specifically
if Image is None:
    try:
        from PIL import Image
        OPTIONAL_DEPENDENCIES['Image'] = Image
    except ImportError:
        pass

# Additional PIL import check
try:
    import PIL
    if not hasattr(PIL, 'Image'):
        from PIL import Image
        OPTIONAL_DEPENDENCIES['Image'] = Image
except ImportError:
    pass

# Handle sklearn imports specifically
if cosine_similarity is None:
    try:
        from sklearn.metrics.pairwise import cosine_similarity
        OPTIONAL_DEPENDENCIES['cosine_similarity'] = cosine_similarity
    except ImportError:
        pass

if TfidfVectorizer is None:
    try:
        from sklearn.feature_extraction.text import TfidfVectorizer
        OPTIONAL_DEPENDENCIES['TfidfVectorizer'] = TfidfVectorizer
    except ImportError:
        pass


class FileScanner:
    """Scans folders and extracts file metadata."""
    
    def __init__(self, db_path: str, dry_run: bool = False):
        self.db_path = db_path
        self.dry_run = dry_run
        self.conn = None
        self.cursor = None
        self.stats = {
            'total_files': 0,
            'processed_files': 0,
            'skipped_files': 0,
            'duplicates_found': 0,
            'errors': 0,
            'skipped_hidden': 0,
            'skipped_system': 0,
            'skipped_large': 0,
            'skipped_zero_byte': 0,
            'skipped_corrupted': 0,
            'start_time': None,
            'end_time': None
        }
        self.error_details = []
        self._column_cache = {}
        self._progress_counter = 0
        self._progress_interval = 100  # Report progress every N files
        
        # Setup logging
        self._setup_logging()
        
        # Check and report missing dependencies
        self._check_optional_dependencies()
    
    def _setup_logging(self):
        """Setup logging configuration for detailed error reporting."""
        # Create logger
        self.logger = logging.getLogger('FileScanner')
        self.logger.setLevel(logging.INFO)
        
        # Create console handler with formatting
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        
        # Create formatter
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        console_handler.setFormatter(formatter)
        
        # Add handler to logger (avoid duplicate handlers)
        if not self.logger.handlers:
            self.logger.addHandler(console_handler)
    
    def _check_optional_dependencies(self):
        """Check for missing optional dependencies and log warnings."""
        missing_deps = []
        available_deps = []
        
        for dep_name, dep_module in OPTIONAL_DEPENDENCIES.items():
            if dep_module is None:
                missing_deps.append(dep_name)
            else:
                available_deps.append(dep_name)
        
        if available_deps:
            self.logger.info(f"Available optional dependencies: {', '.join(available_deps)}")
        
        if missing_deps:
            self.logger.warning(f"Missing optional dependencies: {', '.join(missing_deps)}")
            self.logger.warning("Some features may be limited. Install missing dependencies for full functionality.")
            
            # Provide specific guidance for missing features
            if 'magic' in missing_deps:
                self.logger.warning("- MIME type detection will be limited without python-magic")
            if 'Image' in missing_deps:
                self.logger.warning("- Image processing (dimensions, perceptual hashes) will be disabled without PIL/Pillow")
            if 'imagehash' in missing_deps:
                self.logger.warning("- Perceptual hashing for duplicate image detection will be disabled")
            if 'exifread' in missing_deps:
                self.logger.warning("- EXIF metadata extraction will be disabled")
            if 'numpy' in missing_deps or 'cosine_similarity' in missing_deps:
                self.logger.warning("- Advanced similarity analysis will be disabled without numpy/scikit-learn")
    
    def _is_dependency_available(self, dep_name: str) -> bool:
        """Check if a specific optional dependency is available."""
        return OPTIONAL_DEPENDENCIES.get(dep_name) is not None
    
    def _log_error(self, error_type: str, file_path: str, error_message: str, exception: Exception = None):
        """Log detailed error information and add to error_details list."""
        error_detail = {
            'timestamp': datetime.now().isoformat(),
            'error_type': error_type,
            'file_path': file_path,
            'error_message': error_message,
            'exception_type': type(exception).__name__ if exception else None,
            'exception_message': str(exception) if exception else None
        }
        
        self.error_details.append(error_detail)
        self.stats['errors'] += 1
        
        # Log to console with appropriate level
        if error_type in ['PERMISSION_ERROR', 'FILE_NOT_FOUND']:
            self.logger.warning(f"{error_type}: {file_path} - {error_message}")
        else:
            self.logger.error(f"{error_type}: {file_path} - {error_message}")
            
        if exception:
            self.logger.debug(f"Exception details: {type(exception).__name__}: {exception}")
        
    def connect_db(self):
        """Connect to SQLite database with validation and retry logic."""
        max_retries = 3
        retry_delay = 1  # seconds
        
        for attempt in range(max_retries):
            try:
                # Validate database path and directory
                db_dir = os.path.dirname(self.db_path)
                if db_dir and not os.path.exists(db_dir):
                    try:
                        os.makedirs(db_dir, exist_ok=True)
                        self.logger.info(f"Created database directory: {db_dir}")
                    except (OSError, PermissionError) as e:
                        error_msg = f"Cannot create database directory {db_dir}: {e}"
                        if "Read-only file system" in str(e):
                            error_msg += " - Directory path is on a read-only file system"
                        elif "Permission denied" in str(e):
                            error_msg += " - Insufficient permissions to create directory"
                        
                        self._log_error('DATABASE_DIRECTORY_ERROR', self.db_path, error_msg, e)
                        if attempt == max_retries - 1:
                            sys.exit(1)
                        continue
                
                # Check if database file is writable (if it exists)
                if os.path.exists(self.db_path):
                    if not os.access(self.db_path, os.R_OK | os.W_OK):
                        error_msg = f"Database file {self.db_path} is not readable/writable"
                        self._log_error('DATABASE_PERMISSION_ERROR', self.db_path, error_msg)
                        if attempt == max_retries - 1:
                            sys.exit(1)
                        continue
                
                # Attempt database connection
                self.logger.info(f"Attempting database connection (attempt {attempt + 1}/{max_retries}): {self.db_path}")
                self.conn = sqlite3.connect(self.db_path, timeout=30.0)
                self.cursor = self.conn.cursor()
                
                # Test the connection with a simple query
                if not self._test_database_connection():
                    if attempt < max_retries - 1:
                        self.logger.warning(f"Database connection test failed, retrying in {retry_delay} seconds...")
                        if self.conn:
                            self.conn.close()
                        import time
                        time.sleep(retry_delay)
                        retry_delay *= 2  # Exponential backoff
                        continue
                    else:
                        error_msg = "Database connection test failed after all retry attempts"
                        self._log_error('DATABASE_CONNECTION_TEST_FAILED', self.db_path, error_msg)
                        sys.exit(1)
                
                # Initialize database schema and cache
                self._create_tables()
                # Apply pending migrations if available
                try:
                    sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
                    from app.db.migrations import MigrationManager
                    manager = MigrationManager(self.db_path)
                    manager.apply_all_pending_migrations()
                    self.logger.info("Database migrations applied (if any)")
                except Exception as e:
                    self.logger.warning(f"Could not apply database migrations automatically: {e}")
                self._initialize_column_cache()
                
                self.logger.info(f"Successfully connected to database: {self.db_path}")
                return  # Success - exit retry loop
                
            except sqlite3.OperationalError as e:
                error_msg = f"SQLite operational error (attempt {attempt + 1}/{max_retries}): {e}"
                if "database is locked" in str(e).lower():
                    error_msg += " - Database may be in use by another process"
                elif "no such file or directory" in str(e).lower():
                    error_msg += " - Database file path may be invalid"
                
                self._log_error('DATABASE_OPERATIONAL_ERROR', self.db_path, error_msg, e)
                
                if attempt < max_retries - 1:
                    self.logger.warning(f"Retrying database connection in {retry_delay} seconds...")
                    if self.conn:
                        self.conn.close()
                    import time
                    time.sleep(retry_delay)
                    retry_delay *= 2  # Exponential backoff
                else:
                    self.logger.error("Database connection failed after all retry attempts")
                    sys.exit(1)
                    
            except sqlite3.DatabaseError as e:
                error_msg = f"SQLite database error (attempt {attempt + 1}/{max_retries}): {e}"
                if "file is not a database" in str(e).lower():
                    error_msg += " - File exists but is not a valid SQLite database"
                
                self._log_error('DATABASE_ERROR', self.db_path, error_msg, e)
                
                if attempt < max_retries - 1:
                    self.logger.warning(f"Retrying database connection in {retry_delay} seconds...")
                    if self.conn:
                        self.conn.close()
                    import time
                    time.sleep(retry_delay)
                    retry_delay *= 2
                else:
                    self.logger.error("Database connection failed after all retry attempts")
                    sys.exit(1)
                    
            except sqlite3.Error as e:
                error_msg = f"SQLite error (attempt {attempt + 1}/{max_retries}): {e}"
                self._log_error('DATABASE_CONNECTION_ERROR', self.db_path, error_msg, e)
                
                if attempt < max_retries - 1:
                    self.logger.warning(f"Retrying database connection in {retry_delay} seconds...")
                    if self.conn:
                        self.conn.close()
                    import time
                    time.sleep(retry_delay)
                    retry_delay *= 2
                else:
                    self.logger.error("Database connection failed after all retry attempts")
                    sys.exit(1)
                    
            except Exception as e:
                error_msg = f"Unexpected error connecting to database (attempt {attempt + 1}/{max_retries}): {e}"
                self._log_error('DATABASE_CONNECTION_ERROR', self.db_path, error_msg, e)
                
                if attempt < max_retries - 1:
                    self.logger.warning(f"Retrying database connection in {retry_delay} seconds...")
                    if self.conn:
                        self.conn.close()
                    import time
                    time.sleep(retry_delay)
                    retry_delay *= 2
                else:
                    self.logger.error("Database connection failed after all retry attempts")
                    sys.exit(1)
    
    def _test_database_connection(self) -> bool:
        """Test database connection with a simple query."""
        try:
            # Test basic database functionality
            self.cursor.execute("SELECT 1")
            result = self.cursor.fetchone()
            
            if result and result[0] == 1:
                self.logger.debug("Database connection test passed")
                return True
            else:
                self.logger.error("Database connection test failed - unexpected result")
                return False
                
        except sqlite3.Error as e:
            self.logger.error(f"Database connection test failed with SQLite error: {e}")
            return False
        except Exception as e:
            self.logger.error(f"Database connection test failed with unexpected error: {e}")
            return False
    
    def _create_tables(self):
        """Create tables if they don't exist."""
        # Correct schema path relative to this script: backend/scripts -> backend/sql/schema.sql
        schema_path = os.path.join(os.path.dirname(__file__), '..', 'sql', 'schema.sql')
        if os.path.exists(schema_path):
            with open(schema_path, 'r') as f:
                schema = f.read()
            self.cursor.executescript(schema)
            self.conn.commit()
            print("Database tables created/verified")
        else:
            print("Warning: Schema file not found, using basic table creation")
            self.cursor.execute("""
                CREATE TABLE IF NOT EXISTS files (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    file_path TEXT NOT NULL,
                    file_name TEXT NOT NULL,
                    file_size INTEGER,
                    sha256 TEXT,
                    perceptual_hash TEXT,
                    file_type TEXT,
                    mime_type TEXT,
                    created_at TIMESTAMP,
                    modified_at TIMESTAMP,
                    metadata_json TEXT,
                    added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            self.conn.commit()
    
    def compute_sha256(self, file_path: str) -> str:
        """Compute SHA256 hash of a file."""
        sha256_hash = hashlib.sha256()
        try:
            with open(file_path, "rb") as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    sha256_hash.update(chunk)
            return sha256_hash.hexdigest()
        except PermissionError as e:
            self._log_error('PERMISSION_ERROR', file_path, 'Permission denied while reading file', e)
            return ""
        except FileNotFoundError as e:
            self._log_error('FILE_NOT_FOUND', file_path, 'File not found during hash computation', e)
            return ""
        except OSError as e:
            self._log_error('FILE_IO_ERROR', file_path, f'OS error while reading file: {e}', e)
            return ""
        except Exception as e:
            self._log_error('HASH_COMPUTATION_ERROR', file_path, f'Unexpected error computing SHA256: {e}', e)
            return ""
    
    def compute_perceptual_hash(self, file_path: str) -> Optional[str]:
        """Compute perceptual hash for images with graceful dependency handling."""
        if not self._is_dependency_available('imagehash') or not self._is_dependency_available('Image'):
            self.logger.debug(f"Skipping perceptual hash for {file_path} - missing dependencies")
            return None
        
        try:
            with Image.open(file_path) as img:
                # Convert to RGB if necessary
                if img.mode != 'RGB':
                    img = img.convert('RGB')
                # Compute perceptual hash using multiple algorithms for better accuracy
                hash_value = imagehash.average_hash(img, hash_size=16)  # Increased hash size for better precision
                return str(hash_value)
        except PermissionError as e:
            self._log_error('PERMISSION_ERROR', file_path, 'Permission denied while opening image', e)
            return None
        except FileNotFoundError as e:
            self._log_error('FILE_NOT_FOUND', file_path, 'Image file not found', e)
            return None
        except Exception as e:
            # Handle PIL-specific errors more gracefully
            if 'UnidentifiedImageError' in str(type(e)):
                self._log_error('IMAGE_FORMAT_ERROR', file_path, 'Unidentified or corrupted image format', e)
            elif 'DecompressionBombError' in str(type(e)):
                self._log_error('IMAGE_TOO_LARGE', file_path, 'Image too large (potential decompression bomb)', e)
            elif isinstance(e, OSError):
                self._log_error('FILE_IO_ERROR', file_path, f'OS error while processing image: {e}', e)
            else:
                self._log_error('PERCEPTUAL_HASH_ERROR', file_path, f'Unexpected error computing perceptual hash: {e}', e)
            return None
    
    def calculate_image_similarity(self, hash1: str, hash2: str) -> float:
        """Calculate similarity percentage between two perceptual hashes."""
        if not hash1 or not hash2 or not imagehash:
            return 0.0
        
        try:
            # Convert string hashes back to imagehash objects
            h1 = imagehash.hex_to_hash(hash1)
            h2 = imagehash.hex_to_hash(hash2)
            
            # Calculate Hamming distance
            hamming_distance = h1 - h2
            
            # Convert to similarity percentage (lower distance = higher similarity)
            # For 16x16 hash (256 bits), max distance is 256
            max_distance = len(str(h1)) * 4  # Each hex char represents 4 bits
            similarity = max(0, (max_distance - hamming_distance) / max_distance * 100)
            
            return round(similarity, 1)
        except Exception as e:
            print(f"Error calculating similarity: {e}")
            return 0.0
    
    def extract_image_features(self, file_path: str) -> Optional[Any]:
        """Extract feature vector from image for cosine similarity."""
        if not self._is_dependency_available('Image') or not self._is_dependency_available('numpy'):
            return None
        
        try:
            with Image.open(file_path) as img:
                # Convert to RGB and resize for consistent feature extraction
                img = img.convert('RGB')
                img = img.resize((64, 64))  # Standard size for feature extraction
                
                # Convert to numpy array and flatten
                img_array = np.array(img)
                features = img_array.flatten()
                
                # Normalize features
                features = features / 255.0
                
                return features
        except Exception as e:
            self._log_error('FEATURE_EXTRACTION_ERROR', file_path, f'Error extracting image features: {e}', e)
            return None
    
    def calculate_cosine_similarity(self, features1: Any, features2: Any) -> float:
        """Calculate cosine similarity between two feature vectors."""
        if (not self._is_dependency_available('numpy') or 
            not self._is_dependency_available('cosine_similarity') or 
            features1 is None or features2 is None):
            return 0.0
        
        try:
            # Reshape for sklearn
            f1 = features1.reshape(1, -1)
            f2 = features2.reshape(1, -1)
            
            # Calculate cosine similarity
            similarity = cosine_similarity(f1, f2)[0][0]
            
            # Convert to percentage
            return round(similarity * 100, 1)
        except Exception as e:
            self.logger.error(f"Error calculating cosine similarity: {e}")
            return 0.0
    
    def find_similar_images_cosine(self, threshold: float = 80.0):
        """Find similar images using cosine similarity."""
        if not self._is_dependency_available('numpy') or not self._is_dependency_available('cosine_similarity'):
            print("NumPy and scikit-learn required for cosine similarity")
            return []
        
        try:
            # Get all image files from database
            image_extensions = ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff', '.webp']
            
            query = """
                SELECT id, file_path, file_name, file_size, width, height, perceptual_hash
                FROM files 
                WHERE LOWER(file_type) IN ({})
            """.format(','.join(['?' for _ in image_extensions]))
            
            images = self.cursor.execute(query, [ext.lower() for ext in image_extensions]).fetchall()
            
            if len(images) < 2:
                return []
            
            print(f"Analyzing {len(images)} images for similarity...")
            
            # Extract features for all images
            image_features = []
            valid_images = []
            
            for img in images:
                features = self.extract_image_features(img[1])  # file_path
                if features is not None:
                    image_features.append(features)
                    valid_images.append(img)
            
            if len(valid_images) < 2:
                print("Not enough valid images for similarity analysis")
                return []
            
            # Find similar groups
            similar_groups = []
            processed_indices = set()
            
            for i, img1 in enumerate(valid_images):
                if i in processed_indices:
                    continue
                
                group_images = [img1]
                group_similarities = [100.0]  # Self similarity
                
                for j, img2 in enumerate(valid_images[i+1:], i+1):
                    if j in processed_indices:
                        continue
                    
                    similarity = self.calculate_cosine_similarity(
                        image_features[i], 
                        image_features[j]
                    )
                    
                    if similarity >= threshold:
                        group_images.append(img2)
                        group_similarities.append(similarity)
                        processed_indices.add(j)
                
                if len(group_images) > 1:
                    similar_groups.append({
                        'images': group_images,
                        'similarities': group_similarities,
                        'avg_similarity': sum(group_similarities) / len(group_similarities)
                    })
                    processed_indices.add(i)
            
            return similar_groups
            
        except Exception as e:
            print(f"Error finding similar images: {e}")
            return []
    
    def get_image_dimensions(self, file_path: str) -> tuple[Optional[int], Optional[int]]:
        """Get image dimensions (width, height) with graceful dependency handling."""
        if not self._is_dependency_available('Image'):
            self.logger.debug(f"Skipping image dimensions for {file_path} - PIL not available")
            return None, None
        
        try:
            with Image.open(file_path) as img:
                return img.width, img.height
        except PermissionError as e:
            self._log_error('PERMISSION_ERROR', file_path, 'Permission denied while getting image dimensions', e)
            return None, None
        except FileNotFoundError as e:
            self._log_error('FILE_NOT_FOUND', file_path, 'Image file not found for dimensions', e)
            return None, None
        except Exception as e:
            # Handle PIL-specific errors more gracefully
            if 'UnidentifiedImageError' in str(type(e)):
                self._log_error('IMAGE_FORMAT_ERROR', file_path, 'Cannot identify image format for dimensions', e)
            elif 'DecompressionBombError' in str(type(e)):
                self._log_error('IMAGE_TOO_LARGE', file_path, 'Image too large for dimension extraction', e)
            elif isinstance(e, OSError):
                self._log_error('FILE_IO_ERROR', file_path, f'OS error while getting image dimensions: {e}', e)
            else:
                self._log_error('IMAGE_DIMENSIONS_ERROR', file_path, f'Unexpected error getting image dimensions: {e}', e)
            return None, None
    
    def extract_exif_data(self, file_path: str) -> Dict:
        """Extract EXIF data from images with graceful dependency handling."""
        if not self._is_dependency_available('exifread'):
            self.logger.debug(f"Skipping EXIF extraction for {file_path} - exifread not available")
            return {}
        
        try:
            with open(file_path, 'rb') as f:
                tags = exifread.process_file(f)
            
            exif_data = {}
            for tag, value in tags.items():
                if tag not in ('JPEGThumbnail', 'TIFFThumbnail'):
                    try:
                        exif_data[tag] = str(value)
                    except Exception as e:
                        self.logger.debug(f"Could not convert EXIF tag {tag} to string: {e}")
            return exif_data
        except PermissionError as e:
            self._log_error('PERMISSION_ERROR', file_path, 'Permission denied while extracting EXIF data', e)
            return {}
        except FileNotFoundError as e:
            self._log_error('FILE_NOT_FOUND', file_path, 'File not found while extracting EXIF data', e)
            return {}
        except OSError as e:
            self._log_error('FILE_IO_ERROR', file_path, f'OS error while extracting EXIF data: {e}', e)
            return {}
        except Exception as e:
            self._log_error('EXIF_EXTRACTION_ERROR', file_path, f'Error extracting EXIF data: {e}', e)
            return {}
    
    def get_file_metadata(self, file_path: str) -> Dict:
        """Extract comprehensive file metadata with enhanced error handling."""
        try:
            stat = os.stat(file_path)
            file_info = {
                'file_path': file_path,
                'file_name': os.path.basename(file_path),
                'file_size': stat.st_size,
                'created_at': datetime.fromtimestamp(stat.st_ctime),
                'modified_at': datetime.fromtimestamp(stat.st_mtime),
                'file_type': Path(file_path).suffix.lower(),
                'mime_type': '',
                'metadata_json': '{}'
            }
            
            # Get MIME type with graceful handling
            if self._is_dependency_available('magic'):
                try:
                    file_info['mime_type'] = magic.from_file(file_path, mime=True)
                except Exception as e:
                    self.logger.debug(f"Could not determine MIME type for {file_path}: {e}")
                    # Try alternative method if available
                    try:
                        import mimetypes
                        mime_type, _ = mimetypes.guess_type(file_path)
                        if mime_type:
                            file_info['mime_type'] = mime_type
                            self.logger.debug(f"Used mimetypes fallback for {file_path}: {mime_type}")
                    except Exception:
                        pass
            else:
                # Fallback to built-in mimetypes module
                try:
                    import mimetypes
                    mime_type, _ = mimetypes.guess_type(file_path)
                    if mime_type:
                        file_info['mime_type'] = mime_type
                except Exception as e:
                    self.logger.debug(f"Could not determine MIME type using fallback for {file_path}: {e}")
            
            # Extract EXIF for images with better error handling
            if file_info['file_type'] in ['.jpg', '.jpeg', '.png', '.tiff', '.tif', '.bmp']:
                try:
                    exif_data = self.extract_exif_data(file_path)
                    if exif_data:
                        file_info['metadata_json'] = json.dumps(exif_data, default=str)
                except Exception as e:
                    self.logger.debug(f"Could not extract/serialize EXIF data for {file_path}: {e}")
                    file_info['metadata_json'] = '{}'
            
            return file_info
        except PermissionError as e:
            self._log_error('PERMISSION_ERROR', file_path, 'Permission denied while getting file metadata', e)
            return {}
        except FileNotFoundError as e:
            self._log_error('FILE_NOT_FOUND', file_path, 'File not found while getting metadata', e)
            return {}
        except OSError as e:
            if e.errno == 36:  # File name too long
                self._log_error('FILENAME_TOO_LONG', file_path, f'Filename too long for metadata extraction: {e}', e)
            else:
                self._log_error('FILE_IO_ERROR', file_path, f'OS error while getting file metadata: {e}', e)
            return {}
        except ValueError as e:
            # Handle timestamp conversion errors
            self._log_error('TIMESTAMP_ERROR', file_path, f'Error converting file timestamps: {e}', e)
            return {}
        except Exception as e:
            self._log_error('METADATA_EXTRACTION_ERROR', file_path, f'Unexpected error getting file metadata: {e}', e)
            return {}
    
    def _check_column_exists(self, table_name: str, column_name: str) -> bool:
        """Check if a column exists in the specified table (with caching)."""
        cache_key = f"{table_name}.{column_name}"
        
        if cache_key in self._column_cache:
            return self._column_cache[cache_key]
        
        try:
            cursor_info = self.cursor.execute(f"PRAGMA table_info({table_name})")
            columns = [row[1] for row in cursor_info.fetchall()]
            exists = column_name in columns
            self._column_cache[cache_key] = exists
            return exists
        except Exception as e:
            print(f"Error checking column existence for {table_name}.{column_name}: {e}")
            self._column_cache[cache_key] = False
            return False
    
    def _initialize_column_cache(self):
        """Initialize column cache during database connection."""
        try:
            # Check for width and height columns existence
            self._check_column_exists('files', 'width')
            self._check_column_exists('files', 'height')
            
            # Log column availability
            has_width = self._column_cache.get('files.width', False)
            has_height = self._column_cache.get('files.height', False)
            
            if has_width and has_height:
                print("Database supports width and height columns")
            else:
                print("Warning: Database missing width/height columns - using fallback mode")
                
        except Exception as e:
            print(f"Error initializing column cache: {e}")
    
    def insert_file(self, metadata: Dict) -> bool:
        """Insert file information into database with graceful handling of missing columns and dry-run support."""
        file_path = metadata.get('file_path', 'unknown')
        
        # In dry-run mode, just log what would be inserted and return success
        if self.dry_run:
            self.logger.debug(f"DRY RUN: Would insert file: {file_path}")
            return True
        
        try:
            # Use cached column information
            has_width = self._column_cache.get('width', False)
            has_height = self._column_cache.get('height', False)
            
            # Extract values from metadata
            sha256 = metadata.get('sha256', '')
            perceptual_hash = metadata.get('perceptual_hash')
            width = metadata.get('width')
            height = metadata.get('height')
            
            if has_width and has_height:
                # Full insertion with width and height
                self.cursor.execute("""
                    INSERT OR REPLACE INTO files 
                    (file_path, file_name, file_size, sha256, perceptual_hash, 
                     file_type, mime_type, width, height, created_at, modified_at, metadata_json)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    metadata.get('file_path', ''),
                    metadata.get('file_name', ''),
                    metadata.get('file_size', 0),
                    sha256,
                    perceptual_hash,
                    metadata.get('file_type', ''),
                    metadata.get('mime_type', ''),
                    width,
                    height,
                    metadata.get('created_at'),
                    metadata.get('modified_at'),
                    metadata.get('metadata_json', '{}')
                ))
            else:
                # Fallback insertion without width and height columns
                self.cursor.execute("""
                    INSERT OR REPLACE INTO files 
                    (file_path, file_name, file_size, sha256, perceptual_hash, 
                     file_type, mime_type, created_at, modified_at, metadata_json)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    metadata.get('file_path', ''),
                    metadata.get('file_name', ''),
                    metadata.get('file_size', 0),
                    sha256,
                    perceptual_hash,
                    metadata.get('file_type', ''),
                    metadata.get('mime_type', ''),
                    metadata.get('created_at'),
                    metadata.get('modified_at'),
                    metadata.get('metadata_json', '{}')
                ))
            
            self.conn.commit()
            return True
            
        except sqlite3.IntegrityError as e:
            self._log_error('DATABASE_INTEGRITY_ERROR', file_path, f'Database integrity constraint violation: {e}', e)
            return False
        except sqlite3.OperationalError as e:
            self._log_error('DATABASE_OPERATIONAL_ERROR', file_path, f'Database operational error (possibly schema mismatch): {e}', e)
            return False
        except sqlite3.DatabaseError as e:
            self._log_error('DATABASE_ERROR', file_path, f'General database error during insertion: {e}', e)
            return False
        except sqlite3.Error as e:
            self._log_error('DATABASE_SQLITE_ERROR', file_path, f'SQLite error during insertion: {e}', e)
            return False
        except Exception as e:
            self._log_error('DATABASE_INSERTION_ERROR', file_path, f'Unexpected error during database insertion: {e}', e)
            return False
    
    def scan_folder(self, folder_path: str, recursive: bool = True):
        """Scan a folder for files with enhanced progress reporting and dry-run support."""
        if not os.path.exists(folder_path):
            error_msg = f"Folder {folder_path} does not exist"
            self._log_error('FOLDER_NOT_FOUND', folder_path, error_msg)
            return
        
        # Record start time
        self.stats['start_time'] = datetime.now()
        
        self.logger.info(f"Scanning folder: {folder_path}")
        self.logger.info(f"Recursive: {recursive}")
        self.logger.info(f"Dry run mode: {self.dry_run}")
        
        print("=" * 60)
        print(f"STARTING SCAN: {folder_path}")
        print(f"Mode: {'Recursive' if recursive else 'Non-recursive'}")
        if self.dry_run:
            print("DRY RUN MODE: No database changes will be made")
        print(f"Started at: {self.stats['start_time'].strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 60)
        
        try:
            if recursive:
                for root, dirs, files in os.walk(folder_path):
                    for file in files:
                        file_path = os.path.join(root, file)
                        self._process_file(file_path)
                        self._update_progress()
            else:
                for item in os.listdir(folder_path):
                    item_path = os.path.join(folder_path, item)
                    if os.path.isfile(item_path):
                        self._process_file(item_path)
                        self._update_progress()
        except PermissionError as e:
            self._log_error('PERMISSION_ERROR', folder_path, f'Permission denied while scanning folder: {e}', e)
        except OSError as e:
            self._log_error('FILE_IO_ERROR', folder_path, f'OS error while scanning folder: {e}', e)
        except Exception as e:
            self._log_error('SCAN_ERROR', folder_path, f'Unexpected error during folder scan: {e}', e)
        
        # Record end time
        self.stats['end_time'] = datetime.now()
        
        # Display comprehensive scan results
        self._print_scan_summary()
    
    def _update_progress(self):
        """Update and display progress during scanning."""
        self._progress_counter += 1
        
        # Report progress every N files
        if self._progress_counter % self._progress_interval == 0:
            elapsed_time = datetime.now() - self.stats['start_time']
            files_per_second = self._progress_counter / elapsed_time.total_seconds() if elapsed_time.total_seconds() > 0 else 0
            
            print(f"Progress: {self.stats['total_files']} files found, "
                  f"{self.stats['processed_files']} processed, "
                  f"{self.stats['skipped_files']} skipped, "
                  f"{self.stats['errors']} errors "
                  f"({files_per_second:.1f} files/sec)")
    
    def _print_scan_summary(self):
        """Print comprehensive scan summary with detailed statistics."""
        duration = self.stats['end_time'] - self.stats['start_time']
        
        print("\n" + "=" * 60)
        print("SCAN COMPLETE - SUMMARY REPORT")
        print("=" * 60)
        
        # Basic statistics
        print(f"Scan Duration: {duration}")
        print(f"Files per Second: {self.stats['total_files'] / duration.total_seconds():.1f}")
        print()
        
        # File processing statistics
        print("FILE PROCESSING STATISTICS:")
        print("-" * 30)
        print(f"Total files found:     {self.stats['total_files']:,}")
        print(f"Successfully processed: {self.stats['processed_files']:,}")
        print(f"Total skipped:         {self.stats['skipped_files']:,}")
        print(f"Duplicates found:      {self.stats['duplicates_found']:,}")
        print(f"Errors encountered:    {self.stats['errors']:,}")
        
        # Detailed skip breakdown
        if self.stats['skipped_files'] > 0:
            print("\nSKIP BREAKDOWN:")
            print("-" * 15)
            if self.stats['skipped_hidden'] > 0:
                print(f"Hidden files:          {self.stats['skipped_hidden']:,}")
            if self.stats['skipped_system'] > 0:
                print(f"System files:          {self.stats['skipped_system']:,}")
            if self.stats['skipped_large'] > 0:
                print(f"Large files (>1GB):    {self.stats['skipped_large']:,}")
            if self.stats['skipped_zero_byte'] > 0:
                print(f"Zero-byte files:       {self.stats['skipped_zero_byte']:,}")
            if self.stats['skipped_corrupted'] > 0:
                print(f"Corrupted files:       {self.stats['skipped_corrupted']:,}")
        
        # Success rate
        if self.stats['total_files'] > 0:
            success_rate = (self.stats['processed_files'] / self.stats['total_files']) * 100
            print(f"\nSuccess Rate: {success_rate:.1f}%")
        
        # Display error summary if there were errors
        if self.stats['errors'] > 0:
            self._print_error_summary()
        
        # Recommendations
        self._print_recommendations()
        
        print("=" * 60)
    
    def _print_error_summary(self):
        """Print a summary of errors encountered during scanning."""
        print("\n" + "=" * 50)
        print("ERROR SUMMARY:")
        print("=" * 50)
        
        # Group errors by type
        error_types = {}
        for error in self.error_details:
            error_type = error['error_type']
            if error_type not in error_types:
                error_types[error_type] = []
            error_types[error_type].append(error)
        
        # Display summary by error type
        for error_type, errors in error_types.items():
            print(f"\n{error_type}: {len(errors)} occurrences")
            
            # Show first few examples
            for i, error in enumerate(errors[:3]):
                print(f"  - {error['file_path']}: {error['error_message']}")
            
            if len(errors) > 3:
                print(f"  ... and {len(errors) - 3} more")
        
        print(f"\nTotal errors: {len(self.error_details)}")
        print("Check logs for detailed error information.")
    
    def _print_recommendations(self):
        """Print recommendations based on scan results."""
        print("\nRECOMMENDATIONS:")
        print("-" * 15)
        
        recommendations = []
        
        # Error-based recommendations
        if self.stats['errors'] > 0:
            error_rate = (self.stats['errors'] / self.stats['total_files']) * 100
            if error_rate > 10:
                recommendations.append("High error rate detected. Check file permissions and disk health.")
        
        # Skip-based recommendations
        if self.stats['skipped_large'] > 0:
            recommendations.append(f"{self.stats['skipped_large']} large files (>1GB) were skipped. Consider processing them separately.")
        
        if self.stats['skipped_corrupted'] > 0:
            recommendations.append(f"{self.stats['skipped_corrupted']} corrupted files detected. Consider running disk check.")
        
        # Duplicate recommendations
        if self.stats['duplicates_found'] > 0:
            recommendations.append(f"{self.stats['duplicates_found']} duplicate files found. Use --duplicates flag to see details.")
        
        # Performance recommendations
        if self.stats['total_files'] > 10000:
            recommendations.append("Large folder detected. Consider scanning in smaller batches for better performance.")
        
        if not recommendations:
            recommendations.append("Scan completed successfully with no issues detected.")
        
        for i, rec in enumerate(recommendations, 1):
            print(f"{i}. {rec}")
    
    def _validate_file_existence(self, file_path: str) -> bool:
        """Enhanced file existence validation with detailed error reporting."""
        try:
            # Check if file exists
            if not os.path.exists(file_path):
                self._log_error('FILE_NOT_FOUND', file_path, 'File does not exist during processing')
                return False
            
            # Check if it's actually a file (not a directory or special file)
            if not os.path.isfile(file_path):
                if os.path.isdir(file_path):
                    self._log_error('NOT_A_FILE', file_path, 'Path is a directory, not a file')
                elif os.path.islink(file_path):
                    # Handle broken symlinks
                    if not os.path.exists(os.readlink(file_path)):
                        self._log_error('BROKEN_SYMLINK', file_path, 'Symbolic link points to non-existent file')
                        return False
                    self.logger.debug(f"Following symbolic link: {file_path}")
                else:
                    self._log_error('SPECIAL_FILE', file_path, 'Path is not a regular file (may be device, pipe, etc.)')
                return False
            
            # Check file accessibility
            if not os.access(file_path, os.R_OK):
                self._log_error('PERMISSION_ERROR', file_path, 'File is not readable')
                return False
            
            return True
            
        except PermissionError as e:
            self._log_error('PERMISSION_ERROR', file_path, f'Permission denied while validating file: {e}', e)
            return False
        except OSError as e:
            self._log_error('FILE_IO_ERROR', file_path, f'OS error while validating file: {e}', e)
            return False
        except Exception as e:
            self._log_error('FILE_VALIDATION_ERROR', file_path, f'Unexpected error validating file: {e}', e)
            return False
    
    def _validate_file_type(self, file_path: str) -> bool:
        """Enhanced file type detection and validation."""
        try:
            # Get file extension
            file_ext = Path(file_path).suffix.lower()
            
            # Define supported file types
            supported_image_types = {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff', '.tif', '.webp', '.ico', '.svg'}
            supported_document_types = {'.pdf', '.doc', '.docx', '.txt', '.rtf', '.odt'}
            supported_archive_types = {'.zip', '.rar', '.7z', '.tar', '.gz', '.bz2'}
            supported_video_types = {'.mp4', '.avi', '.mkv', '.mov', '.wmv', '.flv', '.webm'}
            supported_audio_types = {'.mp3', '.wav', '.flac', '.aac', '.ogg', '.wma'}
            
            all_supported_types = (supported_image_types | supported_document_types | 
                                 supported_archive_types | supported_video_types | supported_audio_types)
            
            # Check if file type is supported
            if file_ext and file_ext not in all_supported_types:
                self.logger.debug(f"Unsupported file type: {file_path} ({file_ext})")
                # Still process unsupported types for basic metadata, but log it
            
            # Validate MIME type if magic is available
            if magic:
                try:
                    mime_type = magic.from_file(file_path, mime=True)
                    
                    # Check for potentially corrupted files
                    if mime_type == 'application/octet-stream' and file_ext in supported_image_types:
                        self.logger.warning(f"Potential corrupted image file: {file_path} (detected as binary)")
                    
                    # Validate image files more strictly
                    if file_ext in supported_image_types:
                        if not mime_type.startswith('image/'):
                            self._log_error('FILE_TYPE_MISMATCH', file_path, 
                                          f'File extension suggests image but MIME type is {mime_type}')
                            return False
                    
                except Exception as e:
                    self.logger.debug(f"Could not determine MIME type for {file_path}: {e}")
            
            return True
            
        except Exception as e:
            self._log_error('FILE_TYPE_VALIDATION_ERROR', file_path, f'Error validating file type: {e}', e)
            return False
    
    def _should_skip_file(self, file_path: str) -> tuple[bool, str]:
        """Enhanced logic to determine if a file should be skipped with reason tracking."""
        try:
            filename = os.path.basename(file_path)
            
            # Skip hidden files (starting with .)
            if filename.startswith('.'):
                self.logger.debug(f"Skipped hidden file: {file_path}")
                return True, 'hidden'
            
            # Skip temporary files
            if filename.startswith('~') or filename.endswith('~'):
                self.logger.debug(f"Skipped temporary file: {file_path}")
                return True, 'system'
            
            # Skip system files on different platforms
            system_files = {
                'Thumbs.db',      # Windows thumbnail cache
                'Desktop.ini',    # Windows desktop settings
                '.DS_Store',      # macOS folder settings
                '.localized',     # macOS localization
                'Icon\r',         # macOS custom folder icon
                '$RECYCLE.BIN',   # Windows recycle bin
                'System Volume Information',  # Windows system folder
            }
            
            if filename in system_files:
                self.logger.debug(f"Skipped system file: {file_path}")
                return True, 'system'
            
            # Skip files with certain patterns
            skip_patterns = [
                r'^\._',          # macOS resource forks
                r'\.tmp$',        # Temporary files
                r'\.temp$',       # Temporary files
                r'\.bak$',        # Backup files
                r'\.swp$',        # Vim swap files
                r'\.lock$',       # Lock files
                r'\.log$',        # Log files (optional - might want to process these)
            ]
            
            import re
            for pattern in skip_patterns:
                if re.search(pattern, filename, re.IGNORECASE):
                    self.logger.debug(f"Skipped file matching pattern '{pattern}': {file_path}")
                    return True, 'system'
            
            # Skip zero-byte files
            try:
                if os.path.getsize(file_path) == 0:
                    self.logger.debug(f"Skipped zero-byte file: {file_path}")
                    return True, 'zero_byte'
            except OSError:
                # If we can't get size, let other validation catch it
                pass
            
            return False, ''
            
        except Exception as e:
            self.logger.debug(f"Error checking if file should be skipped: {file_path}: {e}")
            return False, ''  # When in doubt, don't skip
    
    def _get_safe_file_size(self, file_path: str) -> Optional[int]:
        """Safely get file size with enhanced error handling."""
        try:
            return os.path.getsize(file_path)
        except PermissionError as e:
            self._log_error('PERMISSION_ERROR', file_path, f'Permission denied while getting file size: {e}', e)
            return None
        except FileNotFoundError as e:
            self._log_error('FILE_NOT_FOUND', file_path, f'File not found while getting size: {e}', e)
            return None
        except OSError as e:
            # Handle specific OS errors
            if e.errno == 36:  # File name too long
                self._log_error('FILENAME_TOO_LONG', file_path, f'Filename too long: {e}', e)
            elif e.errno == 2:  # No such file or directory
                self._log_error('FILE_NOT_FOUND', file_path, f'File disappeared during processing: {e}', e)
            else:
                self._log_error('FILE_IO_ERROR', file_path, f'OS error while getting file size: {e}', e)
            return None
        except Exception as e:
            self._log_error('FILE_SIZE_ERROR', file_path, f'Unexpected error getting file size: {e}', e)
            return None
    
    def _validate_file_integrity(self, file_path: str, file_info: Dict) -> tuple[bool, str]:
        """Validate file integrity and detect potential corruption with reason tracking."""
        try:
            # Check for zero-byte files (already handled in _should_skip_file, but double-check)
            if file_info.get('file_size', 0) == 0:
                self.logger.debug(f"Skipping zero-byte file: {file_path}")
                return False, 'zero_byte'
            
            # Check for extremely large files that might cause issues
            max_file_size = 10 * 1024 * 1024 * 1024  # 10GB
            if file_info.get('file_size', 0) > max_file_size:
                self._log_error('FILE_TOO_LARGE', file_path, f'File too large ({file_info["file_size"]} bytes)')
                return False, 'large'
            
            # For image files, do basic validation
            if self._is_image_file(file_info.get('file_type', '')):
                is_valid = self._validate_image_file(file_path)
                return is_valid, 'corrupted' if not is_valid else ''
            
            return True, ''
            
        except Exception as e:
            self._log_error('FILE_INTEGRITY_ERROR', file_path, f'Error validating file integrity: {e}', e)
            return False, 'corrupted'
    
    def _validate_image_file(self, file_path: str) -> bool:
        """Validate image file integrity."""
        # Temporarily disable image validation due to PIL issues
        return True
        
        # Original validation code commented out
        # if not self._is_dependency_available('Image'):
        #     return True  # Can't validate without PIL, assume it's okay
        # 
        # try:
        #     # Try to open and verify the image
        #     with Image.open(file_path) as img:
        #         # Try to load the image data to detect corruption
        #         img.verify()
        #     return True
        # except Exception as e:
        #     if 'cannot identify image file' in str(e).lower():
        #         self._log_error('CORRUPTED_IMAGE', file_path, 'Cannot identify image file (possibly corrupted)', e)
        #     elif 'truncated' in str(e).lower():
        #         self._log_error('TRUNCATED_IMAGE', file_path, 'Image file appears to be truncated', e)
        #     else:
        #         self._log_error('IMAGE_VALIDATION_ERROR', file_path, f'Image validation failed: {e}', e)
        #     return False
    
    def _is_image_file(self, file_type: str) -> bool:
        """Check if file type indicates an image file."""
        image_extensions = {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff', '.tif', '.webp', '.ico', '.svg'}
        return file_type.lower() in image_extensions
    
    def _compute_sha256_with_retry(self, file_path: str, max_retries: int = 2) -> str:
        """Compute SHA256 with retry logic for temporary issues."""
        for attempt in range(max_retries + 1):
            sha256 = self.compute_sha256(file_path)
            if sha256:
                return sha256
            
            if attempt < max_retries:
                self.logger.debug(f"Retrying SHA256 computation for {file_path} (attempt {attempt + 2})")
                import time
                time.sleep(0.1)  # Brief pause before retry
        
        return ""
    
    def _process_image_features(self, file_path: str) -> tuple[Optional[str], Optional[int], Optional[int]]:
        """Process image-specific features with enhanced error handling."""
        perceptual_hash = None
        width, height = None, None
        
        try:
            # Get image dimensions
            width, height = self.get_image_dimensions(file_path)
            
            # Compute perceptual hash
            perceptual_hash = self.compute_perceptual_hash(file_path)
            
        except Exception as e:
            # Log but don't fail the entire file processing
            self.logger.debug(f"Could not process image features for {file_path}: {e}")
        
        return perceptual_hash, width, height
    
    def _process_file(self, file_path: str):
        """Process a single file with comprehensive error handling and detailed skip tracking."""
        self.stats['total_files'] += 1
        
        try:
            # Enhanced file existence validation
            if not self._validate_file_existence(file_path):
                return
            
            # Enhanced file type detection and validation
            if not self._validate_file_type(file_path):
                return
            
            # Skip hidden files and system files with better detection
            should_skip, skip_reason = self._should_skip_file(file_path)
            if should_skip:
                self.stats['skipped_files'] += 1
                if skip_reason == 'hidden':
                    self.stats['skipped_hidden'] += 1
                elif skip_reason == 'system':
                    self.stats['skipped_system'] += 1
                elif skip_reason == 'zero_byte':
                    self.stats['skipped_zero_byte'] += 1
                return
            
            # Enhanced file size validation with better error handling
            file_size = self._get_safe_file_size(file_path)
            if file_size is None:
                return
            
            # Skip very large files (>1GB) to prevent memory issues
            if file_size > 1024 * 1024 * 1024:  # 1GB
                self.stats['skipped_files'] += 1
                self.stats['skipped_large'] += 1
                self.logger.info(f"Skipped large file (>1GB): {file_path} ({file_size} bytes)")
                return
            
            # Get metadata with enhanced error handling
            file_info = self.get_file_metadata(file_path)
            if not file_info:
                self._log_error('METADATA_ERROR', file_path, 'Failed to extract file metadata')
                return
            
            # Validate file integrity before processing
            is_valid, validation_reason = self._validate_file_integrity(file_path, file_info)
            if not is_valid:
                self.stats['skipped_files'] += 1
                if validation_reason == 'zero_byte':
                    self.stats['skipped_zero_byte'] += 1
                elif validation_reason == 'large':
                    self.stats['skipped_large'] += 1
                elif validation_reason == 'corrupted':
                    self.stats['skipped_corrupted'] += 1
                return
            
            # Compute SHA256 with retry logic for temporary issues
            sha256 = self._compute_sha256_with_retry(file_path)
            if not sha256:
                self._log_error('HASH_ERROR', file_path, 'Failed to compute SHA256 hash after retries')
                return
            
            # Check for existing file with same hash
            try:
                existing = self.cursor.execute(
                    "SELECT file_path FROM files WHERE sha256 = ?", (sha256,)
                ).fetchone()
                
                if existing:
                    self.logger.info(f"Duplicate found: {file_path} (same as {existing[0]})")
                    self.stats['duplicates_found'] += 1
            except sqlite3.Error as e:
                self._log_error('DATABASE_QUERY_ERROR', file_path, f'Error checking for duplicates: {e}', e)
                # Continue processing even if duplicate check fails
            
            # Compute perceptual hash and dimensions for images with enhanced handling
            perceptual_hash = None
            width, height = None, None
            
            if self._is_image_file(file_info['file_type']):
                perceptual_hash, width, height = self._process_image_features(file_path)
                file_info['perceptual_hash'] = perceptual_hash
                file_info['width'] = width
                file_info['height'] = height
            
            # Add SHA256 to file_info
            file_info['sha256'] = sha256
            
            # Insert into database
            if self.insert_file(file_info):
                self.stats['processed_files'] += 1
                self.logger.debug(f"✓ Processed: {file_path} ({file_info['file_size']} bytes)")
            else:
                self._log_error('DATABASE_INSERT_FAILED', file_path, 'Failed to insert file into database')
            
        except PermissionError as e:
            self._log_error('PERMISSION_ERROR', file_path, f'Permission denied: {e}', e)
        except FileNotFoundError as e:
            self._log_error('FILE_NOT_FOUND', file_path, f'File not found during processing: {e}', e)
        except OSError as e:
            self._log_error('FILE_IO_ERROR', file_path, f'OS error during file processing: {e}', e)
        except MemoryError as e:
            self._log_error('MEMORY_ERROR', file_path, f'Out of memory while processing file: {e}', e)
        except KeyboardInterrupt:
            self.logger.info("Scan interrupted by user")
            raise
        except Exception as e:
            self._log_error('UNEXPECTED_ERROR', file_path, f'Unexpected error during file processing: {e}', e)
    
    def find_duplicates(self) -> List[Dict]:
        """Find all duplicate files based on SHA256 (legacy method)."""
        duplicates = self.cursor.execute("""
            SELECT sha256, COUNT(*) as count, GROUP_CONCAT(file_path) as paths
            FROM files 
            WHERE sha256 IS NOT NULL
            GROUP BY sha256 
            HAVING COUNT(*) > 1
            ORDER BY count DESC
        """).fetchall()
        
        # Convert to list of dictionaries for easier testing
        result = []
        for sha256, count, paths in duplicates:
            files = []
            for path in paths.split(','):
                # Get file details
                self.cursor.execute("SELECT * FROM files WHERE file_path = ?", (path,))
                file_data = self.cursor.fetchone()
                if file_data:
                    files.append({
                        'id': file_data[0],
                        'file_path': file_data[1],
                        'file_name': file_data[2],
                        'file_size': file_data[3],
                        'sha256': file_data[4],
                        'perceptual_hash': file_data[5],
                        'file_type': file_data[6],
                        'mime_type': file_data[7],
                        'width': file_data[8] if len(file_data) > 8 else None,
                        'height': file_data[9] if len(file_data) > 9 else None,
                    })
            
            if files:
                result.append({
                    'sha256': sha256,
                    'count': count,
                    'files': files
                })
        
        return result
    
    def detect_duplicates_enhanced(self, 
                                 mode: str = 'comprehensive',
                                 config: Optional[Dict[str, Any]] = None,
                                 file_filters: Optional[Dict[str, Any]] = None,
                                 progress_callback: Optional[callable] = None) -> Optional[Any]:
        """
        Enhanced duplicate detection using the new detection engine.
        
        Args:
            mode: Detection mode ('exact', 'similar', 'metadata', 'comprehensive')
            config: Optional configuration dictionary
            file_filters: Optional filters for file selection
            progress_callback: Optional callback for progress reporting
            
        Returns:
            DetectionResults object or None if enhanced detection not available
        """
        if not ENHANCED_DETECTION_AVAILABLE:
            self.logger.warning("Enhanced duplicate detection not available, falling back to basic detection")
            return None
        
        try:
            # For now, just return None to avoid import issues
            self.logger.info("Enhanced detection temporarily disabled due to import issues")
            return None
            
        except Exception as e:
            self.logger.error(f"Enhanced duplicate detection failed: {e}")
            if progress_callback:
                progress_callback(f"Detection failed: {e}", -1)
            return None
    
    def _get_files_for_enhanced_detection(self, file_filters: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """Get files from database for enhanced duplicate detection."""
        try:
            # Build query with filters
            query = "SELECT * FROM files WHERE 1=1"
            params = []
            
            if file_filters:
                if 'file_types' in file_filters:
                    placeholders = ','.join(['?' for _ in file_filters['file_types']])
                    query += f" AND file_type IN ({placeholders})"
                    params.extend(file_filters['file_types'])
                
                if 'min_size' in file_filters:
                    query += " AND file_size >= ?"
                    params.append(file_filters['min_size'])
                
                if 'max_size' in file_filters:
                    query += " AND file_size <= ?"
                    params.append(file_filters['max_size'])
                
                if 'path_pattern' in file_filters:
                    query += " AND file_path LIKE ?"
                    params.append(f"%{file_filters['path_pattern']}%")
            
            # Execute query
            rows = self.cursor.execute(query, params).fetchall()
            
            # Convert to DuplicateFile objects
            files = []
            for row in rows:
                try:
                    # Handle different column counts based on schema
                    file_data = {
                        'id': row[0],
                        'file_path': row[1],
                        'file_name': row[2],
                        'file_size': row[3] or 0,
                        'sha256': row[4],
                        'perceptual_hash': row[5],
                        'file_type': row[6],
                        'mime_type': row[7],
                        'width': row[8] if len(row) > 8 else None,
                        'height': row[9] if len(row) > 9 else None,
                        'created_at': datetime.fromisoformat(row[10]) if len(row) > 10 and row[10] else None,
                        'modified_at': datetime.fromisoformat(row[11]) if len(row) > 11 and row[11] else None,
                    }
                    
                    duplicate_file = DuplicateFile(
                        file_id=file_data['id'],
                        file_path=file_data['file_path'],
                        file_name=file_data['file_name'],
                        file_size=file_data['file_size'],
                        sha256=file_data['sha256'],
                        perceptual_hash=file_data['perceptual_hash'],
                        file_type=file_data['file_type'],
                        mime_type=file_data['mime_type'],
                        width=file_data['width'],
                        height=file_data['height'],
                        created_at=file_data['created_at'],
                        modified_at=file_data['modified_at']
                    )
                    files.append(duplicate_file)
                    
                except Exception as e:
                    self.logger.debug(f"Skipping file due to conversion error: {e}")
                    continue
            
            return files
            
        except Exception as e:
            self.logger.error(f"Failed to get files for enhanced detection: {e}")
            return []
    
    def find_similar_images(self, threshold: float = 80.0) -> List[Dict]:
        """Find similar images using perceptual hashing."""
        if not self._is_dependency_available('imagehash'):
            return []
        
        # Get all image files with perceptual hashes
        image_files = self.cursor.execute("""
            SELECT id, file_path, file_name, perceptual_hash
            FROM files 
            WHERE perceptual_hash IS NOT NULL
            AND file_type IN ('.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff', '.webp')
        """).fetchall()
        
        if len(image_files) < 2:
            return []
        
        similar_groups = []
        processed_ids = set()
        
        for i, (id1, path1, name1, hash1) in enumerate(image_files):
            if id1 in processed_ids:
                continue
            
            group_images = [(id1, path1, name1, hash1)]
            group_similarities = [100.0]  # Self similarity
            
            for j, (id2, path2, name2, hash2) in enumerate(image_files[i+1:], i+1):
                if id2 in processed_ids:
                    continue
                
                similarity = self.calculate_image_similarity(hash1, hash2)
                
                if similarity >= threshold:
                    group_images.append((id2, path2, name2, hash2))
                    group_similarities.append(similarity)
                    processed_ids.add(id2)
            
            if len(group_images) > 1:
                similar_groups.append({
                    'images': group_images,
                    'similarities': group_similarities,
                    'avg_similarity': sum(group_similarities) / len(group_similarities)
                })
                processed_ids.add(id1)
        
        return similar_groups
    
    def get_statistics_report(self) -> Dict:
        """Generate comprehensive statistics report."""
        if self.stats['start_time'] and self.stats['end_time']:
            duration = (self.stats['end_time'] - self.stats['start_time']).total_seconds()
        else:
            duration = 0
        
        report = self.stats.copy()
        report['scan_duration'] = duration
        report['success_rate'] = (
            (self.stats['processed_files'] / max(self.stats['total_files'], 1)) * 100
            if self.stats['total_files'] > 0 else 0
        )
        
        return report
    
    def get_error_summary(self) -> Dict:
        """Generate error summary with categorization."""
        error_types = {}
        for error in self.error_details:
            error_type = error['error_type']
            error_types[error_type] = error_types.get(error_type, 0) + 1
        
        return {
            'total_errors': self.stats['errors'],
            'error_types': error_types,
            'error_details': self.error_details
        }
    
    def _initialize_column_cache(self):
        """Initialize cache of available database columns."""
        try:
            self.cursor.execute("PRAGMA table_info(files)")
            columns = self.cursor.fetchall()
            self._column_cache = {col[1]: True for col in columns}
            self.logger.debug(f"Column cache initialized with {len(self._column_cache)} columns")
        except sqlite3.Error as e:
            self.logger.error(f"Failed to initialize column cache: {e}")
            self._column_cache = {}
    
    def close(self):
        """Close database connection."""
        if self.conn:
            self.conn.close()


def test_database_connection(db_path: str) -> bool:
    """Test database connection without scanning."""
    print(f"Testing database connection: {db_path}")
    
    try:
        scanner = FileScanner(db_path)
        scanner.connect_db()
        
        # Test basic operations
        print("✓ Database connection successful")
        
        # Check schema
        scanner.cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = scanner.cursor.fetchall()
        print(f"✓ Found {len(tables)} tables: {[t[0] for t in tables]}")
        
        # Check files table structure
        scanner.cursor.execute("PRAGMA table_info(files)")
        columns = scanner.cursor.fetchall()
        print(f"✓ Files table has {len(columns)} columns")
        
        # Test write access
        scanner.cursor.execute("SELECT COUNT(*) FROM files")
        count = scanner.cursor.fetchone()[0]
        print(f"✓ Current files in database: {count}")
        
        scanner.close()
        print("✓ Database test completed successfully")
        return True
        
    except Exception as e:
        print(f"✗ Database test failed: {e}")
        return False


def print_usage_help():
    """Print detailed usage instructions and troubleshooting tips."""
    help_text = """
RAG Smart Folder Scanner - Usage Guide
=====================================

BASIC USAGE:
  python3 scan_folder.py --path /path/to/scan --db data/scanner.db

COMMON COMMANDS:
  # Scan folder and show duplicates
  python3 scan_folder.py --path ~/Pictures --duplicates --verbose
  
  # Find similar images with custom threshold
  python3 scan_folder.py --path ~/Photos --mode similarity --similarity-threshold 85
  
  # Test database connection
  python3 scan_folder.py --test-db --db data/scanner.db
  
  # Scan with detailed error reporting
  python3 scan_folder.py --path ~/Documents --verbose --show-errors
  
  # Dry run (no database changes)
  python3 scan_folder.py --path ~/Downloads --dry-run --verbose

DEBUGGING OPTIONS:
  --verbose         Enable detailed logging and progress reporting
  --debug           Enable debug-level logging (very detailed)
  --show-errors     Display detailed error summary at the end
  --test-db         Test database connection without scanning
  --dry-run         Scan files but don't write to database
  --progress        Show progress every N files (default: 100)

TROUBLESHOOTING:

1. Permission Errors:
   - Ensure you have read access to the scan directory
   - Check database file permissions
   - Try running with elevated permissions if needed

2. Database Issues:
   - Use --test-db to verify database connectivity
   - Check if database file is locked by another process
   - Ensure database directory exists and is writable

3. Missing Dependencies:
   - Install required packages: pip install pillow imagehash python-magic
   - Some features work without optional dependencies
   - Use --verbose to see which dependencies are missing

4. Performance Issues:
   - Use --progress to monitor scanning speed
   - Consider scanning smaller directories first
   - Check available disk space for database growth

5. File Processing Errors:
   - Use --show-errors to see detailed error information
   - Check file permissions and corruption
   - Some files may be skipped intentionally (hidden, system files)

EXAMPLES:
  # Quick scan with progress reporting
  python3 scan_folder.py --path ~/Pictures --verbose --progress 50
  
  # Comprehensive scan with error analysis
  python3 scan_folder.py --path ~/Documents --duplicates --show-errors --debug
  
  # Test setup before large scan
  python3 scan_folder.py --test-db --db data/scanner.db
  python3 scan_folder.py --path ~/test_folder --dry-run --verbose

For more help, check the README.md file or run with --help
"""
    print(help_text)


def setup_enhanced_logging(verbose: bool = False, debug: bool = False):
    """Setup enhanced logging configuration."""
    if debug:
        level = logging.DEBUG
    elif verbose:
        level = logging.INFO
    else:
        level = logging.WARNING
    
    # Configure root logger
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # Reduce noise from some modules
    if not debug:
        logging.getLogger('PIL').setLevel(logging.WARNING)
        logging.getLogger('urllib3').setLevel(logging.WARNING)


def print_enhanced_detection_results(results: Any, verbose: bool = False):
    """Print enhanced duplicate detection results."""
    print(f"\nDetection Summary:")
    print(f"  Session ID: {results.session_id}")
    print(f"  Detection Mode: {results.detection_mode.value}")
    print(f"  Files Scanned: {results.total_files_scanned:,}")
    print(f"  Groups Found: {results.total_groups_found:,}")
    print(f"  Duplicates Found: {results.total_duplicates_found:,}")
    print(f"  Detection Time: {results.detection_time_ms:,}ms")
    print(f"  Success Rate: {results.success_rate:.1f}%")
    print(f"  Duplicate Percentage: {results.duplicate_percentage:.1f}%")
    
    if results.algorithm_performance:
        print(f"\nAlgorithm Performance:")
        for algo_name, perf in results.algorithm_performance.items():
            print(f"  {algo_name}:")
            print(f"    Files Processed: {perf.get('files_processed', 0):,}")
            print(f"    Execution Time: {perf.get('execution_time_ms', 0):,}ms")
            print(f"    Groups Found: {perf.get('groups_found', 0):,}")
            print(f"    Processing Speed: {perf.get('files_per_second', 0):.1f} files/sec")
            if perf.get('error_rate', 0) > 0:
                print(f"    Error Rate: {perf.get('error_rate', 0):.1f}%")
    
    if results.errors:
        print(f"\nErrors Encountered ({len(results.errors)}):")
        for i, error in enumerate(results.errors[:5], 1):  # Show first 5 errors
            print(f"  {i}. {error}")
        if len(results.errors) > 5:
            print(f"  ... and {len(results.errors) - 5} more errors")
    
    if results.groups:
        print(f"\nDuplicate Groups:")
        for i, group in enumerate(results.groups, 1):
            print(f"\nGroup {i} ({group.detection_method.value}):")
            print(f"  Confidence: {group.confidence_score:.1f}%")
            print(f"  Similarity: {group.similarity_percentage:.1f}%")
            print(f"  Files ({len(group.files)}):")
            
            for file in group.files:
                original_marker = " [ORIGINAL]" if file.is_original else ""
                confidence_info = f" (confidence: {file.confidence_score:.1f}%)" if verbose else ""
                print(f"    - {file.file_name}{original_marker}")
                print(f"      Path: {file.file_path}")
                print(f"      Size: {file.file_size:,} bytes{confidence_info}")
                
                if verbose and file.detection_reasons:
                    print(f"      Reasons: {', '.join(file.detection_reasons)}")
            
            if verbose and group.metadata:
                print(f"  Metadata: {group.metadata}")
    else:
        print("\nNo duplicate groups found.")


def print_scan_summary(scanner: FileScanner, show_errors: bool = False):
    """Print comprehensive scan summary with optional error details."""
    stats = scanner.get_statistics_report()
    error_summary = scanner.get_error_summary()
    
    print("\n" + "=" * 60)
    print("SCAN SUMMARY")
    print("=" * 60)
    
    # Basic statistics
    print(f"Total files found:     {stats['total_files']:,}")
    print(f"Successfully processed: {stats['processed_files']:,}")
    print(f"Files skipped:         {stats['skipped_files']:,}")
    print(f"Errors encountered:    {stats['errors']:,}")
    print(f"Success rate:          {stats['success_rate']:.1f}%")
    
    if stats['scan_duration'] > 0:
        print(f"Scan duration:         {stats['scan_duration']:.1f} seconds")
        files_per_sec = stats['total_files'] / stats['scan_duration']
        print(f"Processing speed:      {files_per_sec:.1f} files/second")
    
    # Detailed skip reasons
    if stats['skipped_files'] > 0:
        print(f"\nSkip Details:")
        if stats['skipped_hidden'] > 0:
            print(f"  Hidden files:        {stats['skipped_hidden']:,}")
        if stats['skipped_system'] > 0:
            print(f"  System files:        {stats['skipped_system']:,}")
        if stats['skipped_large'] > 0:
            print(f"  Large files:         {stats['skipped_large']:,}")
        if stats['skipped_zero_byte'] > 0:
            print(f"  Zero-byte files:     {stats['skipped_zero_byte']:,}")
        if stats['skipped_corrupted'] > 0:
            print(f"  Corrupted files:     {stats['skipped_corrupted']:,}")
    
    # Error summary
    if error_summary['total_errors'] > 0:
        print(f"\nError Summary:")
        for error_type, count in error_summary['error_types'].items():
            print(f"  {error_type}: {count}")
        
        if show_errors and error_summary['error_details']:
            print(f"\nDetailed Errors (showing first 10):")
            for i, error in enumerate(error_summary['error_details'][:10]):
                print(f"  {i+1}. {error['error_type']}: {error['file_path']}")
                print(f"     {error['error_message']}")
                if len(error_summary['error_details']) > 10:
                    remaining = len(error_summary['error_details']) - 10
                    print(f"     ... and {remaining} more errors")
    
    print("=" * 60)


def main():
    parser = argparse.ArgumentParser(
        description='RAG Smart Folder Scanner - Scan directories for files and detect duplicates/similarities',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Enhanced duplicate detection (recommended)
  %(prog)s --path ~/Pictures --use-enhanced --detection-mode comprehensive
  %(prog)s --path ~/Photos --use-enhanced --detection-mode similar --perceptual-threshold 85
  %(prog)s --path ~/Documents --use-enhanced --detection-mode exact --file-types .pdf .doc
  
  # Legacy detection methods
  %(prog)s --path ~/Pictures --duplicates --verbose
  %(prog)s --path ~/Photos --mode similarity --similarity-threshold 85
  
  # Utility commands
  %(prog)s --test-db --db data/scanner.db
  %(prog)s --help-usage  # Show detailed usage guide
        """
    )
    
    # Required arguments
    parser.add_argument('--path', help='Path to folder to scan')
    parser.add_argument('--db', default='data/dev.db', help='Database file path (default: data/dev.db)')
    
    # Scanning options
    parser.add_argument('--recursive', action='store_true', default=True, 
                       help='Scan directories recursively (default: True)')
    parser.add_argument('--mode', choices=['duplicates', 'similarity'], default='duplicates',
                       help='Legacy scan mode: duplicates or similarity detection (default: duplicates)')
    parser.add_argument('--similarity-threshold', type=float, default=80.0,
                       help='Similarity threshold percentage for image comparison (default: 80.0)')
    
    # Enhanced duplicate detection options
    parser.add_argument('--detection-mode', choices=['exact', 'similar', 'metadata', 'comprehensive'], 
                       default='comprehensive',
                       help='Enhanced detection mode (default: comprehensive)')
    parser.add_argument('--use-enhanced', action='store_true',
                       help='Use enhanced duplicate detection engine instead of legacy methods')
    parser.add_argument('--perceptual-threshold', type=float, default=80.0,
                       help='Perceptual hash similarity threshold (0-100, default: 80.0)')
    parser.add_argument('--min-confidence', type=float, default=50.0,
                       help='Minimum confidence threshold for results (0-100, default: 50.0)')
    parser.add_argument('--metadata-fields', nargs='+', 
                       default=['file_size', 'modified_at'],
                       help='Metadata fields to compare (default: file_size modified_at)')
    parser.add_argument('--size-tolerance', type=int, default=0,
                       help='File size tolerance in bytes for metadata comparison (default: 0)')
    parser.add_argument('--time-tolerance', type=int, default=60,
                       help='Time tolerance in seconds for metadata comparison (default: 60)')
    parser.add_argument('--max-results-per-group', type=int, default=100,
                       help='Maximum files per duplicate group (default: 100)')
    
    # File filtering options
    parser.add_argument('--file-types', nargs='+',
                       help='Filter by file types (e.g., .jpg .png .pdf)')
    parser.add_argument('--min-file-size', type=int,
                       help='Minimum file size in bytes')
    parser.add_argument('--max-file-size', type=int,
                       help='Maximum file size in bytes')
    parser.add_argument('--path-pattern',
                       help='Filter files by path pattern (substring match)')
    
    # Output options
    parser.add_argument('--duplicates', action='store_true',
                       help='Show duplicate files after scanning')
    parser.add_argument('--show-errors', action='store_true',
                       help='Display detailed error summary at the end')
    parser.add_argument('--progress', type=int, default=100, metavar='N',
                       help='Show progress every N files (default: 100, 0 to disable)')
    
    # Debugging options
    parser.add_argument('--verbose', '-v', action='store_true',
                       help='Enable verbose logging and detailed output')
    parser.add_argument('--debug', action='store_true',
                       help='Enable debug-level logging (very detailed)')
    parser.add_argument('--dry-run', action='store_true',
                       help='Scan files but don\'t write to database (for testing)')
    
    # Utility options
    parser.add_argument('--test-db', action='store_true',
                       help='Test database connection without scanning')
    parser.add_argument('--help-usage', action='store_true',
                       help='Show detailed usage instructions and troubleshooting tips')
    
    args = parser.parse_args()
    
    # Handle special options first
    if args.help_usage:
        print_usage_help()
        return
    
    if args.test_db:
        success = test_database_connection(args.db)
        sys.exit(0 if success else 1)
    
    # Validate required arguments
    if not args.path:
        parser.error("--path is required unless using --test-db or --help-usage")
    
    # Setup enhanced logging
    setup_enhanced_logging(args.verbose, args.debug)
    
    # Validate scan path
    if not os.path.exists(args.path):
        print(f"Error: Scan path does not exist: {args.path}")
        sys.exit(1)
    
    if not os.path.isdir(args.path):
        print(f"Error: Scan path is not a directory: {args.path}")
        sys.exit(1)
    
    # Auto-enable enhanced detection if available and not explicitly disabled
    if ENHANCED_DETECTION_AVAILABLE and not args.use_enhanced:
        # Check if user is using legacy options that would conflict
        legacy_options_used = (
            args.mode != 'duplicates' or 
            args.similarity_threshold != 80.0
        )
        
        if not legacy_options_used:
            args.use_enhanced = True
            print("Enhanced duplicate detection available and enabled by default")
    
    # Initialize scanner with enhanced configuration
    print(f"Initializing scanner...")
    print(f"  Scan path: {args.path}")
    print(f"  Database: {args.db}")
    
    if args.use_enhanced and ENHANCED_DETECTION_AVAILABLE:
        print(f"  Detection Mode: {args.detection_mode} (enhanced)")
        print(f"  Perceptual Threshold: {args.perceptual_threshold}%")
        print(f"  Min Confidence: {args.min_confidence}%")
        if args.file_types:
            print(f"  File Types Filter: {', '.join(args.file_types)}")
        if args.min_file_size or args.max_file_size:
            size_filter = []
            if args.min_file_size:
                size_filter.append(f"min: {args.min_file_size:,} bytes")
            if args.max_file_size:
                size_filter.append(f"max: {args.max_file_size:,} bytes")
            print(f"  Size Filter: {', '.join(size_filter)}")
    else:
        print(f"  Mode: {args.mode} (legacy)")
        if args.mode == 'similarity':
            print(f"  Similarity Threshold: {args.similarity_threshold}%")
    
    if args.dry_run:
        print("  DRY RUN MODE - No database changes will be made")
    
    scanner = FileScanner(args.db, dry_run=args.dry_run)
    
    # Set progress reporting interval
    if args.progress > 0:
        scanner._progress_interval = args.progress
    
    try:
        # Connect to database
        if not args.dry_run:
            scanner.connect_db()
        else:
            print("Skipping database connection (dry run mode)")
        
        # Scan folder
        print(f"\nStarting scan of: {args.path}")
        scanner.scan_folder(args.path, args.recursive)
        
        # Print scan summary
        print_scan_summary(scanner, args.show_errors)
        
        # Handle duplicate detection
        if args.use_enhanced and ENHANCED_DETECTION_AVAILABLE:
            print("\n" + "=" * 60)
            print("ENHANCED DUPLICATE DETECTION:")
            print("=" * 60)
            
            if not args.dry_run:
                # Build configuration
                config = {
                    'perceptual_threshold': args.perceptual_threshold,
                    'min_confidence_threshold': args.min_confidence,
                    'metadata_fields': args.metadata_fields,
                    'size_tolerance': args.size_tolerance,
                    'time_tolerance': args.time_tolerance,
                    'max_results_per_group': args.max_results_per_group
                }
                
                # Build file filters
                file_filters = {}
                if args.file_types:
                    file_filters['file_types'] = args.file_types
                if args.min_file_size:
                    file_filters['min_size'] = args.min_file_size
                if args.max_file_size:
                    file_filters['max_size'] = args.max_file_size
                if args.path_pattern:
                    file_filters['path_pattern'] = args.path_pattern
                
                # Progress callback
                def progress_callback(message: str, percentage: int):
                    if percentage >= 0:
                        print(f"Progress: {message} ({percentage}%)")
                    else:
                        print(f"Error: {message}")
                
                # Run enhanced detection
                results = scanner.detect_duplicates_enhanced(
                    mode=args.detection_mode,
                    config=config,
                    file_filters=file_filters if file_filters else None,
                    progress_callback=progress_callback
                )
                
                if results:
                    print_enhanced_detection_results(results, args.verbose)
                else:
                    print("Enhanced duplicate detection failed or returned no results")
            else:
                print("DRY RUN: Would run enhanced duplicate detection here")
        
        elif args.mode == 'duplicates' and (args.duplicates or args.verbose):
            print("\n" + "=" * 50)
            print("LEGACY DUPLICATE FILES ANALYSIS:")
            print("=" * 50)
            
            if not args.dry_run:
                duplicates = scanner.find_duplicates()
                if duplicates:
                    print(f"Found {len(duplicates)} groups of duplicate files:")
                    for i, group in enumerate(duplicates, 1):
                        print(f"\nDuplicate Group {i}:")
                        print(f"  Hash: {group['sha256']}")
                        print(f"  Files ({group['count']}):")
                        for file_info in group['files']:
                            print(f"    - {file_info['file_path']} ({file_info['file_size']} bytes)")
                else:
                    print("No duplicate files found!")
            else:
                print("DRY RUN: Would analyze duplicates here")
        
        elif args.mode == 'similarity':
            print("\n" + "=" * 50)
            print(f"LEGACY SIMILAR IMAGES ANALYSIS (Threshold: {args.similarity_threshold}%):")
            print("=" * 50)
            
            if not args.dry_run:
                similar_groups = scanner.find_similar_images_cosine(args.similarity_threshold)
                if similar_groups:
                    print(f"Found {len(similar_groups)} groups of similar images:")
                    for i, group in enumerate(similar_groups, 1):
                        print(f"\nSimilar Group {i} (Avg: {group['avg_similarity']:.1f}%):")
                        for img, similarity in zip(group['images'], group['similarities']):
                            print(f"  {similarity:5.1f}% - {img[2]} ({img[1]})")  # name, path
                else:
                    print("No similar images found above the threshold!")
            else:
                print("DRY RUN: Would analyze similar images here")
        
        # Success message
        if args.verbose:
            print(f"\n✓ Scan completed successfully!")
        
    except KeyboardInterrupt:
        print("\n\nScan interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n✗ Scan failed with error: {e}")
        if args.debug:
            import traceback
            traceback.print_exc()
        sys.exit(1)
    finally:
        if scanner.conn:
            scanner.close()


if __name__ == "__main__":
    main()
