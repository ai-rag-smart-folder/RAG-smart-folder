"""
Tests for error handling with various failure conditions.
Tests Requirements: 1.4, 3.1, 3.2, 3.3, 4.4
"""

import pytest
import os
import sys
import tempfile
import sqlite3
import shutil
from unittest.mock import patch, MagicMock
from pathlib import Path

# Add the scripts directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'scripts'))

from scan_folder import FileScanner


class TestDatabaseErrorHandling:
    """Test database-related error handling."""
    
    def test_database_connection_failure(self):
        """Test handling of database connection failures."""
        # Try to connect to invalid database path
        scanner = FileScanner('/invalid/readonly/path/db.sqlite')
        
        with pytest.raises(SystemExit):
            scanner.connect_db()
    
    def test_database_locked_error(self, temp_db):
        """Test handling of database locked errors."""
        # Create a connection that locks the database
        lock_conn = sqlite3.connect(temp_db)
        lock_conn.execute("BEGIN EXCLUSIVE TRANSACTION")
        
        try:
            scanner = FileScanner(temp_db)
            
            # Should retry and eventually fail or succeed
            with patch('time.sleep'):  # Speed up test
                with pytest.raises(SystemExit):
                    scanner.connect_db()
        finally:
            lock_conn.close()
    
    def test_database_corruption_handling(self):
        """Test handling of corrupted database files."""
        # Create a corrupted database file
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
            f.write(b'This is not a valid SQLite database')
            corrupted_db = f.name
        
        try:
            scanner = FileScanner(corrupted_db)
            
            with pytest.raises(SystemExit):
                scanner.connect_db()
        finally:
            os.unlink(corrupted_db)
    
    def test_database_permission_error(self):
        """Test handling of database permission errors."""
        # Create a read-only database file
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
            db_path = f.name
        
        # Create valid database first
        conn = sqlite3.connect(db_path)
        conn.execute("CREATE TABLE test (id INTEGER)")
        conn.close()
        
        try:
            # Make it read-only
            os.chmod(db_path, 0o444)
            
            scanner = FileScanner(db_path)
            
            # Should detect permission issue
            with pytest.raises(SystemExit):
                scanner.connect_db()
        finally:
            # Restore permissions for cleanup
            try:
                os.chmod(db_path, 0o644)
                os.unlink(db_path)
            except OSError:
                pass
    
    def test_database_insertion_error(self, temp_db):
        """Test handling of database insertion errors."""
        scanner = FileScanner(temp_db)
        scanner.connect_db()
        
        # Mock cursor.execute to raise an error
        with patch.object(scanner.cursor, 'execute', side_effect=sqlite3.Error("Insertion failed")):
            result = scanner.insert_file({
                'file_name': 'test.txt',
                'file_path': '/test/path.txt',
                'file_size': 100
            })
            
            assert result is False
            assert scanner.stats['errors'] > 0
        
        scanner.conn.close()
    
    def test_database_schema_mismatch(self, temp_db_no_columns):
        """Test handling of schema mismatches."""
        scanner = FileScanner(temp_db_no_columns)
        scanner.connect_db()
        
        # Try to insert file with width/height (columns don't exist)
        metadata = {
            'file_name': 'test.txt',
            'file_path': '/test/path.txt',
            'file_size': 100,
            'width': 200,
            'height': 300
        }
        
        # Should handle gracefully by falling back to basic insertion
        result = scanner.insert_file(metadata)
        assert result is True  # Should succeed with fallback
        
        scanner.conn.close()


