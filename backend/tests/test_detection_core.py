"""
Unit tests for core detection engine components.
"""

import pytest
from datetime import datetime
from unittest.mock import Mock, patch
import uuid

from backend.app.core.detection.models import (
    DetectionConfig, DuplicateFile, DuplicateGroup, DetectionResults,
    DetectionMode, DetectionMethod, AlgorithmPerformance
)
from backend.app.core.detection.algorithms import DetectionAlgorithm, AlgorithmRegistry
from backend.app.core.detection.config import ConfigManager
from backend.app.core.detection.engine import DuplicateDetectionEngine, ResultsProcessor


class TestDetectionConfig:
    """Test DetectionConfig validation and functionality."""
    
    def test_default_config_is_valid(self):
        """Test that default configuration is valid."""
        config = DetectionConfig()
        errors = config.validate()
        assert errors == []
    
    def test_invalid_perceptual_threshold(self):
        """Test validation of perceptual threshold."""
        config = DetectionConfig(perceptual_threshold=150.0)
        errors = config.validate()
        assert any("perceptual_threshold" in error for error in errors)
    
    def test_invalid_hash_size(self):
        """Test validation of perceptual hash size."""
        config = DetectionConfig(perceptual_hash_size=12)
        errors = config.validate()
        assert any("perceptual_hash_size" in error for error in errors)
    
    def test_invalid_feature_weights(self):
        """Test validation of feature weights."""
        config = DetectionConfig(
            feature_weight_perceptual=0.5,
            feature_weight_color=0.3,
            feature_weight_edge=0.3  # Sum > 1.0
        )
        errors = config.validate()
        assert any("feature weights" in error for error in errors)
    
    def test_negative_tolerances(self):
        """Test validation of negative tolerance values."""
        config = DetectionConfig(size_tolerance=-100, time_tolerance=-60)
        errors = config.validate()
        assert len(errors) >= 2


class TestDuplicateFile:
    """Test DuplicateFile model."""
    
    def test_create_duplicate_file(self):
        """Test creating a DuplicateFile instance."""
        file = DuplicateFile(
            file_id=1,
            file_path="/test/file.jpg",
            file_name="file.jpg",
            file_size=1024,
            sha256="abc123",
            confidence_score=95.0
        )
        
        assert file.file_id == 1
        assert file.file_path == "/test/file.jpg"
        assert file.confidence_score == 95.0
        assert file.detection_reasons == []


class TestDuplicateGroup:
    """Test DuplicateGroup model."""
    
    def test_create_duplicate_group(self):
        """Test creating a DuplicateGroup with files."""
        file1 = DuplicateFile(1, "/test/file1.jpg", "file1.jpg", 1024)
        file2 = DuplicateFile(2, "/test/file2.jpg", "file2.jpg", 1024)
        
        group = DuplicateGroup(
            id="group1",
            detection_method=DetectionMethod.SHA256,
            confidence_score=100.0,
            similarity_percentage=100.0,
            files=[file1, file2]
        )
        
        assert group.file_count == 2
        assert group.total_size == 2048
    
    def test_empty_group_raises_error(self):
        """Test that empty group raises ValueError."""
        with pytest.raises(ValueError, match="must contain at least one file"):
            DuplicateGroup(
                id="group1",
                detection_method=DetectionMethod.SHA256,
                confidence_score=100.0,
                similarity_percentage=100.0,
                files=[]
            )
    
    def test_single_file_group_raises_error(self):
        """Test that single file group raises ValueError."""
        file1 = DuplicateFile(1, "/test/file1.jpg", "file1.jpg", 1024)
        
        with pytest.raises(ValueError, match="must contain at least two files"):
            DuplicateGroup(
                id="group1",
                detection_method=DetectionMethod.SHA256,
                confidence_score=100.0,
                similarity_percentage=100.0,
                files=[file1]
            )
    
    def test_suggested_original(self):
        """Test suggested original file functionality."""
        file1 = DuplicateFile(1, "/test/file1.jpg", "file1.jpg", 1024, is_original=True)
        file2 = DuplicateFile(2, "/test/file2.jpg", "file2.jpg", 1024)
        
        group = DuplicateGroup(
            id="group1",
            detection_method=DetectionMethod.SHA256,
            confidence_score=100.0,
            similarity_percentage=100.0,
            files=[file1, file2]
        )
        
        assert group.suggested_original == file1


