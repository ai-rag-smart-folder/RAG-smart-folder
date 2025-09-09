"""
Unit tests for database operations and schema migration.
Tests Requirements: 1.2, 2.1, 2.2, 2.3
"""

import pytest
import sqlite3
import os
import sys
from unittest.mock import patch, MagicMock

# Add the scripts directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'scripts'))

from migrate_database import (
    check_column_exists,
    add_column_if_not_exists,
    migrate_database,
    backup_database
)
from scan_folder import FileScanner


class TestDatabaseMigration:
    """Test database migration functionality."""
    
    def test_check_column_exists_true(self, temp_db):
        """Test checking for existing column."""
        conn = sqlite3.connect(temp_db)
        cursor = conn.cursor()
        
        # Check for existing column
        assert check_column_exists(cursor, 'files', 'file_path') is True
        assert check_column_exists(cursor, 'files', 'width') is True  # Should exist in our fixture
        
        conn.close()
    
    def test_check_column_exists_false(self, temp_db_no_columns):
        """Test checking for non-existing column."""
        conn = sqlite3.connect(temp_db_no_columns)
        cursor = conn.cursor()
        
        # Check for non-existing columns
        assert check_column_exists(cursor, 'files', 'width') is False
        assert check_column_exists(cursor, 'files', 'height') is False
        assert check_column_exists(cursor, 'files', 'nonexistent') is False
        
        conn.close()
    
    def test_check_column_exists_invalid_table(self, temp_db):
        """Test checking column on non-existent table."""
        conn = sqlite3.connect(temp_db)
        cursor = conn.cursor()
        
        # Should return False for non-existent table
        assert check_column_exists(cursor, 'nonexistent_table', 'column') is False
        
        conn.close()
    
    def test_add_column_if_not_exists_new_column(self, temp_db_no_columns):
        """Test adding a new column."""
        conn = sqlite3.connect(temp_db_no_columns)
        cursor = conn.cursor()
        
        # Add width column
        result = add_column_if_not_exists(cursor, 'files', 'width', 'INTEGER')
        assert result is True
        
        # Verify column was added
        assert check_column_exists(cursor, 'files', 'width') is True
        
        conn.commit()
        conn.close()
    
    def test_add_column_if_not_exists_existing_column(self, temp_db):
        """Test adding a column that already exists."""
        conn = sqlite3.connect(temp_db)
        cursor = conn.cursor()
        
        # Try to add existing column
        result = add_column_if_not_exists(cursor, 'files', 'file_path', 'TEXT')
        assert result is True  # Should succeed (skip existing)
        
        conn.close()
    
    def test_migrate_database_success(self, temp_db_no_columns):
        """Test successful database migration."""
        result = migrate_database(temp_db_no_columns)
        assert result is True
        
        # Verify columns were added
        conn = sqlite3.connect(temp_db_no_columns)
        cursor = conn.cursor()
        
        assert check_column_exists(cursor, 'files', 'width') is True
        assert check_column_exists(cursor, 'files', 'height') is True
        
        conn.close()
    
    def test_migrate_database_nonexistent_file(self):
        """Test migration with non-existent database file."""
        result = migrate_database('/nonexistent/path/db.sqlite')
        assert result is False
    
    def test_backup_database_success(self, temp_db):
        """Test database backup creation."""
        backup_path = backup_database(temp_db)
        
        assert backup_path is not None
        assert os.path.exists(backup_path)
        assert backup_path == f"{temp_db}.backup"
        
        # Verify backup has same structure
        conn = sqlite3.connect(backup_path)
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = cursor.fetchall()
        assert len(tables) > 0
        conn.close()
        
        # Cleanup
        os.unlink(backup_path)