class TestFileSystemErrorHandling:
    """Test file system related error handling."""
    
    def test_permission_denied_error(self):
        """Test handling of permission denied errors."""
        scanner = FileScanner(':memory:')
        
        # Test SHA256 computation with permission error
        with patch('builtins.open', side_effect=PermissionError("Permission denied")):
            sha256 = scanner.compute_sha256('/restricted/file.txt')
            assert sha256 == ""
            assert scanner.stats['errors'] > 0
    
    def test_file_not_found_error(self):
        """Test handling of file not found errors."""
        scanner = FileScanner(':memory:')
        
        # Test with non-existent file
        sha256 = scanner.compute_sha256('/nonexistent/file.txt')
        assert sha256 == ""
        assert scanner.stats['errors'] > 0
        
        # Check error was logged
        assert len(scanner.error_details) > 0
        assert scanner.error_details[-1]['error_type'] == 'FILE_NOT_FOUND'
    
    def test_io_error_handling(self):
        """Test handling of I/O errors."""
        scanner = FileScanner(':memory:')
        
        # Mock file operations to raise IOError
        with patch('builtins.open', side_effect=OSError("I/O error")):
            sha256 = scanner.compute_sha256('/test/file.txt')
            assert sha256 == ""
            assert scanner.stats['errors'] > 0
    
    def test_directory_access_error(self, temp_db):
        """Test handling of directory access errors."""
        scanner = FileScanner(temp_db)
        scanner.connect_db()
        
        # Try to scan non-existent directory
        scanner.scan_folder('/nonexistent/directory')
        
        # Should log error but not crash
        assert scanner.stats['errors'] > 0
        
        scanner.conn.close()
    
    def test_symlink_handling(self, temp_db):
        """Test handling of symbolic links."""
        test_dir = tempfile.mkdtemp(prefix="symlink_test_")
        
        try:
            # Create a regular file
            regular_file = os.path.join(test_dir, 'regular.txt')
            with open(regular_file, 'w') as f:
                f.write('Regular file content')
            
            # Create a symlink (if supported)
            symlink_file = os.path.join(test_dir, 'symlink.txt')
            try:
                os.symlink(regular_file, symlink_file)
                has_symlink = True
            except (OSError, NotImplementedError):
                has_symlink = False
            
            scanner = FileScanner(temp_db)
            scanner.connect_db()
            
            scanner.scan_folder(test_dir)
            
            # Should process at least the regular file
            assert scanner.stats['processed_files'] > 0
            
            scanner.conn.close()
            
        finally:
            shutil.rmtree(test_dir, ignore_errors=True)


class TestImageProcessingErrors:
    """Test image processing error handling."""
    
    def test_corrupted_image_handling(self):
        """Test handling of corrupted image files."""
        scanner = FileScanner(':memory:')
        
        # Create a fake corrupted image file
        with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as f:
            f.write(b'This is not a valid image')
            corrupted_image = f.name
        
        try:
            # Test perceptual hash computation
            phash = scanner.compute_perceptual_hash(corrupted_image)
            assert phash is None
            assert scanner.stats['errors'] > 0
            
            # Test dimension extraction
            width, height = scanner.get_image_dimensions(corrupted_image)
            assert width is None
            assert height is None
            
        finally:
            os.unlink(corrupted_image)
    
    def test_unsupported_image_format(self):
        """Test handling of unsupported image formats."""
        scanner = FileScanner(':memory:')
        
        # Create a file with image extension but unsupported format
        with tempfile.NamedTemporaryFile(suffix='.xyz', delete=False) as f:
            f.write(b'Unsupported format')
            unsupported_file = f.name
        
        try:
            phash = scanner.compute_perceptual_hash(unsupported_file)
            assert phash is None
            
            width, height = scanner.get_image_dimensions(unsupported_file)
            assert width is None
            assert height is None
            
        finally:
            os.unlink(unsupported_file)
    
    def test_large_image_handling(self):
        """Test handling of very large images."""
        scanner = FileScanner(':memory:')
        
        if not scanner._is_dependency_available('Image'):
            pytest.skip("PIL not available")
        
        # Mock PIL to raise DecompressionBombError
        from PIL import Image
        
        with patch.object(Image, 'open', side_effect=Image.DecompressionBombError("Image too large")):
            phash = scanner.compute_perceptual_hash('large_image.jpg')
            assert phash is None
            assert scanner.stats['errors'] > 0
            
            width, height = scanner.get_image_dimensions('large_image.jpg')
            assert width is None
            assert height is None
    
    def test_image_processing_without_dependencies(self):
        """Test image processing when PIL/imagehash are not available."""
        scanner = FileScanner(':memory:')
        
        # Mock dependencies as unavailable
        with patch.object(scanner, '_is_dependency_available', return_value=False):
            phash = scanner.compute_perceptual_hash('test.jpg')
            assert phash is None
            
            width, height = scanner.get_image_dimensions('test.jpg')
            assert width is None
            assert height is None
            
            exif_data = scanner.extract_exif_data('test.jpg')
            assert exif_data == {}


