"""
Unit tests for results processing and consolidation system.
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock

from backend.app.core.detection.models import (
    DetectionConfig, DuplicateFile, DuplicateGroup, DetectionMethod
)
from backend.app.core.detection.engine import ResultsProcessor


class TestResultsProcessor:
    """Test ResultsProcessor functionality."""
    
    def setup_method(self):
        """Setup test fixtures."""
        self.processor = ResultsProcessor()
        self.config = DetectionConfig(
            min_confidence_threshold=60.0,
            max_results_per_group=10,
            enable_cross_algorithm_validation=True
        )
    
    def test_consolidate_empty_results(self):
        """Test consolidating empty results."""
        consolidated = self.processor.consolidate_results([], self.config)
        assert consolidated == []
    
    def test_filter_by_confidence_threshold(self):
        """Test filtering groups by confidence threshold."""
        file1 = DuplicateFile(1, "/test/file1.jpg", "file1.jpg", 1024)
        file2 = DuplicateFile(2, "/test/file2.jpg", "file2.jpg", 1024)
        
        high_confidence_group = DuplicateGroup(
            id="high",
            detection_method=DetectionMethod.SHA256,
            confidence_score=80.0,
            similarity_percentage=80.0,
            files=[file1, file2]
        )
        
        low_confidence_group = DuplicateGroup(
            id="low",
            detection_method=DetectionMethod.METADATA,
            confidence_score=50.0,
            similarity_percentage=50.0,
            files=[file1, file2]
        )
        
        groups = [high_confidence_group, low_confidence_group]
        consolidated = self.processor.consolidate_results(groups, self.config)
        
        assert len(consolidated) == 1
        assert consolidated[0].confidence_score == 80.0
    
    def test_merge_overlapping_groups(self):
        """Test merging groups with overlapping files."""
        file1 = DuplicateFile(1, "/test/file1.jpg", "file1.jpg", 1024)
        file2 = DuplicateFile(2, "/test/file2.jpg", "file2.jpg", 1024)
        file3 = DuplicateFile(3, "/test/file3.jpg", "file3.jpg", 1024)
        
        group1 = DuplicateGroup(
            id="group1",
            detection_method=DetectionMethod.SHA256,
            confidence_score=90.0,
            similarity_percentage=90.0,
            files=[file1, file2]
        )
        
        group2 = DuplicateGroup(
            id="group2",
            detection_method=DetectionMethod.PERCEPTUAL_HASH,
            confidence_score=80.0,
            similarity_percentage=80.0,
            files=[file2, file3]  # Overlaps with group1 (file2)
        )
        
        groups = [group1, group2]
        merged = self.processor._merge_overlapping_groups(groups)
        
        assert len(merged) == 1
        merged_group = merged[0]
        
        # Should contain all three files
        assert len(merged_group.files) == 3
        file_ids = {f.file_id for f in merged_group.files}
        assert file_ids == {1, 2, 3}
        
        # Should have merged methods in metadata
        assert 'merged_methods' in merged_group.metadata
        assert DetectionMethod.PERCEPTUAL_HASH.value in merged_group.metadata['merged_methods']
    
    def test_merge_groups_confidence_calculation(self):
        """Test confidence calculation when merging groups."""
        file1 = DuplicateFile(1, "/test/file1.jpg", "file1.jpg", 1024)
        file2 = DuplicateFile(2, "/test/file2.jpg", "file2.jpg", 1024)
        file3 = DuplicateFile(3, "/test/file3.jpg", "file3.jpg", 1024)
        
        target_group = DuplicateGroup(
            id="target",
            detection_method=DetectionMethod.SHA256,
            confidence_score=90.0,
            similarity_percentage=90.0,
            files=[file1, file2]  # 2 files
        )
        
        source_group = DuplicateGroup(
            id="source",
            detection_method=DetectionMethod.PERCEPTUAL_HASH,
            confidence_score=70.0,
            similarity_percentage=70.0,
            files=[file3]  # 1 file
        )
        
        self.processor._merge_groups(target_group, source_group)
        
        # Weighted average: (90*2 + 70*1) / 3 = 83.3
        expected_confidence = (90.0 * 2 + 70.0 * 1) / 3
        assert abs(target_group.confidence_score - expected_confidence) < 0.1
        
        # Should have merge history
        assert 'merge_history' in target_group.metadata
        assert len(target_group.metadata['merge_history']) == 1
    
    def test_rank_groups(self):
        """Test ranking groups by confidence, file count, and size."""
        file1 = DuplicateFile(1, "/test/file1.jpg", "file1.jpg", 1000)
        file2 = DuplicateFile(2, "/test/file2.jpg", "file2.jpg", 1000)
        file3 = DuplicateFile(3, "/test/file3.jpg", "file3.jpg", 2000)
        file4 = DuplicateFile(4, "/test/file4.jpg", "file4.jpg", 2000)
        file5 = DuplicateFile(5, "/test/file5.jpg", "file5.jpg", 3000)
        
        # High confidence, fewer files, smaller total size
        group1 = DuplicateGroup(
            id="group1",
            detection_method=DetectionMethod.SHA256,
            confidence_score=95.0,
            similarity_percentage=95.0,
            files=[file1, file2]  # Total size: 2000
        )
        
        # Lower confidence, more files, larger total size
        group2 = DuplicateGroup(
            id="group2",
            detection_method=DetectionMethod.PERCEPTUAL_HASH,
            confidence_score=85.0,
            similarity_percentage=85.0,
            files=[file3, file4, file5]  # Total size: 7000
        )
        
        groups = [group2, group1]  # Intentionally out of order
        ranked = self.processor._rank_groups(groups)
        
        # group1 should be first (higher confidence)
        assert ranked[0].id == "group1"
        assert ranked[1].id == "group2"
    
    def test_suggest_original_by_timestamp(self):
        """Test original file suggestion based on timestamps."""
        base_time = datetime.now()
        
        # Older file (should be original)
        file1 = DuplicateFile(
            file_id=1,
            file_path="/test/original.jpg",
            file_name="original.jpg",
            file_size=1000,
            created_at=base_time - timedelta(days=1)
        )
        
        # Newer file
        file2 = DuplicateFile(
            file_id=2,
            file_path="/test/copy.jpg",
            file_name="copy.jpg",
            file_size=1000,
            created_at=base_time
        )
        
        group = DuplicateGroup(
            id="test",
            detection_method=DetectionMethod.SHA256,
            confidence_score=100.0,
            similarity_percentage=100.0,
            files=[file1, file2]
        )
        
        self.processor._suggest_original(group)
        
        # Older file should be marked as original
        assert file1.is_original is True
        assert file2.is_original is False
        assert "suggested_original" in file1.detection_reasons
        assert "earliest_timestamp" in file1.detection_reasons
    
    def test_suggest_original_by_size(self):
        """Test original file suggestion based on file size."""
        # Larger file (should be original)
        file1 = DuplicateFile(1, "/test/large.jpg", "large.jpg", 2000)
        # Smaller file
        file2 = DuplicateFile(2, "/test/small.jpg", "small.jpg", 1000)
        
        group = DuplicateGroup(
            id="test",
            detection_method=DetectionMethod.SHA256,
            confidence_score=100.0,
            similarity_percentage=100.0,
            files=[file1, file2]
        )
        
        self.processor._suggest_original(group)
        
        # Larger file should be marked as original
        assert file1.is_original is True
        assert file2.is_original is False
        assert "largest_size" in file1.detection_reasons
    
    def test_suggest_original_by_quality(self):
        """Test original file suggestion based on image quality."""
        # Higher resolution (should be original)
        file1 = DuplicateFile(1, "/test/hires.jpg", "hires.jpg", 1000, width=1920, height=1080)
        # Lower resolution
        file2 = DuplicateFile(2, "/test/lowres.jpg", "lowres.jpg", 1000, width=640, height=480)
        
        group = DuplicateGroup(
            id="test",
            detection_method=DetectionMethod.PERCEPTUAL_HASH,
            confidence_score=90.0,
            similarity_percentage=90.0,
            files=[file1, file2]
        )
        
        self.processor._suggest_original(group)
        
        # Higher resolution file should be marked as original
        assert file1.is_original is True
        assert file2.is_original is False
        assert "best_quality" in file1.detection_reasons
    
    def test_calculate_path_score(self):
        """Test path scoring for original file suggestion."""
        # Good path (root level, short name)
        good_score = self.processor._calculate_path_score("/photos/image.jpg")
        
        # Bad path (backup directory, long name)
        bad_score = self.processor._calculate_path_score("/backup/very/deep/path/very_long_filename_with_lots_of_characters.jpg")
        
        # Temp path (should be penalized)
        temp_score = self.processor._calculate_path_score("/tmp/image.jpg")
        
        assert good_score > bad_score
        assert good_score > temp_score
        assert 0.0 <= good_score <= 1.0
        assert 0.0 <= bad_score <= 1.0
        assert 0.0 <= temp_score <= 1.0
    
    def test_limit_results_per_group(self):
        """Test limiting results per group."""
        # Create a group with many files
        files = [
            DuplicateFile(i, f"/test/file{i}.jpg", f"file{i}.jpg", 1000)
            for i in range(1, 16)  # 15 files
        ]
        
        group = DuplicateGroup(
            id="large_group",
            detection_method=DetectionMethod.SHA256,
            confidence_score=90.0,
            similarity_percentage=90.0,
            files=files
        )
        
        config = DetectionConfig(max_results_per_group=5)
        consolidated = self.processor.consolidate_results([group], config)
        
        assert len(consolidated) == 1
        assert len(consolidated[0].files) == 5  # Limited to 5 files
    
    def test_generate_consolidation_report(self):
        """Test consolidation report generation."""
        file1 = DuplicateFile(1, "/test/file1.jpg", "file1.jpg", 1000)
        file2 = DuplicateFile(2, "/test/file2.jpg", "file2.jpg", 1000)
        file3 = DuplicateFile(3, "/test/file3.jpg", "file3.jpg", 1000)
        
        original_groups = [
            DuplicateGroup("orig1", DetectionMethod.SHA256, 95.0, 95.0, [file1, file2]),
            DuplicateGroup("orig2", DetectionMethod.PERCEPTUAL_HASH, 40.0, 40.0, [file2, file3])  # Low confidence
        ]
        
        consolidated_groups = [
            DuplicateGroup("cons1", DetectionMethod.SHA256, 95.0, 95.0, [file1, file2])
        ]
        
        report = self.processor.generate_consolidation_report(
            original_groups, consolidated_groups, self.config
        )
        
        assert report['summary']['original_groups'] == 2
        assert report['summary']['consolidated_groups'] == 1
        assert report['summary']['groups_filtered'] == 1
        assert report['confidence_distribution']['90-100'] == 1
        assert report['detection_method_distribution']['sha256'] == 1
        assert report['quality_metrics']['avg_confidence'] == 95.0
    
    def test_validate_consolidation_results(self):
        """Test validation of consolidation results."""
        file1 = DuplicateFile(1, "/test/file1.jpg", "file1.jpg", 1000)
        file2 = DuplicateFile(2, "/test/file2.jpg", "file2.jpg", 1000)
        file3 = DuplicateFile(3, "/test/file3.jpg", "file3.jpg", 1000)
        
        # Valid group
        valid_group = DuplicateGroup(
            id="valid",
            detection_method=DetectionMethod.SHA256,
            confidence_score=90.0,
            similarity_percentage=90.0,
            files=[file1, file2]
        )
        
        # Invalid group (single file)
        invalid_group1 = DuplicateGroup(
            id="invalid1",
            detection_method=DetectionMethod.SHA256,
            confidence_score=90.0,
            similarity_percentage=90.0,
            files=[file3]
        )
        
        # Invalid group (bad confidence score)
        invalid_group2 = DuplicateGroup(
            id="invalid2",
            detection_method=DetectionMethod.SHA256,
            confidence_score=150.0,  # Invalid
            similarity_percentage=90.0,
            files=[file1, file2]
        )
        
        groups = [valid_group, invalid_group1, invalid_group2]
        issues = self.processor.validate_consolidation_results(groups)
        
        assert len(issues) >= 2  # Should find at least 2 issues
        assert any("fewer than 2 files" in issue for issue in issues)
        assert any("invalid confidence score" in issue for issue in issues)
    
    def test_validate_duplicate_file_ids(self):
        """Test validation catches duplicate file IDs across groups."""
        file1 = DuplicateFile(1, "/test/file1.jpg", "file1.jpg", 1000)
        file2 = DuplicateFile(2, "/test/file2.jpg", "file2.jpg", 1000)
        file3 = DuplicateFile(1, "/test/file1_copy.jpg", "file1_copy.jpg", 1000)  # Same ID as file1
        
        group1 = DuplicateGroup("group1", DetectionMethod.SHA256, 90.0, 90.0, [file1, file2])
        group2 = DuplicateGroup("group2", DetectionMethod.PERCEPTUAL_HASH, 80.0, 80.0, [file2, file3])
        
        issues = self.processor.validate_consolidation_results([group1, group2])
        
        # Should detect overlapping file IDs
        assert any("appear in multiple groups" in issue for issue in issues)
    
    def test_validate_multiple_originals(self):
        """Test validation catches multiple original files in same group."""
        file1 = DuplicateFile(1, "/test/file1.jpg", "file1.jpg", 1000, is_original=True)
        file2 = DuplicateFile(2, "/test/file2.jpg", "file2.jpg", 1000, is_original=True)  # Also original
        
        group = DuplicateGroup("group", DetectionMethod.SHA256, 90.0, 90.0, [file1, file2])
        
        issues = self.processor.validate_consolidation_results([group])
        
        assert any("multiple files marked as original" in issue for issue in issues)
    
    def test_cross_algorithm_validation_disabled(self):
        """Test consolidation with cross-algorithm validation disabled."""
        file1 = DuplicateFile(1, "/test/file1.jpg", "file1.jpg", 1000)
        file2 = DuplicateFile(2, "/test/file2.jpg", "file2.jpg", 1000)
        
        group1 = DuplicateGroup("group1", DetectionMethod.SHA256, 90.0, 90.0, [file1, file2])
        group2 = DuplicateGroup("group2", DetectionMethod.PERCEPTUAL_HASH, 80.0, 80.0, [file1, file2])
        
        config = DetectionConfig(enable_cross_algorithm_validation=False)
        consolidated = self.processor.consolidate_results([group1, group2], config)
        
        # Should not merge overlapping groups when validation is disabled
        assert len(consolidated) == 2
    
    def test_consolidate_with_original_suggestion(self):
        """Test full consolidation process including original suggestion."""
        base_time = datetime.now()
        
        file1 = DuplicateFile(1, "/test/old.jpg", "old.jpg", 2000, created_at=base_time - timedelta(days=1))
        file2 = DuplicateFile(2, "/test/new.jpg", "new.jpg", 1000, created_at=base_time)
        
        group = DuplicateGroup("test", DetectionMethod.SHA256, 90.0, 90.0, [file1, file2])
        
        consolidated = self.processor.consolidate_results([group], self.config)
        
        assert len(consolidated) == 1
        result_group = consolidated[0]
        
        # Should have suggested an original
        originals = [f for f in result_group.files if f.is_original]
        assert len(originals) == 1
        assert originals[0].file_id == 1  # Older, larger file should be original