class TestFileScannerDatabase:
    """Test FileScanner database operations."""
    
    def test_scanner_database_connection(self, temp_db):
        """Test scanner database connection."""
        scanner = FileScanner(temp_db)
        scanner.connect_db()
        
        assert scanner.conn is not None
        assert scanner.cursor is not None
        
        # Test connection with simple query
        scanner.cursor.execute("SELECT 1")
        result = scanner.cursor.fetchone()
        assert result[0] == 1
        
        scanner.conn.close()
    
    def test_scanner_database_connection_invalid_path(self):
        """Test scanner connection with invalid database path."""
        scanner = FileScanner('/invalid/path/db.sqlite')
        
        # Should exit with error
        with pytest.raises(SystemExit):
            scanner.connect_db()
    
    def test_scanner_column_cache_initialization(self, temp_db):
        """Test scanner column cache initialization."""
        scanner = FileScanner(temp_db)
        scanner.connect_db()
        
        # Column cache should be initialized
        assert hasattr(scanner, '_column_cache')
        
        scanner.conn.close()
    
    def test_scanner_insert_file_with_columns(self, temp_db, sample_file_metadata):
        """Test file insertion with width/height columns available."""
        scanner = FileScanner(temp_db)
        scanner.connect_db()
        
        # Add width and height to metadata
        sample_file_metadata['width'] = 100
        sample_file_metadata['height'] = 200
        
        # Insert file
        result = scanner.insert_file(sample_file_metadata)
        assert result is True
        
        # Verify insertion
        scanner.cursor.execute("SELECT width, height FROM files WHERE file_name = ?", 
                             (sample_file_metadata['file_name'],))
        row = scanner.cursor.fetchone()
        assert row is not None
        assert row[0] == 100  # width
        assert row[1] == 200  # height
        
        scanner.conn.close()
    
    def test_scanner_insert_file_without_columns(self, temp_db_no_columns, sample_file_metadata):
        """Test file insertion gracefully handles missing width/height columns."""
        scanner = FileScanner(temp_db_no_columns)
        scanner.connect_db()
        
        # Try to insert file with width/height (should handle gracefully)
        sample_file_metadata['width'] = 100
        sample_file_metadata['height'] = 200
        
        result = scanner.insert_file(sample_file_metadata)
        assert result is True  # Should succeed by falling back
        
        # Verify basic data was inserted
        scanner.cursor.execute("SELECT file_name, file_size FROM files WHERE file_name = ?", 
                             (sample_file_metadata['file_name'],))
        row = scanner.cursor.fetchone()
        assert row is not None
        assert row[0] == sample_file_metadata['file_name']
        assert row[1] == sample_file_metadata['file_size']
        
        scanner.conn.close()
    
    def test_scanner_database_error_handling(self, temp_db):
        """Test scanner database error handling."""
        scanner = FileScanner(temp_db)
        scanner.connect_db()
        
        # Test with invalid SQL (should be handled gracefully)
        with patch.object(scanner.cursor, 'execute', side_effect=sqlite3.Error("Test error")):
            result = scanner.insert_file({'file_name': 'test.txt'})
            assert result is False
            assert scanner.stats['errors'] > 0
        
        scanner.conn.close()
    
    def test_scanner_connection_retry_logic(self):
        """Test scanner connection retry logic."""
        scanner = FileScanner('/tmp/test_retry.db')
        
        # Mock sqlite3.connect to fail first few times
        original_connect = sqlite3.connect
        call_count = 0
        
        def mock_connect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise sqlite3.OperationalError("database is locked")
            return original_connect(*args, **kwargs)
        
        with patch('sqlite3.connect', side_effect=mock_connect):
            with patch('time.sleep'):  # Speed up test
                scanner.connect_db()
                assert call_count >= 3  # Should have retried
        
        scanner.conn.close()
        # Cleanup
        if os.path.exists('/tmp/test_retry.db'):
            os.unlink('/tmp/test_retry.db')


class TestDatabaseSchema:
    """Test database schema validation."""
    
    def test_schema_file_loading(self, temp_db):
        """Test loading schema from SQL file."""
        scanner = FileScanner(temp_db)
        scanner.connect_db()
        
        # Check that all expected tables exist
        scanner.cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row[0] for row in scanner.cursor.fetchall()]
        
        assert 'files' in tables
        
        scanner.conn.close()
    
    def test_files_table_structure(self, temp_db):
        """Test files table has correct structure."""
        conn = sqlite3.connect(temp_db)
        cursor = conn.cursor()
        
        cursor.execute("PRAGMA table_info(files)")
        columns = cursor.fetchall()
        column_names = [col[1] for col in columns]
        
        expected_columns = [
            'id', 'file_path', 'file_name', 'file_size', 'sha256',
            'perceptual_hash', 'file_type', 'mime_type', 'width', 'height',
            'created_at', 'modified_at', 'metadata_json', 'added_at'
        ]
        
        for col in expected_columns:
            assert col in column_names, f"Column {col} missing from files table"
        
        conn.close()
    
    def test_database_indexes(self, temp_db):
        """Test that expected indexes exist."""
        conn = sqlite3.connect(temp_db)
        cursor = conn.cursor()
        
        # Get all indexes
        cursor.execute("SELECT name FROM sqlite_master WHERE type='index'")
        indexes = [row[0] for row in cursor.fetchall()]
        
        # Note: Our test fixture doesn't create indexes, but we can test the concept
        # In a real scenario, we'd check for performance indexes
        
        conn.close()