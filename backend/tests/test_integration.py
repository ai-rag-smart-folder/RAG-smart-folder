"""
Integration tests for end-to-end scanning scenarios.
Tests Requirements: 1.1, 1.3, 1.4, 3.1, 3.2, 3.3
"""

import pytest
import os
import sys
import tempfile
import sqlite3
import shutil
from pathlib import Path

# Add the scripts directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'scripts'))

from scan_folder import FileScanner


class TestEndToEndScanning:
    """Test complete scanning workflows."""
    
    def test_scan_folder_basic(self, test_files_dir, temp_db):
        """Test basic folder scanning functionality."""
        scanner = FileScanner(temp_db)
        scanner.connect_db()
        
        # Scan the test directory
        scanner.scan_folder(test_files_dir)
        
        # Verify results
        assert scanner.stats['total_files'] > 0
        assert scanner.stats['processed_files'] > 0
        
        # Check database has entries
        scanner.cursor.execute("SELECT COUNT(*) FROM files")
        file_count = scanner.cursor.fetchone()[0]
        assert file_count > 0
        
        scanner.conn.close()
    
    def test_scan_folder_with_subdirectories(self, test_files_dir, temp_db):
        """Test scanning folder with subdirectories."""
        scanner = FileScanner(temp_db)
        scanner.connect_db()
        
        # Scan recursively
        scanner.scan_folder(test_files_dir)
        
        # Should find files in subdirectories
        scanner.cursor.execute("SELECT file_path FROM files WHERE file_path LIKE '%subdir%'")
        subdir_files = scanner.cursor.fetchall()
        assert len(subdir_files) > 0
        
        scanner.conn.close()
    
    def test_scan_mixed_file_types(self, mixed_files_dir, temp_db):
        """Test scanning directory with mixed file types."""
        scanner = FileScanner(temp_db)
        scanner.connect_db()
        
        scanner.scan_folder(mixed_files_dir)
        
        # Verify different file types were processed
        scanner.cursor.execute("SELECT DISTINCT file_type FROM files")
        file_types = [row[0] for row in scanner.cursor.fetchall()]
        
        # Should have multiple file types
        assert len(file_types) > 1
        
        scanner.conn.close()
    
    def test_scan_images_with_dimensions(self, test_images_dir, temp_db):
        """Test scanning images and extracting dimensions."""
        scanner = FileScanner(temp_db)
        scanner.connect_db()
        
        scanner.scan_folder(test_images_dir)
        
        # Check for image files with dimensions
        scanner.cursor.execute("""
            SELECT file_name, width, height 
            FROM files 
            WHERE file_type IN ('.png', '.jpg') 
            AND width IS NOT NULL 
            AND height IS NOT NULL
        """)
        
        image_files = scanner.cursor.fetchall()
        
        if scanner._is_dependency_available('Image'):
            assert len(image_files) > 0
            # Verify specific dimensions
            for file_name, width, height in image_files:
                assert width > 0
                assert height > 0
        
        scanner.conn.close()
    
    def test_duplicate_detection(self, test_files_dir, temp_db):
        """Test duplicate file detection."""
        scanner = FileScanner(temp_db)
        scanner.connect_db()
        
        scanner.scan_folder(test_files_dir)
        
        # Find duplicates by SHA256
        duplicates = scanner.find_duplicates()
        
        # Should find the duplicate files we created
        assert len(duplicates) > 0
        
        # Verify duplicate group structure
        for group in duplicates:
            assert 'files' in group
            assert len(group['files']) >= 2  # At least 2 files in duplicate group
            
            # All files in group should have same SHA256
            sha256_values = [f['sha256'] for f in group['files']]
            assert len(set(sha256_values)) == 1  # All same
        
        scanner.conn.close()
    
    def test_similarity_detection(self, test_images_dir, temp_db):
        """Test image similarity detection."""
        scanner = FileScanner(temp_db)
        scanner.connect_db()
        
        scanner.scan_folder(test_images_dir)
        
        if scanner._is_dependency_available('imagehash'):
            # Find similar images
            similar_groups = scanner.find_similar_images()
            
            # May or may not find similar groups depending on test images
            assert isinstance(similar_groups, list)
            
            for group in similar_groups:
                assert 'images' in group
                assert 'similarities' in group
                assert len(group['images']) >= 2
        
        scanner.conn.close()
    
    def test_scan_empty_directory(self, temp_db):
        """Test scanning an empty directory."""
        empty_dir = tempfile.mkdtemp(prefix="empty_test_")
        
        try:
            scanner = FileScanner(temp_db)
            scanner.connect_db()
            
            scanner.scan_folder(empty_dir)
            
            # Should complete without errors
            assert scanner.stats['total_files'] == 0
            assert scanner.stats['processed_files'] == 0
            
            scanner.conn.close()
        finally:
            shutil.rmtree(empty_dir, ignore_errors=True)
    
    def test_scan_nonexistent_directory(self, temp_db):
        """Test scanning a non-existent directory."""
        scanner = FileScanner(temp_db)
        scanner.connect_db()
        
        # Should handle gracefully
        scanner.scan_folder('/nonexistent/directory')
        
        # Should log error but not crash
        assert scanner.stats['errors'] > 0
        
        scanner.conn.close()


