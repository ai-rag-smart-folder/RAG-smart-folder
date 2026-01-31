"""
Pytest configuration and fixtures for scanner tests.
"""

import pytest
import tempfile
import os
import sqlite3
import shutil
from pathlib import Path
from PIL import Image
import json
from datetime import datetime


@pytest.fixture
def temp_db():
    """Create a temporary database for testing."""
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
        db_path = f.name
    
    # Create the database with schema
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Create basic files table
    cursor.execute("""
        CREATE TABLE files (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            file_path TEXT NOT NULL,
            file_name TEXT NOT NULL,
            file_size INTEGER,
            sha256 TEXT,
            perceptual_hash TEXT,
            file_type TEXT,
            mime_type TEXT,
            width INTEGER,
            height INTEGER,
            created_at TIMESTAMP,
            modified_at TIMESTAMP,
            metadata_json TEXT,
            added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    conn.commit()
    conn.close()
    
    yield db_path
    
    # Cleanup
    if os.path.exists(db_path):
        os.unlink(db_path)


@pytest.fixture
def temp_db_no_columns():
    """Create a temporary database without width/height columns for migration testing."""
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
        db_path = f.name
    
    # Create the database with old schema (no width/height)
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    cursor.execute("""
        CREATE TABLE files (
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
    
    conn.commit()
    conn.close()
    
    yield db_path
    
    # Cleanup
    if os.path.exists(db_path):
        os.unlink(db_path)


@pytest.fixture
def test_files_dir():
    """Create a temporary directory with test files."""
    test_dir = tempfile.mkdtemp(prefix="scanner_test_")
    
    # Create various test files
    test_files = {
        'text_file.txt': 'This is a test text file',
        'duplicate1.txt': 'This is duplicate content',
        'duplicate2.txt': 'This is duplicate content',
        'unique.txt': 'This is unique content',
        'empty.txt': '',
        'large_text.txt': 'A' * 10000,  # 10KB file
    }
    
    for filename, content in test_files.items():
        file_path = os.path.join(test_dir, filename)
        with open(file_path, 'w') as f:
            f.write(content)
    
    # Create a subdirectory
    subdir = os.path.join(test_dir, 'subdir')
    os.makedirs(subdir)
    
    with open(os.path.join(subdir, 'sub_file.txt'), 'w') as f:
        f.write('Subdirectory file')
    
    # Create hidden files
    with open(os.path.join(test_dir, '.hidden_file'), 'w') as f:
        f.write('Hidden file content')
    
    yield test_dir
    
    # Cleanup
    shutil.rmtree(test_dir, ignore_errors=True)


@pytest.fixture
def test_images_dir():
    """Create a temporary directory with test image files."""
    test_dir = tempfile.mkdtemp(prefix="scanner_images_test_")
    
    # Create test images
    images = [
        ('test_image_100x100.png', (100, 100), 'RGB'),
        ('test_image_200x150.jpg', (200, 150), 'RGB'),
        ('duplicate_image1.png', (50, 50), 'RGB'),
        ('duplicate_image2.png', (50, 50), 'RGB'),  # Same size, will have similar hash
        ('grayscale.png', (100, 100), 'L'),
    ]
    
    for filename, size, mode in images:
        img = Image.new(mode, size, color='red' if 'duplicate' in filename else 'blue')
        img.save(os.path.join(test_dir, filename))
    
    # Create a corrupted "image" file
    with open(os.path.join(test_dir, 'corrupted.jpg'), 'wb') as f:
        f.write(b'This is not a valid image file')
    
    yield test_dir
    
    # Cleanup
    shutil.rmtree(test_dir, ignore_errors=True)


@pytest.fixture
def mixed_files_dir():
    """Create a directory with mixed file types for comprehensive testing."""
    test_dir = tempfile.mkdtemp(prefix="scanner_mixed_test_")
    
    # Text files
    with open(os.path.join(test_dir, 'document.txt'), 'w') as f:
        f.write('Document content')
    
    # Image files
    img = Image.new('RGB', (100, 100), color='green')
    img.save(os.path.join(test_dir, 'image.png'))
    
    # Binary file
    with open(os.path.join(test_dir, 'binary.bin'), 'wb') as f:
        f.write(b'\x00\x01\x02\x03\x04\x05')
    
    # JSON file
    with open(os.path.join(test_dir, 'data.json'), 'w') as f:
        json.dump({'test': 'data'}, f)
    
    # Create files with permission issues (if possible)
    restricted_file = os.path.join(test_dir, 'restricted.txt')
    with open(restricted_file, 'w') as f:
        f.write('Restricted content')
    
    # Try to make it read-only (may not work on all systems)
    try:
        os.chmod(restricted_file, 0o444)
    except OSError:
        pass  # Ignore if we can't change permissions
    
    yield test_dir
    
    # Cleanup - restore permissions first
    try:
        os.chmod(restricted_file, 0o644)
    except (OSError, FileNotFoundError):
        pass
    
    shutil.rmtree(test_dir, ignore_errors=True)


@pytest.fixture
def sample_file_metadata():
    """Sample file metadata for testing."""
    return {
        'file_path': '/test/path/file.txt',
        'file_name': 'file.txt',
        'file_size': 1024,
        'sha256': 'abc123def456',
        'perceptual_hash': 'hash123',
        'file_type': '.txt',
        'mime_type': 'text/plain',
        'width': None,
        'height': None,
        'created_at': datetime.now(),
        'modified_at': datetime.now(),
        'metadata_json': '{}',
    }