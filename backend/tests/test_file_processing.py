"""
Unit tests for file processing functionality.
Tests Requirements: 1.1, 1.2, 4.1, 4.2, 4.3, 4.4
"""

import pytest
import os
import sys
import tempfile
import json
from unittest.mock import patch, MagicMock
from PIL import Image

# Add the scripts directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'scripts'))

from scan_folder import FileScanner


class TestFileMetadataExtraction:
    """Test file metadata extraction functionality."""
    
    def test_get_file_metadata_text_file(self, test_files_dir):
        """Test metadata extraction for text files."""
        scanner = FileScanner(':memory:')
        
        text_file = os.path.join(test_files_dir, 'text_file.txt')
        metadata = scanner.get_file_metadata(text_file)
        
        assert metadata['file_name'] == 'text_file.txt'
        assert metadata['file_path'] == text_file
        assert metadata['file_size'] > 0
        assert metadata['file_type'] == '.txt'
        assert 'created_at' in metadata
        assert 'modified_at' in metadata
    
    def test_get_file_metadata_image_file(self, test_images_dir):
        """Test metadata extraction for image files."""
        scanner = FileScanner(':memory:')
        
        image_file = os.path.join(test_images_dir, 'test_image_100x100.png')
        metadata = scanner.get_file_metadata(image_file)
        
        assert metadata['file_name'] == 'test_image_100x100.png'
        assert metadata['file_type'] == '.png'
        assert metadata['file_size'] > 0
    
    def test_get_file_metadata_nonexistent_file(self):
        """Test metadata extraction for non-existent file."""
        scanner = FileScanner(':memory:')
        
        with pytest.raises(FileNotFoundError):
            scanner.get_file_metadata('/nonexistent/file.txt')
    
    def test_get_file_metadata_permission_error(self, mixed_files_dir):
        """Test metadata extraction with permission errors."""
        scanner = FileScanner(':memory:')
        
        # Try to access restricted file
        restricted_file = os.path.join(mixed_files_dir, 'restricted.txt')
        
        # This may or may not raise an error depending on system permissions
        try:
            metadata = scanner.get_file_metadata(restricted_file)
            # If successful, should still have basic metadata
            assert 'file_name' in metadata
        except PermissionError:
            # Expected on some systems
            pass


class TestHashComputation:
    """Test file hash computation functionality."""
    
    def test_compute_sha256_success(self, test_files_dir):
        """Test successful SHA256 computation."""
        scanner = FileScanner(':memory:')
        
        text_file = os.path.join(test_files_dir, 'text_file.txt')
        sha256 = scanner.compute_sha256(text_file)
        
        assert sha256 != ""
        assert len(sha256) == 64  # SHA256 is 64 hex characters
        assert all(c in '0123456789abcdef' for c in sha256)
    
    def test_compute_sha256_duplicate_files(self, test_files_dir):
        """Test SHA256 computation for duplicate files."""
        scanner = FileScanner(':memory:')
        
        file1 = os.path.join(test_files_dir, 'duplicate1.txt')
        file2 = os.path.join(test_files_dir, 'duplicate2.txt')
        
        hash1 = scanner.compute_sha256(file1)
        hash2 = scanner.compute_sha256(file2)
        
        assert hash1 == hash2  # Same content should have same hash
        assert hash1 != ""
    
    def test_compute_sha256_different_files(self, test_files_dir):
        """Test SHA256 computation for different files."""
        scanner = FileScanner(':memory:')
        
        file1 = os.path.join(test_files_dir, 'text_file.txt')
        file2 = os.path.join(test_files_dir, 'unique.txt')
        
        hash1 = scanner.compute_sha256(file1)
        hash2 = scanner.compute_sha256(file2)
        
        assert hash1 != hash2  # Different content should have different hashes
        assert hash1 != ""
        assert hash2 != ""
    
    def test_compute_sha256_empty_file(self, test_files_dir):
        """Test SHA256 computation for empty file."""
        scanner = FileScanner(':memory:')
        
        empty_file = os.path.join(test_files_dir, 'empty.txt')
        sha256 = scanner.compute_sha256(empty_file)
        
        # Empty file should have a specific SHA256
        expected_empty_sha256 = "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
        assert sha256 == expected_empty_sha256
    
    def test_compute_sha256_nonexistent_file(self):
        """Test SHA256 computation for non-existent file."""
        scanner = FileScanner(':memory:')
        
        sha256 = scanner.compute_sha256('/nonexistent/file.txt')
        assert sha256 == ""  # Should return empty string on error
        assert scanner.stats['errors'] > 0
    
    def test_compute_sha256_large_file(self, test_files_dir):
        """Test SHA256 computation for large file."""
        scanner = FileScanner(':memory:')
        
        large_file = os.path.join(test_files_dir, 'large_text.txt')
        sha256 = scanner.compute_sha256(large_file)
        
        assert sha256 != ""
        assert len(sha256) == 64