class TestScannerStatistics:
    """Test scanner statistics and reporting."""
    
    def test_statistics_initialization(self, temp_db):
        """Test that statistics are properly initialized."""
        scanner = FileScanner(temp_db)
        
        expected_stats = [
            'total_files', 'processed_files', 'skipped_files', 
            'duplicates_found', 'errors', 'skipped_hidden',
            'skipped_system', 'skipped_large', 'skipped_zero_byte',
            'skipped_corrupted', 'start_time', 'end_time'
        ]
        
        for stat in expected_stats:
            assert stat in scanner.stats
    
    def test_statistics_tracking(self, test_files_dir, temp_db):
        """Test that statistics are properly tracked during scanning."""
        scanner = FileScanner(temp_db)
        scanner.connect_db()
        
        initial_processed = scanner.stats['processed_files']
        initial_total = scanner.stats['total_files']
        
        scanner.scan_folder(test_files_dir)
        
        # Statistics should have increased
        assert scanner.stats['processed_files'] > initial_processed
        assert scanner.stats['total_files'] > initial_total
        
        scanner.conn.close()
    
    def test_error_statistics(self, temp_db):
        """Test error statistics tracking."""
        scanner = FileScanner(temp_db)
        
        initial_errors = scanner.stats['errors']
        
        # Generate some errors
        scanner._log_error('TEST_ERROR', '/test/path', 'Test error')
        scanner._log_error('ANOTHER_ERROR', '/test/path2', 'Another error')
        
        assert scanner.stats['errors'] == initial_errors + 2
        assert len(scanner.error_details) == 2
    
    def test_progress_reporting(self, test_files_dir, temp_db):
        """Test progress reporting during scanning."""
        scanner = FileScanner(temp_db)
        scanner.connect_db()
        
        # Set small progress interval for testing
        scanner._progress_interval = 1
        
        # Capture log output to verify progress reporting
        import logging
        import io
        
        log_capture = io.StringIO()
        handler = logging.StreamHandler(log_capture)
        scanner.logger.addHandler(handler)
        
        scanner.scan_folder(test_files_dir)
        
        log_output = log_capture.getvalue()
        
        # Should have some progress or completion messages
        assert len(log_output) > 0
        
        scanner.conn.close()
    
    def test_final_statistics_report(self, test_files_dir, temp_db):
        """Test final statistics reporting."""
        scanner = FileScanner(temp_db)
        scanner.connect_db()
        
        scanner.scan_folder(test_files_dir)
        
        # Generate statistics report
        report = scanner.get_statistics_report()
        
        assert 'total_files' in report
        assert 'processed_files' in report
        assert 'errors' in report
        assert 'scan_duration' in report
        
        scanner.conn.close()


