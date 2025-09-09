"""
Unit tests for updated API endpoints.
"""

import pytest
from unittest.mock import Mock, patch
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.core.detection.models import DetectionResults, DetectionMode, DuplicateGroup, DuplicateFile, DetectionMethod, DetectionConfig


class TestDuplicatesEndpoint:
    """Test the enhanced /duplicates endpoint."""
    
    def setup_method(self):
        """Setup test fixtures."""
        self.client = TestClient(app)
    
    @patch('backend.app.main.DuplicateDetectionService')
    @patch('backend.app.main.get_db')
    def test_duplicates_exact_mode(self, mock_get_db, mock_service_class):
        """Test duplicates endpoint with exact mode."""
        # Setup mock service
        mock_service = Mock()
        mock_service_class.return_value = mock_service
        
        # Create mock results
        file1 = DuplicateFile(1, "/test/file1.jpg", "file1.jpg", 1000)
        file2 = DuplicateFile(2, "/test/file2.jpg", "file2.jpg", 1000)
        
        group = DuplicateGroup(
            id="test_group",
            detection_method=DetectionMethod.SHA256,
            confidence_score=100.0,
            similarity_percentage=100.0,
            files=[file1, file2]
        )
        
        mock_results = DetectionResults(
            session_id="test_session",
            detection_mode=DetectionMode.EXACT,
            groups=[group],
            total_files_scanned=10,
            total_groups_found=1,
            total_duplicates_found=2,
            detection_time_ms=1000,
            config=DetectionConfig(),
            algorithm_performance={"SHA256Detector": {"files_processed": 10}}
        )
        
        mock_service.detect_duplicates_exact.return_value = mock_results
        
        # Make request
        response = self.client.get("/duplicates?mode=exact")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["session_id"] == "test_session"
        assert data["detection_mode"] == "exact"
        assert data["summary"]["total_files_scanned"] == 10
        assert data["summary"]["total_groups_found"] == 1
        assert len(data["duplicate_groups"]) == 1
        
        group_data = data["duplicate_groups"][0]
        assert group_data["id"] == "test_group"
        assert group_data["detection_method"] == "sha256"
        assert group_data["confidence_score"] == 100.0
        assert len(group_data["files"]) == 2
    
    @patch('backend.app.main.DuplicateDetectionService')
    @patch('backend.app.main.get_db')
    def test_duplicates_similar_mode(self, mock_get_db, mock_service_class):
        """Test duplicates endpoint with similar mode."""
        mock_service = Mock()
        mock_service_class.return_value = mock_service
        
        # Create mock results for similar detection
        file1 = DuplicateFile(1, "/test/img1.jpg", "img1.jpg", 1000, confidence_score=85.0)
        file2 = DuplicateFile(2, "/test/img2.jpg", "img2.jpg", 1000, confidence_score=85.0)
        
        group = DuplicateGroup(
            id="similar_group",
            detection_method=DetectionMethod.PERCEPTUAL_HASH,
            confidence_score=85.0,
            similarity_percentage=85.0,
            files=[file1, file2]
        )
        
        mock_results = DetectionResults(
            session_id="similar_session",
            detection_mode=DetectionMode.SIMILAR,
            groups=[group],
            total_files_scanned=20,
            total_groups_found=1,
            total_duplicates_found=2,
            detection_time_ms=2000,
            config=DetectionConfig(),
            algorithm_performance={"PerceptualHashDetector": {"files_processed": 20}}
        )
        
        mock_service.detect_duplicates_similar.return_value = mock_results
        
        # Make request with similarity threshold
        response = self.client.get("/duplicates?mode=similar&similarity_threshold=85.0")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["detection_mode"] == "similar"
        assert data["configuration"]["similarity_threshold"] == 85.0
        mock_service.detect_duplicates_similar.assert_called_once_with(similarity_threshold=85.0)
    
    @patch('backend.app.main.DuplicateDetectionService')
    @patch('backend.app.main.get_db')
    def test_duplicates_comprehensive_mode(self, mock_get_db, mock_service_class):
        """Test duplicates endpoint with comprehensive mode."""
        mock_service = Mock()
        mock_service_class.return_value = mock_service
        
        mock_results = DetectionResults(
            session_id="comprehensive_session",
            detection_mode=DetectionMode.COMPREHENSIVE,
            groups=[],
            total_files_scanned=50,
            total_groups_found=0,
            total_duplicates_found=0,
            detection_time_ms=5000,
            config=DetectionConfig(),
            algorithm_performance={}
        )
        
        mock_service.detect_duplicates_comprehensive.return_value = mock_results
        
        response = self.client.get("/duplicates?mode=comprehensive&confidence_threshold=70.0")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["detection_mode"] == "comprehensive"
        assert data["configuration"]["confidence_threshold"] == 70.0
        mock_service.detect_duplicates_comprehensive.assert_called_once()
    
    @patch('backend.app.main.DuplicateDetectionService')
    @patch('backend.app.main.get_db')
    def test_duplicates_metadata_mode(self, mock_get_db, mock_service_class):
        """Test duplicates endpoint with metadata mode."""
        mock_service = Mock()
        mock_service_class.return_value = mock_service
        
        mock_results = DetectionResults(
            session_id="metadata_session",
            detection_mode=DetectionMode.METADATA,
            groups=[],
            total_files_scanned=30,
            total_groups_found=0,
            total_duplicates_found=0,
            detection_time_ms=3000,
            config=DetectionConfig(),
            algorithm_performance={}
        )
        
        mock_service.detect_duplicates_metadata.return_value = mock_results
        
        response = self.client.get("/duplicates?mode=metadata")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["detection_mode"] == "metadata"
        mock_service.detect_duplicates_metadata.assert_called_once()
    
    @patch('backend.app.main.get_db')
    def test_duplicates_invalid_mode(self, mock_get_db):
        """Test duplicates endpoint with invalid mode."""
        response = self.client.get("/duplicates?mode=invalid")
        
        assert response.status_code == 400
        assert "Invalid detection mode" in response.json()["detail"]
    
    @patch('backend.app.main.DuplicateDetectionService')
    @patch('backend.app.main.get_db')
    def test_duplicates_service_error(self, mock_get_db, mock_service_class):
        """Test duplicates endpoint with service error."""
        mock_service = Mock()
        mock_service_class.return_value = mock_service
        mock_service.detect_duplicates_exact.side_effect = Exception("Service error")
        
        response = self.client.get("/duplicates?mode=exact")
        
        assert response.status_code == 500
        assert "Failed to find duplicates" in response.json()["detail"]