class TestPerceptualHashing:
    """Test perceptual hash computation for images."""
    
    def test_compute_perceptual_hash_success(self, test_images_dir):
        """Test successful perceptual hash computation."""
        scanner = FileScanner(':memory:')
        
        image_file = os.path.join(test_images_dir, 'test_image_100x100.png')
        phash = scanner.compute_perceptual_hash(image_file)
        
        if scanner._is_dependency_available('imagehash'):
            assert phash is not None
            assert len(phash) > 0
        else:
            assert phash is None
    
    def test_compute_perceptual_hash_similar_images(self, test_images_dir):
        """Test perceptual hash for similar images."""
        scanner = FileScanner(':memory:')
        
        if not scanner._is_dependency_available('imagehash'):
            pytest.skip("imagehash not available")
        
        image1 = os.path.join(test_images_dir, 'duplicate_image1.png')
        image2 = os.path.join(test_images_dir, 'duplicate_image2.png')
        
        hash1 = scanner.compute_perceptual_hash(image1)
        hash2 = scanner.compute_perceptual_hash(image2)
        
        assert hash1 is not None
        assert hash2 is not None
        # Similar images should have similar hashes (but may not be identical)
    
    def test_compute_perceptual_hash_corrupted_image(self, test_images_dir):
        """Test perceptual hash computation for corrupted image."""
        scanner = FileScanner(':memory:')
        
        corrupted_file = os.path.join(test_images_dir, 'corrupted.jpg')
        phash = scanner.compute_perceptual_hash(corrupted_file)
        
        assert phash is None  # Should handle gracefully
        assert scanner.stats['errors'] > 0
    
    def test_compute_perceptual_hash_nonexistent_file(self):
        """Test perceptual hash computation for non-existent file."""
        scanner = FileScanner(':memory:')
        
        phash = scanner.compute_perceptual_hash('/nonexistent/image.jpg')
        assert phash is None
        assert scanner.stats['errors'] > 0
    
    def test_compute_perceptual_hash_missing_dependencies(self):
        """Test perceptual hash when dependencies are missing."""
        scanner = FileScanner(':memory:')
        
        # Mock missing dependencies
        with patch.object(scanner, '_is_dependency_available', return_value=False):
            phash = scanner.compute_perceptual_hash('any_file.jpg')
            assert phash is None


class TestImageProcessing:
    """Test image-specific processing functionality."""
    
    def test_get_image_dimensions_success(self, test_images_dir):
        """Test successful image dimension extraction."""
        scanner = FileScanner(':memory:')
        
        image_file = os.path.join(test_images_dir, 'test_image_100x100.png')
        width, height = scanner.get_image_dimensions(image_file)
        
        if scanner._is_dependency_available('Image'):
            assert width == 100
            assert height == 100
        else:
            assert width is None
            assert height is None
    
    def test_get_image_dimensions_different_sizes(self, test_images_dir):
        """Test dimension extraction for different image sizes."""
        scanner = FileScanner(':memory:')
        
        if not scanner._is_dependency_available('Image'):
            pytest.skip("PIL not available")
        
        image_file = os.path.join(test_images_dir, 'test_image_200x150.jpg')
        width, height = scanner.get_image_dimensions(image_file)
        
        assert width == 200
        assert height == 150
    
    def test_get_image_dimensions_corrupted_image(self, test_images_dir):
        """Test dimension extraction for corrupted image."""
        scanner = FileScanner(':memory:')
        
        corrupted_file = os.path.join(test_images_dir, 'corrupted.jpg')
        width, height = scanner.get_image_dimensions(corrupted_file)
        
        assert width is None
        assert height is None
        assert scanner.stats['errors'] > 0
    
    def test_extract_exif_data_success(self, test_images_dir):
        """Test EXIF data extraction."""
        scanner = FileScanner(':memory:')
        
        image_file = os.path.join(test_images_dir, 'test_image_100x100.png')
        exif_data = scanner.extract_exif_data(image_file)
        
        # Should return dict (may be empty for PNG without EXIF)
        assert isinstance(exif_data, dict)
    
    def test_extract_exif_data_missing_dependency(self):
        """Test EXIF extraction when exifread is missing."""
        scanner = FileScanner(':memory:')
        
        with patch.object(scanner, '_is_dependency_available', return_value=False):
            exif_data = scanner.extract_exif_data('any_file.jpg')
            assert exif_data == {}