class TestErrorRecovery:
    """Test error recovery and resilience."""
    
    def test_database_error_recovery(self, test_files_dir, temp_db):
        """Test recovery from database errors."""
        scanner = FileScanner(temp_db)
        scanner.connect_db()
        
        # Simulate database error during scanning
        original_insert = scanner.insert_file
        
        def failing_insert(metadata):
            if 'text_file.txt' in metadata.get('file_name', ''):
                raise sqlite3.Error("Simulated database error")
            return original_insert(metadata)
        
        scanner.insert_file = failing_insert
        
        scanner.scan_folder(test_files_dir)
        
        # Should have errors but continue processing other files
        assert scanner.stats['errors'] > 0
        assert scanner.stats['processed_files'] > 0  # Some files should still be processed
        
        scanner.conn.close()
    
    def test_file_access_error_recovery(self, temp_db):
        """Test recovery from file access errors."""
        # Create a test directory with a file we'll make inaccessible
        test_dir = tempfile.mkdtemp(prefix="access_test_")
        
        try:
            # Create a normal file
            normal_file = os.path.join(test_dir, 'normal.txt')
            with open(normal_file, 'w') as f:
                f.write('Normal file content')
            
            # Create a file and try to make it inaccessible
            restricted_file = os.path.join(test_dir, 'restricted.txt')
            with open(restricted_file, 'w') as f:
                f.write('Restricted content')
            
            # Try to remove read permissions (may not work on all systems)
            try:
                os.chmod(restricted_file, 0o000)
            except OSError:
                pass  # Skip if we can't change permissions
            
            scanner = FileScanner(temp_db)
            scanner.connect_db()
            
            scanner.scan_folder(test_dir)
            
            # Should process at least the normal file
            assert scanner.stats['processed_files'] > 0
            
            scanner.conn.close()
            
        finally:
            # Restore permissions for cleanup
            try:
                os.chmod(restricted_file, 0o644)
            except (OSError, FileNotFoundError):
                pass
            shutil.rmtree(test_dir, ignore_errors=True)
    
    def test_partial_dependency_functionality(self, test_images_dir, temp_db):
        """Test functionality with partial dependencies available."""
        scanner = FileScanner(temp_db)
        scanner.connect_db()
        
        # Mock some dependencies as missing
        original_deps = scanner.__class__.OPTIONAL_DEPENDENCIES.copy()
        
        try:
            # Simulate missing imagehash but available PIL
            scanner.__class__.OPTIONAL_DEPENDENCIES['imagehash'] = None
            
            scanner.scan_folder(test_images_dir)
            
            # Should still process images (get dimensions) but not perceptual hashes
            scanner.cursor.execute("""
                SELECT COUNT(*) FROM files 
                WHERE file_type IN ('.png', '.jpg')
            """)
            image_count = scanner.cursor.fetchone()[0]
            assert image_count > 0
            
            # Check that some images have dimensions but no perceptual hashes
            scanner.cursor.execute("""
                SELECT COUNT(*) FROM files 
                WHERE file_type IN ('.png', '.jpg') 
                AND width IS NOT NULL 
                AND perceptual_hash IS NULL
            """)
            no_hash_count = scanner.cursor.fetchone()[0]
            
            if scanner._is_dependency_available('Image'):
                assert no_hash_count > 0  # Should have dimensions but no hashes
            
        finally:
            # Restore original dependencies
            scanner.__class__.OPTIONAL_DEPENDENCIES = original_deps
        
        scanner.conn.close()


class TestPerformance:
    """Test performance-related aspects."""
    
    def test_large_directory_handling(self, temp_db):
        """Test handling of directories with many files."""
        # Create directory with many small files
        large_dir = tempfile.mkdtemp(prefix="large_test_")
        
        try:
            # Create 100 small files
            for i in range(100):
                file_path = os.path.join(large_dir, f'file_{i:03d}.txt')
                with open(file_path, 'w') as f:
                    f.write(f'Content of file {i}')
            
            scanner = FileScanner(temp_db)
            scanner.connect_db()
            
            scanner.scan_folder(large_dir)
            
            # Should process all files
            assert scanner.stats['total_files'] == 100
            assert scanner.stats['processed_files'] == 100
            
            # Database should have all entries
            scanner.cursor.execute("SELECT COUNT(*) FROM files")
            db_count = scanner.cursor.fetchone()[0]
            assert db_count == 100
            
            scanner.conn.close()
            
        finally:
            shutil.rmtree(large_dir, ignore_errors=True)
    
    def test_memory_usage_stability(self, temp_db):
        """Test that memory usage remains stable during scanning."""
        # This is a basic test - in practice you'd use memory profiling tools
        scanner = FileScanner(temp_db)
        scanner.connect_db()
        
        # Process multiple batches to check for memory leaks
        for batch in range(5):
            batch_dir = tempfile.mkdtemp(prefix=f"batch_{batch}_")
            
            try:
                # Create files for this batch
                for i in range(20):
                    file_path = os.path.join(batch_dir, f'batch_{batch}_file_{i}.txt')
                    with open(file_path, 'w') as f:
                        f.write(f'Batch {batch} file {i} content')
                
                scanner.scan_folder(batch_dir)
                
            finally:
                shutil.rmtree(batch_dir, ignore_errors=True)
        
        # Should have processed all batches successfully
        assert scanner.stats['processed_files'] == 100  # 5 batches * 20 files
        
        scanner.conn.close()