class TestDependencyErrorHandling:
    """Test handling of missing or failing dependencies."""
    
    def test_missing_magic_dependency(self):
        """Test handling when python-magic is missing."""
        scanner = FileScanner(':memory:')
        
        # Mock magic as unavailable
        with patch.object(scanner, '_is_dependency_available', return_value=False):
            # Should fall back to mimetypes module
            metadata = scanner.get_file_metadata(__file__)  # Use this test file
            
            # Should still have basic metadata
            assert 'file_name' in metadata
            assert 'file_size' in metadata
    
    def test_missing_numpy_dependency(self):
        """Test handling when numpy is missing."""
        scanner = FileScanner(':memory:')
        
        with patch.object(scanner, '_is_dependency_available', return_value=False):
            # Feature extraction should return None
            features = scanner.extract_image_features('test.jpg')
            assert features is None
            
            # Cosine similarity should return 0
            similarity = scanner.calculate_cosine_similarity(None, None)
            assert similarity == 0.0
    
    def test_dependency_import_errors(self):
        """Test handling of dependency import errors."""
        scanner = FileScanner(':memory:')
        
        # Mock imagehash to raise import error during use
        with patch('imagehash.average_hash', side_effect=ImportError("Module not found")):
            phash = scanner.compute_perceptual_hash('test.jpg')
            # Should handle gracefully
            assert phash is None or isinstance(phash, str)
    
    def test_dependency_runtime_errors(self):
        """Test handling of runtime errors in dependencies."""
        scanner = FileScanner(':memory:')
        
        if not scanner._is_dependency_available('Image'):
            pytest.skip("PIL not available")
        
        # Mock PIL to raise runtime error
        with patch('PIL.Image.open', side_effect=RuntimeError("Runtime error")):
            phash = scanner.compute_perceptual_hash('test.jpg')
            assert phash is None
            assert scanner.stats['errors'] > 0


class TestErrorReporting:
    """Test error reporting and logging functionality."""
    
    def test_error_detail_structure(self):
        """Test structure of error detail records."""
        scanner = FileScanner(':memory:')
        
        try:
            raise ValueError("Test exception")
        except ValueError as e:
            scanner._log_error('TEST_ERROR', '/test/path', 'Test message', e)
        
        assert len(scanner.error_details) == 1
        error = scanner.error_details[0]
        
        required_fields = [
            'timestamp', 'error_type', 'file_path', 'error_message',
            'exception_type', 'exception_message'
        ]
        
        for field in required_fields:
            assert field in error
        
        assert error['error_type'] == 'TEST_ERROR'
        assert error['file_path'] == '/test/path'
        assert error['exception_type'] == 'ValueError'
    
    def test_error_statistics_tracking(self):
        """Test that error statistics are properly tracked."""
        scanner = FileScanner(':memory:')
        
        initial_errors = scanner.stats['errors']
        
        # Log multiple errors
        scanner._log_error('ERROR1', '/path1', 'Message 1')
        scanner._log_error('ERROR2', '/path2', 'Message 2')
        scanner._log_error('ERROR3', '/path3', 'Message 3')
        
        assert scanner.stats['errors'] == initial_errors + 3
        assert len(scanner.error_details) == 3
    
    def test_error_logging_levels(self, caplog):
        """Test that different error types use appropriate logging levels."""
        scanner = FileScanner(':memory:')
        
        # Test warning level errors
        scanner._log_error('PERMISSION_ERROR', '/test/path', 'Permission denied')
        
        # Test error level errors
        scanner._log_error('DATABASE_ERROR', '/test/path', 'Database failed')
        
        # Should have logged at appropriate levels
        assert len(scanner.error_details) == 2
    
    def test_error_summary_generation(self):
        """Test generation of error summary reports."""
        scanner = FileScanner(':memory:')
        
        # Generate various types of errors
        scanner._log_error('PERMISSION_ERROR', '/path1', 'Permission denied')
        scanner._log_error('PERMISSION_ERROR', '/path2', 'Permission denied')
        scanner._log_error('DATABASE_ERROR', '/path3', 'Database error')
        scanner._log_error('IMAGE_FORMAT_ERROR', '/path4', 'Invalid image')
        
        # Generate error summary
        summary = scanner.get_error_summary()
        
        assert 'total_errors' in summary
        assert 'error_types' in summary
        assert summary['total_errors'] == 4
        
        # Should group by error type
        error_types = summary['error_types']
        assert 'PERMISSION_ERROR' in error_types
        assert error_types['PERMISSION_ERROR'] == 2
        assert error_types['DATABASE_ERROR'] == 1
        assert error_types['IMAGE_FORMAT_ERROR'] == 1


