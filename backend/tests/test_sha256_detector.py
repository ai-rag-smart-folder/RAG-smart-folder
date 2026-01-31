"""
Unit tests for SHA256 duplicate detector.
"""

import pytest
from datetime import datetime

from backend.app.core.detection.models import DetectionConfig, DuplicateFile, DetectionMethod
from backend.app.core.detection.algorithms.sha256_detector import SHA256Detector


class TestSHA256Detector:
    """Test SHA256Detector functionality."""
    
    def setup_method(self):
        """Setup test fixtures."""
        self.config = DetectionConfig()
        self.detector = SHA256Detector(self.config)
    
    def test_algorithm_name(self):
        """Test algorithm name."""
        assert self.detector.get_algorithm_name() == "SHA256Detector"
    
    def test_supported_file_types(self):
        """Test supported file types (should support all)."""
        supported_types = self.detector.get_supported_file_types()
        assert supported_types == []  # Empty means all types supported
    
    def test_can_process_file_with_hash(self):
        """Test file processing capability with SHA256 hash."""
        file_with_hash = DuplicateFile(
            file_id=1,
            file_path="/test/file.jpg",
            file_name="file.jpg",
            file_size=1024,
            sha256="abc123def456"
        )
        
        assert self.detector.can_process_file(file_with_hash) is True
    
    def test_can_process_file_without_hash(self):
        """Test file processing capability without SHA256 hash."""
        file_without_hash = DuplicateFile(
            file_id=1,
            file_path="/test/file.jpg",
            file_name="file.jpg",
            file_size=1024,
            sha256=None
        )
        
        assert self.detector.can_process_file(file_without_hash) is False
    
    def test_can_process_file_with_empty_hash(self):
        """Test file processing capability with empty SHA256 hash."""
        file_empty_hash = DuplicateFile(
            file_id=1,
            file_path="/test/file.jpg",
            file_name="file.jpg",
            file_size=1024,
            sha256=""
        )
        
        assert self.detector.can_process_file(file_empty_hash) is False
    
    def test_detect_no_files(self):
        """Test detection with no files."""
        groups = self.detector.detect([])
        assert groups == []
    
    def test_detect_single_file(self):
        """Test detection with single file."""
        file1 = DuplicateFile(
            file_id=1,
            file_path="/test/file1.jpg",
            file_name="file1.jpg",
            file_size=1024,
            sha256="abc123"
        )
        
        groups = self.detector.detect([file1])
        assert groups == []  # Single file cannot form a duplicate group
    
    def test_detect_exact_duplicates(self):
        """Test detection of exact duplicates with same SHA256."""
        file1 = DuplicateFile(
            file_id=1,
            file_path="/test/file1.jpg",
            file_name="file1.jpg",
            file_size=1024,
            sha256="abc123def456"
        )
        
        file2 = DuplicateFile(
            file_id=2,
            file_path="/test/copy/file1_copy.jpg",
            file_name="file1_copy.jpg",
            file_size=1024,
            sha256="abc123def456"  # Same hash
        )
        
        groups = self.detector.detect([file1, file2])
        
        assert len(groups) == 1
        group = groups[0]
        
        # Check group properties
        assert group.detection_method == DetectionMethod.SHA256
        assert group.confidence_score == 100.0
        assert group.similarity_percentage == 100.0
        assert len(group.files) == 2
        
        # Check file properties
        for file in group.files:
            assert file.confidence_score == 100.0
            assert "identical_sha256_hash" in file.detection_reasons
        
        # Check metadata
        assert group.metadata['sha256_hash'] == "abc123def456"
        assert group.metadata['file_count'] == 2
        assert group.metadata['detection_algorithm'] == "SHA256Detector"
    
    def test_detect_multiple_duplicate_groups(self):
        """Test detection of multiple separate duplicate groups."""
        # First duplicate group
        file1a = DuplicateFile(1, "/test/file1a.jpg", "file1a.jpg", 1024, sha256="hash1")
        file1b = DuplicateFile(2, "/test/file1b.jpg", "file1b.jpg", 1024, sha256="hash1")
        
        # Second duplicate group
        file2a = DuplicateFile(3, "/test/file2a.jpg", "file2a.jpg", 2048, sha256="hash2")
        file2b = DuplicateFile(4, "/test/file2b.jpg", "file2b.jpg", 2048, sha256="hash2")
        file2c = DuplicateFile(5, "/test/file2c.jpg", "file2c.jpg", 2048, sha256="hash2")
        
        # Unique file (no duplicates)
        file3 = DuplicateFile(6, "/test/file3.jpg", "file3.jpg", 512, sha256="hash3")
        
        files = [file1a, file1b, file2a, file2b, file2c, file3]
        groups = self.detector.detect(files)
        
        assert len(groups) == 2
        
        # Find groups by hash
        group1 = next(g for g in groups if g.metadata['sha256_hash'] == "hash1")
        group2 = next(g for g in groups if g.metadata['sha256_hash'] == "hash2")
        
        assert len(group1.files) == 2
        assert len(group2.files) == 3
        
        # Check total sizes
        assert group1.metadata['total_size'] == 2048  # 2 * 1024
        assert group2.metadata['total_size'] == 6144  # 3 * 2048
    
    def test_detect_files_without_hash(self):
        """Test detection with files that don't have SHA256 hashes."""
        file_with_hash = DuplicateFile(1, "/test/file1.jpg", "file1.jpg", 1024, sha256="abc123")
        file_without_hash = DuplicateFile(2, "/test/file2.jpg", "file2.jpg", 1024, sha256=None)
        file_empty_hash = DuplicateFile(3, "/test/file3.jpg", "file3.jpg", 1024, sha256="")
        
        files = [file_with_hash, file_without_hash, file_empty_hash]
        groups = self.detector.detect(files)
        
        # Should find no groups since no duplicates
        assert groups == []
    
    def test_detect_mixed_files_with_duplicates(self):
        """Test detection with mix of files with and without hashes."""
        # Duplicate pair
        file1 = DuplicateFile(1, "/test/file1.jpg", "file1.jpg", 1024, sha256="duplicate_hash")
        file2 = DuplicateFile(2, "/test/file2.jpg", "file2.jpg", 1024, sha256="duplicate_hash")
        
        # Files without hashes
        file3 = DuplicateFile(3, "/test/file3.jpg", "file3.jpg", 1024, sha256=None)
        file4 = DuplicateFile(4, "/test/file4.jpg", "file4.jpg", 1024, sha256="")
        
        # Unique file
        file5 = DuplicateFile(5, "/test/file5.jpg", "file5.jpg", 1024, sha256="unique_hash")
        
        files = [file1, file2, file3, file4, file5]
        groups = self.detector.detect(files)
        
        assert len(groups) == 1
        group = groups[0]
        assert len(group.files) == 2
        assert group.metadata['sha256_hash'] == "duplicate_hash"
    
    def test_get_statistics_empty(self):
        """Test statistics with no groups."""
        stats = self.detector.get_statistics([])
        
        expected = {
            'total_groups': 0,
            'total_duplicates': 0,
            'total_size_duplicated': 0,
            'largest_group_size': 0,
            'average_group_size': 0.0
        }
        
        assert stats == expected
    
    def test_get_statistics_with_groups(self):
        """Test statistics calculation with duplicate groups."""
        # Create test files and groups
        file1 = DuplicateFile(1, "/test/file1.jpg", "file1.jpg", 1000, sha256="hash1")
        file2 = DuplicateFile(2, "/test/file2.jpg", "file2.jpg", 1000, sha256="hash1")
        
        file3 = DuplicateFile(3, "/test/file3.jpg", "file3.jpg", 2000, sha256="hash2")
        file4 = DuplicateFile(4, "/test/file4.jpg", "file4.jpg", 2000, sha256="hash2")
        file5 = DuplicateFile(5, "/test/file5.jpg", "file5.jpg", 2000, sha256="hash2")
        
        groups = self.detector.detect([file1, file2, file3, file4, file5])
        stats = self.detector.get_statistics(groups)
        
        assert stats['total_groups'] == 2
        assert stats['total_duplicates'] == 5  # 2 + 3 files
        assert stats['total_size_duplicated'] == 8000  # 2*1000 + 3*2000
        assert stats['largest_group_size'] == 3
        assert stats['average_group_size'] == 2.5  # (2 + 3) / 2
        
        # Size savings: total duplicated size minus one file from each group
        expected_savings = 8000 - (1000 + 2000)  # Keep largest from each group
        assert stats['size_savings_potential'] == expected_savings
    
    def test_run_detection_with_performance_tracking(self):
        """Test detection with performance tracking."""
        file1 = DuplicateFile(1, "/test/file1.jpg", "file1.jpg", 1024, sha256="abc123")
        file2 = DuplicateFile(2, "/test/file2.jpg", "file2.jpg", 1024, sha256="abc123")
        
        groups = self.detector.run_detection([file1, file2])
        
        assert len(groups) == 1
        
        # Check performance metrics
        perf = self.detector.get_performance_metrics()
        assert perf.files_processed == 2
        assert perf.groups_found == 1
        assert perf.execution_time_ms > 0
        assert perf.errors_encountered == 0
    
    def test_filter_files_all_supported(self):
        """Test file filtering (SHA256 supports all types with hashes)."""
        file1 = DuplicateFile(1, "/test/file1.jpg", "file1.jpg", 1024, sha256="abc123")
        file2 = DuplicateFile(2, "/test/file2.pdf", "file2.pdf", 2048, sha256="def456")
        file3 = DuplicateFile(3, "/test/file3.txt", "file3.txt", 512, sha256=None)
        
        files = [file1, file2, file3]
        filtered = self.detector.filter_files(files)
        
        # Should include files with hashes, exclude file without hash
        assert len(filtered) == 2
        assert file1 in filtered
        assert file2 in filtered
        assert file3 not in filtered