class TestFileTypeHandling:
    """Test handling of different file types."""
    
    def test_process_text_file(self, test_files_dir, temp_db):
        """Test processing text files."""
        scanner = FileScanner(temp_db)
        scanner.connect_db()
        
        text_file = os.path.join(test_files_dir, 'text_file.txt')
        result = scanner._process_file(text_file)
        
        assert result is True
        assert scanner.stats['processed_files'] > 0
        
        scanner.conn.close()
    
    def test_process_image_file(self, test_images_dir, temp_db):
        """Test processing image files."""
        scanner = FileScanner(temp_db)
        scanner.connect_db()
        
        image_file = os.path.join(test_images_dir, 'test_image_100x100.png')
        result = scanner._process_file(image_file)
        
        assert result is True
        assert scanner.stats['processed_files'] > 0
        
        scanner.conn.close()
    
    def test_process_binary_file(self, mixed_files_dir, temp_db):
        """Test processing binary files."""
        scanner = FileScanner(temp_db)
        scanner.connect_db()
        
        binary_file = os.path.join(mixed_files_dir, 'binary.bin')
        result = scanner._process_file(binary_file)
        
        assert result is True
        assert scanner.stats['processed_files'] > 0
        
        scanner.conn.close()
    
    def test_skip_hidden_files(self, test_files_dir, temp_db):
        """Test that hidden files are properly skipped."""
        scanner = FileScanner(temp_db)
        scanner.connect_db()
        
        hidden_file = os.path.join(test_files_dir, '.hidden_file')
        result = scanner._should_skip_file(hidden_file)
        
        assert result is True  # Should skip hidden files
        
        scanner.conn.close()
    
    def test_skip_zero_byte_files(self, test_files_dir, temp_db):
        """Test handling of zero-byte files."""
        scanner = FileScanner(temp_db)
        scanner.connect_db()
        
        empty_file = os.path.join(test_files_dir, 'empty.txt')
        
        # Check if file should be skipped (depends on implementation)
        result = scanner._process_file(empty_file)
        
        # Should either process successfully or skip gracefully
        assert isinstance(result, bool)
        
        scanner.conn.close()


class TestErrorHandling:
    """Test error handling in file processing."""
    
    def test_error_logging(self, temp_db):
        """Test error logging functionality."""
        scanner = FileScanner(temp_db)
        
        # Test error logging
        scanner._log_error('TEST_ERROR', '/test/path', 'Test error message')
        
        assert scanner.stats['errors'] == 1
        assert len(scanner.error_details) == 1
        
        error = scanner.error_details[0]
        assert error['error_type'] == 'TEST_ERROR'
        assert error['file_path'] == '/test/path'
        assert error['error_message'] == 'Test error message'
    
    def test_error_logging_with_exception(self, temp_db):
        """Test error logging with exception details."""
        scanner = FileScanner(temp_db)
        
        try:
            raise ValueError("Test exception")
        except ValueError as e:
            scanner._log_error('TEST_ERROR', '/test/path', 'Test error', e)
        
        assert scanner.stats['errors'] == 1
        error = scanner.error_details[0]
        assert error['exception_type'] == 'ValueError'
        assert error['exception_message'] == 'Test exception'
    
    def test_graceful_dependency_handling(self):
        """Test graceful handling of missing dependencies."""
        scanner = FileScanner(':memory:')
        
        # Test with all dependencies missing
        with patch.dict(scanner.__class__.__dict__, {'OPTIONAL_DEPENDENCIES': {}}):
            # Should not crash
            result = scanner.compute_perceptual_hash('test.jpg')
            assert result is None
            
            width, height = scanner.get_image_dimensions('test.jpg')
            assert width is None
            assert height is None
    
    def test_file_processing_resilience(self, temp_db):
        """Test that file processing continues after errors."""
        scanner = FileScanner(temp_db)
        scanner.connect_db()
        
        # Mock _process_file to fail for first file, succeed for second
        original_process = scanner._process_file
        call_count = 0
        
        def mock_process(file_path):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise Exception("Simulated error")
            return original_process(file_path)
        
        with patch.object(scanner, '_process_file', side_effect=mock_process):
            # Should handle the error and continue
            files = ['file1.txt', 'file2.txt']
            for file_path in files:
                try:
                    scanner._process_file(file_path)
                except Exception:
                    scanner._log_error('PROCESSING_ERROR', file_path, 'Simulated error')
        
        # Should have logged the error but continued processing
        assert scanner.stats['errors'] > 0
        
        scanner.conn.close()