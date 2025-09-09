"""
Unit tests for metadata-based duplicate detector.
"""

import pytest
from datetime import datetime, timedelta

from backend.app.core.detection.models import DetectionConfig, DuplicateFile, DetectionMethod
from backend.app.core.detection.algorithms.metadata_detector import MetadataDetector


class TestMetadataDetector:
    """Test MetadataDetector functionality."""
    
    def setup_method(self):
        """Setup test fixtures."""
        self.config = DetectionConfig(
            metadata_fields=['file_size', 'modified_at', 'width', 'height'],
            size_tolerance=100,  # 100 bytes tolerance
            time_tolerance=60    # 60 seconds tolerance
        )
        self.detector = MetadataDetector(self.config)
    
    def test_algorithm_name(self):
        """Test algorithm name."""
        assert self.detector.get_algorithm_name() == "MetadataDetector"
    
    def test_supported_file_types(self):
        """Test supported file types (should support all)."""
        supported_types = self.detector.get_supported_file_types()
        assert supported_types == []  # Empty means all types supported
    
    def test_can_process_file_with_metadata(self):
        """Test file processing capability with metadata."""
        file_with_metadata = DuplicateFile(
            file_id=1,
            file_path="/test/file.jpg",
            file_name="file.jpg",
            file_size=1024,
            modified_at=datetime.now()
        )
        
        assert self.detector.can_process_file(file_with_metadata) is True
    
    def test_can_process_file_without_metadata(self):
        """Test file processing capability without relevant metadata."""
        file_without_metadata = DuplicateFile(
            file_id=1,
            file_path="/test/file.jpg",
            file_name="file.jpg",
            file_size=None,
            modified_at=None,
            width=None,
            height=None
        )
        
        assert self.detector.can_process_file(file_without_metadata) is False
    
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
            file_size=1024
        )
        
        groups = self.detector.detect([file1])
        assert groups == []
    
    def test_compare_sizes_within_tolerance(self):
        """Test size comparison within tolerance."""
        assert self.detector._compare_sizes(1000, 1050) is True  # 50 bytes diff
        assert self.detector._compare_sizes(1000, 1100) is True  # 100 bytes diff (at limit)
        assert self.detector._compare_sizes(1000, 1150) is False  # 150 bytes diff (over limit)
    
    def test_compare_sizes_with_none(self):
        """Test size comparison with None values."""
        assert self.detector._compare_sizes(None, 1000) is False
        assert self.detector._compare_sizes(1000, None) is False
        assert self.detector._compare_sizes(None, None) is False
    
    def test_compare_timestamps_within_tolerance(self):
        """Test timestamp comparison within tolerance."""
        base_time = datetime.now()
        time1 = base_time
        time2 = base_time + timedelta(seconds=30)  # 30 seconds diff
        time3 = base_time + timedelta(seconds=60)  # 60 seconds diff (at limit)
        time4 = base_time + timedelta(seconds=90)  # 90 seconds diff (over limit)
        
        assert self.detector._compare_timestamps(time1, time2) is True
        assert self.detector._compare_timestamps(time1, time3) is True
        assert self.detector._compare_timestamps(time1, time4) is False
    
    def test_compare_timestamps_with_strings(self):
        """Test timestamp comparison with string inputs."""
        time_str1 = "2023-01-01T12:00:00"
        time_str2 = "2023-01-01T12:00:30"  # 30 seconds later
        
        assert self.detector._compare_timestamps(time_str1, time_str2) is True
    
    def test_compare_dimensions_exact_match(self):
        """Test dimension comparison (exact match required)."""
        assert self.detector._compare_dimensions(1920, 1920) is True
        assert self.detector._compare_dimensions(1920, 1080) is False
        assert self.detector._compare_dimensions(None, 1920) is False
        assert self.detector._compare_dimensions(1920, None) is False
    
    def test_detect_files_with_similar_sizes(self):
        """Test detection of files with similar sizes."""
        file1 = DuplicateFile(1, "/test/file1.jpg", "file1.jpg", 1000)
        file2 = DuplicateFile(2, "/test/file2.jpg", "file2.jpg", 1050)  # Within tolerance
        file3 = DuplicateFile(3, "/test/file3.jpg", "file3.jpg", 2000)  # Different size
        
        groups = self.detector.detect([file1, file2, file3])
        
        assert len(groups) == 1
        group = groups[0]
        
        assert group.detection_method == DetectionMethod.METADATA
        assert len(group.files) == 2
        assert group.files[0].file_id in [1, 2]
        assert group.files[1].file_id in [1, 2]
        
        # Check detection reasons
        for file in group.files:
            assert "similar_metadata" in file.detection_reasons
            assert "matching_file_size" in file.detection_reasons
    
    def test_detect_files_with_similar_timestamps(self):
        """Test detection of files with similar timestamps."""
        base_time = datetime.now()
        
        file1 = DuplicateFile(1, "/test/file1.jpg", "file1.jpg", 1000, modified_at=base_time)
        file2 = DuplicateFile(2, "/test/file2.jpg", "file2.jpg", 2000, 
                             modified_at=base_time + timedelta(seconds=30))
        file3 = DuplicateFile(3, "/test/file3.jpg", "file3.jpg", 3000,
                             modified_at=base_time + timedelta(minutes=10))  # Too far apart
        
        groups = self.detector.detect([file1, file2, file3])
        
        assert len(groups) == 1
        group = groups[0]
        assert len(group.files) == 2
        
        # Check detection reasons
        for file in group.files:
            assert "similar_metadata" in file.detection_reasons
            assert "matching_modified_at" in file.detection_reasons
    
    def test_detect_files_with_multiple_matching_fields(self):
        """Test detection of files with multiple matching metadata fields."""
        base_time = datetime.now()
        
        file1 = DuplicateFile(
            file_id=1,
            file_path="/test/file1.jpg",
            file_name="file1.jpg",
            file_size=1000,
            modified_at=base_time,
            width=1920,
            height=1080
        )
        
        file2 = DuplicateFile(
            file_id=2,
            file_path="/test/file2.jpg",
            file_name="file2.jpg",
            file_size=1050,  # Similar size
            modified_at=base_time + timedelta(seconds=30),  # Similar time
            width=1920,  # Same width
            height=1080  # Same height
        )
        
        groups = self.detector.detect([file1, file2])
        
        assert len(groups) == 1
        group = groups[0]
        
        # Should have high confidence due to multiple matching fields
        assert group.confidence_score > 70.0
        
        # Check that multiple fields are detected as matching
        file = group.files[0]
        reasons = file.detection_reasons
        assert "matching_file_size" in reasons
        assert "matching_modified_at" in reasons
        assert "matching_width" in reasons
        assert "matching_height" in reasons
    
    def test_calculate_pairwise_similarity(self):
        """Test pairwise similarity calculation."""
        file1 = DuplicateFile(1, "/test/file1.jpg", "file1.jpg", 1000, width=1920, height=1080)
        file2 = DuplicateFile(2, "/test/file2.jpg", "file2.jpg", 1000, width=1920, height=1080)
        file3 = DuplicateFile(3, "/test/file3.jpg", "file3.jpg", 2000, width=1280, height=720)
        
        # Files 1 and 2 should be very similar (3/3 fields match)
        similarity_12 = self.detector._calculate_pairwise_similarity(file1, file2)
        assert similarity_12 == 100.0
        
        # Files 1 and 3 should be less similar (1/3 fields match)
        similarity_13 = self.detector._calculate_pairwise_similarity(file1, file3)
        assert similarity_13 < 50.0
    
    def test_get_matching_fields(self):
        """Test getting matching fields between files."""
        file1 = DuplicateFile(1, "/test/file1.jpg", "file1.jpg", 1000, width=1920)
        file2 = DuplicateFile(2, "/test/file2.jpg", "file2.jpg", 1000, width=1920, height=1080)
        
        matching_fields = self.detector._get_matching_fields(file1, file2)
        
        assert "file_size" in matching_fields
        assert "width" in matching_fields
        assert "height" not in matching_fields  # file1 doesn't have height
        assert "modified_at" not in matching_fields  # Neither has modified_at
    
    def test_analyze_group_metadata(self):
        """Test metadata analysis for a group."""
        files = [
            DuplicateFile(1, "/test/file1.jpg", "file1.jpg", 1000, width=1920),
            DuplicateFile(2, "/test/file2.jpg", "file2.jpg", 1000, width=1920),
            DuplicateFile(3, "/test/file3.jpg", "file3.jpg", 1050, width=1920)
        ]
        
        analysis = self.detector._analyze_group_metadata(files)
        
        assert 'field_statistics' in analysis
        assert 'common_patterns' in analysis
        assert 'anomalies' in analysis
        
        # Check file_size statistics
        size_stats = analysis['field_statistics']['file_size']
        assert size_stats['total_files_with_field'] == 3
        assert size_stats['unique_values'] == 2  # 1000 and 1050
        
        # Check width statistics
        width_stats = analysis['field_statistics']['width']
        assert width_stats['total_files_with_field'] == 3
        assert width_stats['unique_values'] == 1  # All have 1920
        
        # Should identify common pattern for width
        assert any("identical width" in pattern for pattern in analysis['common_patterns'])
    
    def test_calculate_group_confidence(self):
        """Test group confidence calculation."""
        # High similarity group
        high_sim_files = [
            DuplicateFile(1, "/test/file1.jpg", "file1.jpg", 1000, width=1920, height=1080),
            DuplicateFile(2, "/test/file2.jpg", "file2.jpg", 1000, width=1920, height=1080)
        ]
        
        high_confidence = self.detector._calculate_group_confidence(high_sim_files)
        
        # Low similarity group
        low_sim_files = [
            DuplicateFile(1, "/test/file1.jpg", "file1.jpg", 1000),
            DuplicateFile(2, "/test/file2.jpg", "file2.jpg", 2000)
        ]
        
        low_confidence = self.detector._calculate_group_confidence(low_sim_files)
        
        assert high_confidence > low_confidence
        assert high_confidence > 80.0
        assert low_confidence < 60.0
    
    def test_get_metadata_comparison_report(self):
        """Test metadata comparison report generation."""
        files = [
            DuplicateFile(1, "/test/file1.jpg", "file1.jpg", 1000, width=1920),
            DuplicateFile(2, "/test/file2.jpg", "file2.jpg", 1000, width=1920),
            DuplicateFile(3, "/test/file3.jpg", "file3.jpg", None, height=1080)  # Missing size
        ]
        
        report = self.detector.get_metadata_comparison_report(files)
        
        assert report['total_files'] == 3
        assert report['processable_files'] == 3  # All have some metadata
        
        # Check field coverage
        assert 'field_coverage' in report
        size_coverage = report['field_coverage']['file_size']
        assert size_coverage['files_with_field'] == 2  # Only files 1 and 2 have size
        assert size_coverage['coverage_percentage'] == 200/3  # 2/3 * 100
        
        # Check potential groups
        assert 'potential_groups' in report
        assert len(report['potential_groups']) >= 1  # Should find at least one group
    
    def test_are_metadata_similar_majority_match(self):
        """Test metadata similarity with majority field matching."""
        # 3 out of 4 fields match (75% > 50% threshold)
        file1 = DuplicateFile(1, "/test/file1.jpg", "file1.jpg", 1000, 
                             modified_at=datetime.now(), width=1920, height=1080)
        file2 = DuplicateFile(2, "/test/file2.jpg", "file2.jpg", 1000,
                             modified_at=datetime.now(), width=1920, height=720)  # Different height
        
        assert self.detector._are_metadata_similar(file1, file2) is True
    
    def test_are_metadata_similar_minority_match(self):
        """Test metadata similarity with minority field matching."""
        # Only 1 out of 3 fields match (33% < 50% threshold)
        file1 = DuplicateFile(1, "/test/file1.jpg", "file1.jpg", 1000, width=1920, height=1080)
        file2 = DuplicateFile(2, "/test/file2.jpg", "file2.jpg", 2000, width=1280, height=720)
        
        assert self.detector._are_metadata_similar(file1, file2) is False
    
    def test_create_metadata_group(self):
        """Test creating metadata group."""
        files = [
            DuplicateFile(1, "/test/file1.jpg", "file1.jpg", 1000),
            DuplicateFile(2, "/test/file2.jpg", "file2.jpg", 1000)
        ]
        
        group = self.detector._create_metadata_group(files)
        
        assert group.detection_method == DetectionMethod.METADATA
        assert len(group.files) == 2
        assert group.metadata['recommendation'] == 'verify_content'
        assert group.metadata['detection_algorithm'] == 'MetadataDetector'
        
        # Check that files have appropriate detection reasons
        for file in group.files:
            assert file.confidence_score > 0
            assert "similar_metadata" in file.detection_reasons
    
    def test_filter_files_by_processability(self):
        """Test filtering files by processing capability."""
        files = [
            DuplicateFile(1, "/test/file1.jpg", "file1.jpg", 1000),  # Has size
            DuplicateFile(2, "/test/file2.jpg", "file2.jpg", None),  # No metadata
            DuplicateFile(3, "/test/file3.jpg", "file3.jpg", None, width=1920)  # Has width
        ]
        
        processable = [f for f in files if self.detector.can_process_file(f)]
        
        assert len(processable) == 2  # Files 1 and 3
        assert processable[0].file_id in [1, 3]
        assert processable[1].file_id in [1, 3]
    
    def test_group_matching_fields_analysis(self):
        """Test analysis of fields that match across entire group."""
        files = [
            DuplicateFile(1, "/test/file1.jpg", "file1.jpg", 1000, width=1920, height=1080),
            DuplicateFile(2, "/test/file2.jpg", "file2.jpg", 1000, width=1920, height=1080),
            DuplicateFile(3, "/test/file3.jpg", "file3.jpg", 1050, width=1920, height=1080)  # Different size
        ]
        
        matching_fields = self.detector._get_group_matching_fields(files)
        
        # Width and height should match across all files
        assert "width" in matching_fields
        assert "height" in matching_fields
        # File size should not match (1000, 1000, 1050 - not all similar)
        assert "file_size" not in matching_fields