class TestImagesEndpoint:
    """Test the enhanced /images endpoint."""
    
    def setup_method(self):
        """Setup test fixtures."""
        self.client = TestClient(app)
    
    @patch('backend.app.main.DuplicateDetectionService')
    @patch('backend.app.main.get_db')
    def test_images_similar_mode(self, mock_get_db, mock_service_class):
        """Test images endpoint with similar mode."""
        # Setup mock database query
        mock_db = Mock()
        mock_get_db.return_value.__enter__.return_value = mock_db
        
        # Mock image files
        mock_image1 = Mock()
        mock_image1.id = 1
        mock_image1.file_name = "image1.jpg"
        mock_image1.file_path = "/test/image1.jpg"
        mock_image1.file_size = 1000
        mock_image1.file_type = ".jpg"
        mock_image1.width = 1920
        mock_image1.height = 1080
        mock_image1.perceptual_hash = "abc123"
        mock_image1.added_at = None
        
        mock_db.query.return_value.filter.return_value.all.return_value = [mock_image1]
        
        # Setup mock service
        mock_service = Mock()
        mock_service_class.return_value = mock_service
        
        # Create mock detection results
        file1 = DuplicateFile(1, "/test/image1.jpg", "image1.jpg", 1000, 
                             width=1920, height=1080, perceptual_hash="abc123",
                             confidence_score=90.0, is_original=True)
        file2 = DuplicateFile(2, "/test/image2.jpg", "image2.jpg", 1000,
                             width=1920, height=1080, perceptual_hash="def456",
                             confidence_score=85.0)
        
        group = DuplicateGroup(
            id="image_group",
            detection_method=DetectionMethod.PERCEPTUAL_HASH,
            confidence_score=87.5,
            similarity_percentage=87.5,
            files=[file1, file2]
        )
        
        mock_results = DetectionResults(
            session_id="image_session",
            detection_mode=DetectionMode.SIMILAR,
            groups=[group],
            total_files_scanned=2,
            total_groups_found=1,
            total_duplicates_found=2,
            detection_time_ms=1500,
            config=DetectionConfig(),
            algorithm_performance={"PerceptualHashDetector": {"files_processed": 2}}
        )
        
        mock_service.detect_duplicates_similar.return_value = mock_results
        
        # Make request
        response = self.client.get("/images?similarity_threshold=80.0&detection_mode=similar")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["session_id"] == "image_session"
        assert data["detection_mode"] == "similar"
        assert data["total_images"] == 1
        assert data["images_analyzed"] == 2
        assert data["similar_groups"] == 1
        assert data["similarity_threshold"] == 80.0
        
        # Check similar groups
        assert len(data["similar_images"]) == 1
        group_data = data["similar_images"][0]
        assert group_data["id"] == "image_group"
        assert group_data["detection_method"] == "perceptual_hash"
        assert group_data["confidence_score"] == 87.5
        assert len(group_data["images"]) == 2
        
        # Check original file marking
        original_files = [img for img in group_data["images"] if img["is_original"]]
        assert len(original_files) == 1
        assert original_files[0]["id"] == 1
    
    @patch('backend.app.main.DuplicateDetectionService')
    @patch('backend.app.main.get_db')
    def test_images_exact_mode(self, mock_get_db, mock_service_class):
        """Test images endpoint with exact mode."""
        mock_db = Mock()
        mock_get_db.return_value.__enter__.return_value = mock_db
        mock_db.query.return_value.filter.return_value.all.return_value = []
        
        mock_service = Mock()
        mock_service_class.return_value = mock_service
        
        mock_results = DetectionResults(
            session_id="exact_session",
            detection_mode=DetectionMode.EXACT,
            groups=[],
            total_files_scanned=0,
            total_groups_found=0,
            total_duplicates_found=0,
            detection_time_ms=100,
            config=DetectionConfig(),
            algorithm_performance={}
        )
        
        mock_service.detect_duplicates_exact.return_value = mock_results
        
        response = self.client.get("/images?detection_mode=exact")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["detection_mode"] == "exact"
        mock_service.detect_duplicates_exact.assert_called_once()
    
    @patch('backend.app.main.DuplicateDetectionService')
    @patch('backend.app.main.get_db')
    def test_images_comprehensive_mode(self, mock_get_db, mock_service_class):
        """Test images endpoint with comprehensive mode."""
        mock_db = Mock()
        mock_get_db.return_value.__enter__.return_value = mock_db
        mock_db.query.return_value.filter.return_value.all.return_value = []
        
        mock_service = Mock()
        mock_service_class.return_value = mock_service
        
        mock_results = DetectionResults(
            session_id="comp_session",
            detection_mode=DetectionMode.COMPREHENSIVE,
            groups=[],
            total_files_scanned=0,
            total_groups_found=0,
            total_duplicates_found=0,
            detection_time_ms=200,
            config=DetectionConfig(),
            algorithm_performance={}
        )
        
        mock_service.detect_duplicates_comprehensive.return_value = mock_results
        
        response = self.client.get("/images?detection_mode=comprehensive&similarity_threshold=75.0")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["detection_mode"] == "comprehensive"
        mock_service.detect_duplicates_comprehensive.assert_called_once()
    
    @patch('backend.app.main.get_db')
    def test_images_invalid_mode(self, mock_get_db):
        """Test images endpoint with invalid detection mode."""
        mock_db = Mock()
        mock_get_db.return_value.__enter__.return_value = mock_db
        mock_db.query.return_value.filter.return_value.all.return_value = []
        
        response = self.client.get("/images?detection_mode=invalid")
        
        assert response.status_code == 400
        assert "Invalid detection mode" in response.json()["detail"]
    
    @patch('backend.app.main.DuplicateDetectionService')
    @patch('backend.app.main.get_db')
    def test_images_service_error(self, mock_get_db, mock_service_class):
        """Test images endpoint with service error."""
        mock_db = Mock()
        mock_get_db.return_value.__enter__.return_value = mock_db
        mock_db.query.return_value.filter.return_value.all.return_value = []
        
        mock_service = Mock()
        mock_service_class.return_value = mock_service
        mock_service.detect_duplicates_similar.side_effect = Exception("Service error")
        
        response = self.client.get("/images")
        
        assert response.status_code == 500
        assert "Failed to get images" in response.json()["detail"]
    
    @patch('backend.app.main.DuplicateDetectionService')
    @patch('backend.app.main.get_db')
    def test_images_with_file_filters(self, mock_get_db, mock_service_class):
        """Test that images endpoint applies correct file filters."""
        mock_db = Mock()
        mock_get_db.return_value.__enter__.return_value = mock_db
        mock_db.query.return_value.filter.return_value.all.return_value = []
        
        mock_service = Mock()
        mock_service_class.return_value = mock_service
        
        mock_results = DetectionResults(
            session_id="filter_session",
            detection_mode=DetectionMode.SIMILAR,
            groups=[],
            total_files_scanned=0,
            total_groups_found=0,
            total_duplicates_found=0,
            detection_time_ms=100,
            config=DetectionConfig(),
            algorithm_performance={}
        )
        
        mock_service.detect_duplicates_similar.return_value = mock_results
        
        response = self.client.get("/images?similarity_threshold=80.0")
        
        assert response.status_code == 200
        
        # Verify that file filters were passed to the service
        call_args = mock_service.detect_duplicates_similar.call_args
        assert 'file_filters' in call_args.kwargs
        file_filters = call_args.kwargs['file_filters']
        assert 'file_types' in file_filters
        
        # Check that image extensions are included
        expected_extensions = ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff', '.webp']
        assert file_filters['file_types'] == expected_extensions