class TestDetectionResults:
    """Test DetectionResults model."""
    
    def test_success_rate_calculation(self):
        """Test success rate calculation."""
        results = DetectionResults(
            session_id="test",
            detection_mode=DetectionMode.EXACT,
            groups=[],
            total_files_scanned=100,
            total_groups_found=0,
            total_duplicates_found=0,
            detection_time_ms=1000,
            config=DetectionConfig(),
            errors=["error1", "error2"]  # 2 errors out of 100 files
        )
        
        assert results.success_rate == 98.0
    
    def test_duplicate_percentage_calculation(self):
        """Test duplicate percentage calculation."""
        results = DetectionResults(
            session_id="test",
            detection_mode=DetectionMode.EXACT,
            groups=[],
            total_files_scanned=100,
            total_groups_found=5,
            total_duplicates_found=20,
            detection_time_ms=1000,
            config=DetectionConfig()
        )
        
        assert results.duplicate_percentage == 20.0


class MockDetectionAlgorithm(DetectionAlgorithm):
    """Mock algorithm for testing."""
    
    def detect(self, files):
        # Create a simple duplicate group for testing
        if len(files) >= 2:
            return [DuplicateGroup(
                id="mock_group",
                detection_method=DetectionMethod.SHA256,
                confidence_score=100.0,
                similarity_percentage=100.0,
                files=files[:2]
            )]
        return []
    
    def get_algorithm_name(self):
        return "MockAlgorithm"
    
    def get_supported_file_types(self):
        return [".jpg", ".png"]


class TestAlgorithmRegistry:
    """Test AlgorithmRegistry functionality."""
    
    def test_register_algorithm(self):
        """Test registering an algorithm."""
        registry = AlgorithmRegistry()
        registry.register(MockDetectionAlgorithm)
        
        assert "MockDetectionAlgorithm" in registry.list_algorithms()
    
    def test_get_algorithm(self):
        """Test getting an algorithm instance."""
        registry = AlgorithmRegistry()
        registry.register(MockDetectionAlgorithm)
        
        config = DetectionConfig()
        algorithm = registry.get_algorithm("MockDetectionAlgorithm", config)
        
        assert algorithm is not None
        assert isinstance(algorithm, MockDetectionAlgorithm)
    
    def test_get_nonexistent_algorithm(self):
        """Test getting a non-existent algorithm."""
        registry = AlgorithmRegistry()
        config = DetectionConfig()
        algorithm = registry.get_algorithm("NonExistent", config)
        
        assert algorithm is None


class TestConfigManager:
    """Test ConfigManager functionality."""
    
    def test_load_default_config(self):
        """Test loading default configuration."""
        manager = ConfigManager()
        config = manager.load_config()
        
        assert isinstance(config, DetectionConfig)
        assert config.perceptual_threshold == 80.0
    
    def test_load_config_from_dict(self):
        """Test loading configuration from dictionary."""
        manager = ConfigManager()
        config_data = {
            "perceptual_threshold": 90.0,
            "min_confidence_threshold": 70.0
        }
        
        config = manager.load_config(config_data)
        
        assert config.perceptual_threshold == 90.0
        assert config.min_confidence_threshold == 70.0
    
    def test_get_config_for_mode(self):
        """Test getting optimized config for detection modes."""
        manager = ConfigManager()
        
        exact_config = manager.get_config_for_mode(DetectionMode.EXACT)
        assert exact_config.min_confidence_threshold == 100.0
        
        similar_config = manager.get_config_for_mode(DetectionMode.SIMILAR)
        assert similar_config.perceptual_threshold == 80.0
        assert similar_config.use_color_histogram is True