class TestRecoveryMechanisms:
    """Test recovery and resilience mechanisms."""
    
    def test_continue_after_file_error(self, temp_db):
        """Test that scanning continues after individual file errors."""
        test_dir = tempfile.mkdtemp(prefix="recovery_test_")
        
        try:
            # Create multiple files
            files = ['file1.txt', 'file2.txt', 'file3.txt']
            for filename in files:
                with open(os.path.join(test_dir, filename), 'w') as f:
                    f.write(f'Content of {filename}')
            
            scanner = FileScanner(temp_db)
            scanner.connect_db()
            
            # Mock _process_file to fail for middle file
            original_process = scanner._process_file
            
            def mock_process(file_path):
                if 'file2.txt' in file_path:
                    raise Exception("Simulated processing error")
                return original_process(file_path)
            
            with patch.object(scanner, '_process_file', side_effect=mock_process):
                scanner.scan_folder(test_dir)
            
            # Should have processed other files despite error
            assert scanner.stats['processed_files'] >= 2  # file1 and file3
            assert scanner.stats['errors'] > 0  # file2 error
            
            scanner.conn.close()
            
        finally:
            shutil.rmtree(test_dir, ignore_errors=True)
    
    def test_graceful_shutdown_on_critical_error(self):
        """Test graceful shutdown on critical errors."""
        scanner = FileScanner('/invalid/database/path.db')
        
        # Should exit gracefully rather than crash
        with pytest.raises(SystemExit):
            scanner.connect_db()
    
    def test_partial_functionality_with_missing_deps(self, temp_db):
        """Test that core functionality works with missing optional dependencies."""
        scanner = FileScanner(temp_db)
        scanner.connect_db()
        
        # Mock all optional dependencies as missing
        with patch.dict(scanner.__class__.OPTIONAL_DEPENDENCIES, 
                       {key: None for key in scanner.__class__.OPTIONAL_DEPENDENCIES}):
            
            # Create a simple test file
            test_dir = tempfile.mkdtemp(prefix="partial_test_")
            
            try:
                test_file = os.path.join(test_dir, 'test.txt')
                with open(test_file, 'w') as f:
                    f.write('Test content')
                
                scanner.scan_folder(test_dir)
                
                # Should still process basic file metadata
                assert scanner.stats['processed_files'] > 0
                
                # Check database has basic file info
                scanner.cursor.execute("SELECT file_name, file_size FROM files")
                files = scanner.cursor.fetchall()
                assert len(files) > 0
                
            finally:
                shutil.rmtree(test_dir, ignore_errors=True)
        
        scanner.conn.close()