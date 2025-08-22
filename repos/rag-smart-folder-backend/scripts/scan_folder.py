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
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# Add backend to path for imports
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'backend'))

try:
    import magic
    import imagehash
    from PIL import Image
    import exifread
except ImportError as e:
    print(f"Warning: Some dependencies not available: {e}")
    print("Install with: pip install python-magic pillow imagehash exifread")
    magic = None
    imagehash = None
    Image = None
    exifread = None


class FileScanner:
    """Scans folders and extracts file metadata."""
    
    def __init__(self, db_path: str):
        self.db_path = db_path
        self.conn = None
        self.cursor = None
        self.stats = {
            'total_files': 0,
            'processed_files': 0,
            'duplicates_found': 0,
            'errors': 0
        }
        
    def connect_db(self):
        """Connect to SQLite database."""
        try:
            self.conn = sqlite3.connect(self.db_path)
            self.cursor = self.conn.cursor()
            self._create_tables()
            print(f"Connected to database: {self.db_path}")
        except Exception as e:
            print(f"Error connecting to database: {e}")
            sys.exit(1)
    
    def _create_tables(self):
        """Create tables if they don't exist."""
        schema_path = os.path.join(os.path.dirname(__file__), '..', 'backend', 'sql', 'schema.sql')
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
        except Exception as e:
            print(f"Error computing SHA256 for {file_path}: {e}")
            return ""
    
    def compute_perceptual_hash(self, file_path: str) -> Optional[str]:
        """Compute perceptual hash for images."""
        if not imagehash or not Image:
            return None
        
        try:
            with Image.open(file_path) as img:
                # Convert to RGB if necessary
                if img.mode != 'RGB':
                    img = img.convert('RGB')
                # Compute perceptual hash
                hash_value = imagehash.average_hash(img)
                return str(hash_value)
        except Exception as e:
            print(f"Error computing perceptual hash for {file_path}: {e}")
            return None
    
    def extract_exif_data(self, file_path: str) -> Dict:
        """Extract EXIF data from images."""
        if not exifread:
            return {}
        
        try:
            with open(file_path, 'rb') as f:
                tags = exifread.process_file(f)
            
            exif_data = {}
            for tag, value in tags.items():
                if tag not in ('JPEGThumbnail', 'TIFFThumbnail'):
                    exif_data[tag] = str(value)
            return exif_data
        except Exception as e:
            print(f"Error extracting EXIF from {file_path}: {e}")
            return {}
    
    def get_file_metadata(self, file_path: str) -> Dict:
        """Extract comprehensive file metadata."""
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
            
            # Get MIME type
            if magic:
                try:
                    file_info['mime_type'] = magic.from_file(file_path, mime=True)
                except:
                    pass
            
            # Extract EXIF for images
            if file_info['file_type'] in ['.jpg', '.jpeg', '.png', '.tiff', '.bmp']:
                exif_data = self.extract_exif_data(file_path)
                if exif_data:
                    file_info['metadata_json'] = json.dumps(exif_data)
            
            return file_info
        except Exception as e:
            print(f"Error getting metadata for {file_path}: {e}")
            return {}
    
    def insert_file(self, file_info: Dict, sha256: str, perceptual_hash: Optional[str] = None):
        """Insert file information into database."""
        try:
            self.cursor.execute("""
                INSERT OR REPLACE INTO files 
                (file_path, file_name, file_size, sha256, perceptual_hash, 
                 file_type, mime_type, created_at, modified_at, metadata_json)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                file_info['file_path'],
                file_info['file_name'],
                file_info['file_size'],
                sha256,
                perceptual_hash,
                file_info['file_type'],
                file_info['mime_type'],
                file_info['created_at'],
                file_info['modified_at'],
                file_info['metadata_json']
            ))
            self.conn.commit()
            return True
        except Exception as e:
            print(f"Error inserting file {file_info['file_path']}: {e}")
            self.stats['errors'] += 1
            return False
    
    def scan_folder(self, folder_path: str, recursive: bool = True):
        """Scan a folder for files."""
        if not os.path.exists(folder_path):
            print(f"Error: Folder {folder_path} does not exist")
            return
        
        print(f"Scanning folder: {folder_path}")
        print(f"Recursive: {recursive}")
        print("-" * 50)
        
        if recursive:
            for root, dirs, files in os.walk(folder_path):
                for file in files:
                    file_path = os.path.join(root, file)
                    self._process_file(file_path)
        else:
            for item in os.listdir(folder_path):
                item_path = os.path.join(folder_path, item)
                if os.path.isfile(item_path):
                    self._process_file(item_path)
        
        print("-" * 50)
        print(f"Scan complete!")
        print(f"Total files found: {self.stats['total_files']}")
        print(f"Processed: {self.stats['processed_files']}")
        print(f"Duplicates found: {self.stats['duplicates_found']}")
        print(f"Errors: {self.stats['errors']}")
    
    def _process_file(self, file_path: str):
        """Process a single file."""
        self.stats['total_files'] += 1
        
        try:
            # Skip hidden files and system files
            if os.path.basename(file_path).startswith('.'):
                return
            
            # Get metadata
            file_info = self.get_file_metadata(file_path)
            if not file_info:
                return
            
            # Compute SHA256
            sha256 = self.compute_sha256(file_path)
            if not sha256:
                return
            
            # Check for existing file with same hash
            existing = self.cursor.execute(
                "SELECT file_path FROM files WHERE sha256 = ?", (sha256,)
            ).fetchone()
            
            if existing:
                print(f"Duplicate found: {file_path} (same as {existing[0]})")
                self.stats['duplicates_found'] += 1
            
            # Compute perceptual hash for images
            perceptual_hash = None
            if file_info['file_type'] in ['.jpg', '.jpeg', '.png', '.tiff', '.bmp']:
                perceptual_hash = self.compute_perceptual_hash(file_path)
            
            # Insert into database
            if self.insert_file(file_info, sha256, perceptual_hash):
                self.stats['processed_files'] += 1
                print(f"✓ {file_path} ({file_info['file_size']} bytes)")
            
        except Exception as e:
            print(f"Error processing {file_path}: {e}")
            self.stats['errors'] += 1
    
    def find_duplicates(self) -> List[Tuple]:
        """Find all duplicate files based on SHA256."""
        duplicates = self.cursor.execute("""
            SELECT sha256, COUNT(*) as count, GROUP_CONCAT(file_path) as paths
            FROM files 
            WHERE sha256 IS NOT NULL
            GROUP BY sha256 
            HAVING COUNT(*) > 1
            ORDER BY count DESC
        """).fetchall()
        
        return duplicates
    
    def close(self):
        """Close database connection."""
        if self.conn:
            self.conn.close()


def main():
    parser = argparse.ArgumentParser(description='Scan folder for files and detect duplicates')
    parser.add_argument('--path', required=True, help='Path to folder to scan')
    parser.add_argument('--db', default='data/dev.db', help='Database file path')
    parser.add_argument('--recursive', action='store_true', default=True, help='Scan recursively')
    parser.add_argument('--duplicates', action='store_true', help='Show duplicates after scan')
    
    args = parser.parse_args()
    
    # Create data directory if it doesn't exist
    os.makedirs(os.path.dirname(args.db), exist_ok=True)
    
    # Initialize scanner
    scanner = FileScanner(args.db)
    scanner.connect_db()
    
    try:
        # Scan folder
        scanner.scan_folder(args.path, args.recursive)
        
        # Show duplicates if requested
        if args.duplicates:
            print("\n" + "=" * 50)
            print("DUPLICATE FILES FOUND:")
            print("=" * 50)
            
            duplicates = scanner.find_duplicates()
            if duplicates:
                for sha256, count, paths in duplicates:
                    print(f"\nHash: {sha256}")
                    print(f"Count: {count}")
                    print("Files:")
                    for path in paths.split(','):
                        print(f"  - {path}")
            else:
                print("No duplicate files found!")
        
    finally:
        scanner.close()


if __name__ == "__main__":
    main()