class TestResultsProcessor:
    """Test ResultsProcessor functionality."""
    
    def test_consolidate_empty_results(self):
        """Test consolidating empty results."""
        processor = ResultsProcessor()
        config = DetectionConfig()
        
        consolidated = processor.consolidate_results([], config)
        assert consolidated == []
    
    def test_filter_by_confidence_threshold(self):
        """Test filtering groups by confidence threshold."""
        processor = ResultsProcessor()
        config = DetectionConfig(min_confidence_threshold=80.0)
        
        file1 = DuplicateFile(1, "/test/file1.jpg", "file1.jpg", 1024)
        file2 = DuplicateFile(2, "/test/file2.jpg", "file2.jpg", 1024)
        
        high_confidence_group = DuplicateGroup(
            id="high",
            detection_method=DetectionMethod.SHA256,
            confidence_score=90.0,
            similarity_percentage=90.0,
            files=[file1, file2]
        )
        
        low_confidence_group = DuplicateGroup(
            id="low",
            detection_method=DetectionMethod.PERCEPTUAL_HASH,
            confidence_score=70.0,
            similarity_percentage=70.0,
            files=[file1, file2]
        )
        
        groups = [high_confidence_group, low_confidence_group]
        consolidated = processor.consolidate_results(groups, config)
        
        assert len(consolidated) == 1
        assert consolidated[0].confidence_score == 90.0
    
    def test_suggest_original_by_size(self):
        """Test original file suggestion based on file size."""
        processor = ResultsProcessor()
        
        small_file = DuplicateFile(1, "/test/small.jpg", "small.jpg", 1024)
        large_file = DuplicateFile(2, "/test/large.jpg", "large.jpg", 2048)
        
        group = DuplicateGroup(
            id="test",
            detection_method=DetectionMethod.SHA256,
            confidence_score=100.0,
            similarity_percentage=100.0,
            files=[small_file, large_file]
        )
        
        processor._suggest_original(group)
        
        # Larger file should be suggested as original
        assert large_file.is_original is True
        assert small_file.is_original is False


class TestDuplicateDetectionEngine:
    """Test DuplicateDetectionEngine functionality."""
    
    def test_add_algorithm(self):
        """Test adding algorithm to engine."""
        engine = DuplicateDetectionEngine()
        algorithm = MockDetectionAlgorithm(DetectionConfig())
        
        engine.add_algorithm(algorithm)
        
        assert len(engine.algorithms) == 1
        assert engine.algorithms[0] == algorithm
    
    @patch('backend.app.core.detection.engine.algorithm_registry')
    def test_detect_duplicates_with_mock_algorithm(self, mock_registry):
        """Test duplicate detection with mock algorithm."""
        # Setup mock registry
        mock_algorithm = MockDetectionAlgorithm(DetectionConfig())
        mock_registry.get_all_algorithms.return_value = [mock_algorithm]
        
        engine = DuplicateDetectionEngine()
        
        file1 = DuplicateFile(1, "/test/file1.jpg", "file1.jpg", 1024)
        file2 = DuplicateFile(2, "/test/file2.jpg", "file2.jpg", 1024)
        files = [file1, file2]
        
        results = engine.detect_duplicates(files, DetectionMode.EXACT)
        
        assert results.total_files_scanned == 2
        assert results.total_groups_found == 1
        assert results.detection_mode == DetectionMode.EXACT
        assert len(results.groups) == 1
    
    def test_get_detection_report(self):
        """Test generating detection report."""
        engine = DuplicateDetectionEngine()
        
        file1 = DuplicateFile(1, "/test/file1.jpg", "file1.jpg", 1024)
        file2 = DuplicateFile(2, "/test/file2.jpg", "file2.jpg", 1024)
        
        group = DuplicateGroup(
            id="test_group",
            detection_method=DetectionMethod.SHA256,
            confidence_score=100.0,
            similarity_percentage=100.0,
            files=[file1, file2]
        )
        
        results = DetectionResults(
            session_id="test_session",
            detection_mode=DetectionMode.EXACT,
            groups=[group],
            total_files_scanned=2,
            total_groups_found=1,
            total_duplicates_found=2,
            detection_time_ms=1000,
            config=DetectionConfig()
        )
        
        report = engine.get_detection_report(results)
        
        assert report['summary']['session_id'] == "test_session"
        assert report['summary']['total_groups_found'] == 1
        assert len(report['groups']) == 1
        assert report['groups'][0]['file_count'] == 2