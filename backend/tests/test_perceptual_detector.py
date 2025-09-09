"""
Unit tests for perceptual hash similarity detector.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock

from backend.app.core.detection.models import DetectionConfig, DuplicateFile, DetectionMethod
from backend.app.core.detection.algorithms.perceptual_detector import PerceptualHashDetector


class TestPerceptualHashDetector:
    """Test PerceptualHashDetector functionality."""
    
    def setup_method(self):
        """Setup test fixtures."""
        self.config = DetectionConfig(perceptual_threshold=80.0)
        
    def test_algorithm_name(self):
        """Test algorithm name."""
        detector = PerceptualHashDetector(self.config)
        assert detector.get_algorithm_name() == "PerceptualHashDetector"
    
    def test_supported_file_types(self):
        """Test supported file types."""
        detector = PerceptualHashDetector(self.config)
        supported_types = detector.get_supported_file_types()
        
        expected_types = ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff', '.webp']
        assert supported_types == expected_types
    
    @patch('backend.app.core.detection.algorithms.perceptual_detector.imagehash')
    def test_can_process_image_file_with_hash(self, mock_imagehash):
        """Test file processing capability for image with perceptual hash."""
        detector = PerceptualHashDetector(self.config)
        detector.hash_available = True
        
        image_file = DuplicateFile(
            file_id=1,
            file_path="/test/image.jpg",
            file_name="image.jpg",
            file_size=1024,
            file_type=".jpg",
            perceptual_hash="abc123def456"
        )
        
        assert detector.can_process_file(image_file) is True
    
    @patch('backend.app.core.detection.algorithms.perceptual_detector.imagehash')
    def test_can_process_non_image_file(self, mock_imagehash):
        """Test file processing capability for non-image file."""
        detector = PerceptualHashDetector(self.config)
        detector.hash_available = True
        
        text_file = DuplicateFile(
            file_id=1,
            file_path="/test/document.txt",
            file_name="document.txt",
            file_size=1024,
            file_type=".txt",
            perceptual_hash="abc123def456"
        )
        
        assert detector.can_process_file(text_file) is False
    
    @patch('backend.app.core.detection.algorithms.perceptual_detector.imagehash')
    def test_can_process_image_without_hash(self, mock_imagehash):
        """Test file processing capability for image without perceptual hash."""
        detector = PerceptualHashDetector(self.config)
        detector.hash_available = True
        
        image_file = DuplicateFile(
            file_id=1,
            file_path="/test/image.jpg",
            file_name="image.jpg",
            file_size=1024,
            file_type=".jpg",
            perceptual_hash=None
        )
        
        assert detector.can_process_file(image_file) is False
    
    def test_imagehash_not_available(self):
        """Test behavior when imagehash library is not available."""
        with patch('backend.app.core.detection.algorithms.perceptual_detector.imagehash', side_effect=ImportError):
            detector = PerceptualHashDetector(self.config)
            assert detector.hash_available is False
            
            # Should not be able to process any files
            image_file = DuplicateFile(1, "/test/image.jpg", "image.jpg", 1024, file_type=".jpg")
            assert detector.can_process_file(image_file) is False
    
    def test_detect_no_files(self):
        """Test detection with no files."""
        with patch('backend.app.core.detection.algorithms.perceptual_detector.imagehash'):
            detector = PerceptualHashDetector(self.config)
            detector.hash_available = True
            
            groups = detector.detect([])
            assert groups == []
    
    @patch('backend.app.core.detection.algorithms.perceptual_detector.imagehash')
    def test_detect_insufficient_files(self, mock_imagehash):
        """Test detection with insufficient files."""
        detector = PerceptualHashDetector(self.config)
        detector.hash_available = True
        
        single_file = DuplicateFile(
            file_id=1,
            file_path="/test/image.jpg",
            file_name="image.jpg",
            file_size=1024,
            file_type=".jpg",
            perceptual_hash="abc123"
        )
        
        groups = detector.detect([single_file])
        assert groups == []
    
    @patch('backend.app.core.detection.algorithms.perceptual_detector.imagehash')
    def test_calculate_similarity_identical_hashes(self, mock_imagehash):
        """Test similarity calculation for identical hashes."""
        detector = PerceptualHashDetector(self.config)
        detector.hash_available = True
        
        # Mock imagehash objects
        mock_hash1 = Mock()
        mock_hash2 = Mock()
        mock_hash1.__sub__ = Mock(return_value=0)  # Hamming distance = 0
        mock_hash1.__str__ = Mock(return_value="abcd1234")  # 8 character hash
        
        mock_imagehash.hex_to_hash.side_effect = [mock_hash1, mock_hash2]
        
        similarity = detector._calculate_similarity("abc123", "abc123")
        assert similarity == 100.0
    
    @patch('backend.app.core.detection.algorithms.perceptual_detector.imagehash')
    def test_calculate_similarity_different_hashes(self, mock_imagehash):
        """Test similarity calculation for different hashes."""
        detector = PerceptualHashDetector(self.config)
        detector.hash_available = True
        
        # Mock imagehash objects
        mock_hash1 = Mock()
        mock_hash2 = Mock()
        mock_hash1.__sub__ = Mock(return_value=8)  # Hamming distance = 8
        mock_hash1.__str__ = Mock(return_value="abcd1234")  # 8 character hash (max distance = 32)
        
        mock_imagehash.hex_to_hash.side_effect = [mock_hash1, mock_hash2]
        
        similarity = detector._calculate_similarity("abc123", "def456")
        expected_similarity = (32 - 8) / 32 * 100  # 75.0
        assert similarity == 75.0
    
    @patch('backend.app.core.detection.algorithms.perceptual_detector.imagehash')
    def test_calculate_similarity_error_handling(self, mock_imagehash):
        """Test similarity calculation error handling."""
        detector = PerceptualHashDetector(self.config)
        detector.hash_available = True
        
        mock_imagehash.hex_to_hash.side_effect = Exception("Invalid hash")
        
        similarity = detector._calculate_similarity("invalid", "hash")
        assert similarity == 0.0
    
    @patch('backend.app.core.detection.algorithms.perceptual_detector.imagehash')
    def test_detect_similar_images(self, mock_imagehash):
        """Test detection of similar images."""
        detector = PerceptualHashDetector(self.config)
        detector.hash_available = True
        
        # Create test files
        file1 = DuplicateFile(1, "/test/img1.jpg", "img1.jpg", 1024, file_type=".jpg", perceptual_hash="hash1")
        file2 = DuplicateFile(2, "/test/img2.jpg", "img2.jpg", 1024, file_type=".jpg", perceptual_hash="hash2")
        file3 = DuplicateFile(3, "/test/img3.jpg", "img3.jpg", 1024, file_type=".jpg", perceptual_hash="hash3")
        
        # Mock similarity calculations
        def mock_similarity(hash1, hash2):
            if (hash1, hash2) in [("hash1", "hash2"), ("hash2", "hash1")]:
                return 85.0  # Above threshold
            return 50.0  # Below threshold
        
        detector._calculate_similarity = Mock(side_effect=mock_similarity)
        
        files = [file1, file2, file3]
        groups = detector.detect(files)
        
        assert len(groups) == 1
        group = groups[0]
        
        assert group.detection_method == DetectionMethod.PERCEPTUAL_HASH
        assert len(group.files) == 2
        assert group.confidence_score >= 80.0  # Should be above threshold
        
        # Check that files have detection reasons
        for file in group.files:
            assert "similar_perceptual_hash" in file.detection_reasons
    
    @patch('backend.app.core.detection.algorithms.perceptual_detector.imagehash')
    def test_detect_identical_perceptual_hashes(self, mock_imagehash):
        """Test detection of identical perceptual hashes."""
        detector = PerceptualHashDetector(self.config)
        detector.hash_available = True
        
        file1 = DuplicateFile(1, "/test/img1.jpg", "img1.jpg", 1024, file_type=".jpg", perceptual_hash="identical")
        file2 = DuplicateFile(2, "/test/img2.jpg", "img2.jpg", 1024, file_type=".jpg", perceptual_hash="identical")
        
        detector._calculate_similarity = Mock(return_value=100.0)
        
        groups = detector.detect([file1, file2])
        
        assert len(groups) == 1
        group = groups[0]
        
        # Check for identical hash detection reason
        for file in group.files:
            assert "identical_perceptual_hash" in file.detection_reasons
            assert file.confidence_score == 100.0
    
    @patch('backend.app.core.detection.algorithms.perceptual_detector.imagehash')
    def test_get_similarity_matrix(self, mock_imagehash):
        """Test similarity matrix calculation."""
        detector = PerceptualHashDetector(self.config)
        detector.hash_available = True
        
        file1 = DuplicateFile(1, "/test/img1.jpg", "img1.jpg", 1024, file_type=".jpg", perceptual_hash="hash1")
        file2 = DuplicateFile(2, "/test/img2.jpg", "img2.jpg", 1024, file_type=".jpg", perceptual_hash="hash2")
        file3 = DuplicateFile(3, "/test/img3.jpg", "img3.jpg", 1024, file_type=".jpg", perceptual_hash="hash3")
        
        # Mock similarity calculations
        similarity_map = {
            ("hash1", "hash2"): 85.0,
            ("hash1", "hash3"): 60.0,
            ("hash2", "hash3"): 70.0
        }
        
        def mock_similarity(hash1, hash2):
            return similarity_map.get((hash1, hash2), similarity_map.get((hash2, hash1), 0.0))
        
        detector._calculate_similarity = Mock(side_effect=mock_similarity)
        
        matrix = detector.get_similarity_matrix([file1, file2, file3])
        
        # Check that matrix is symmetric and contains expected values
        assert matrix[(1, 2)] == 85.0
        assert matrix[(2, 1)] == 85.0
        assert matrix[(1, 3)] == 60.0
        assert matrix[(3, 1)] == 60.0
        assert matrix[(2, 3)] == 70.0
        assert matrix[(3, 2)] == 70.0
    
    @patch('backend.app.core.detection.algorithms.perceptual_detector.imagehash')
    def test_get_hash_algorithms_info(self, mock_imagehash):
        """Test getting hash algorithms information."""
        detector = PerceptualHashDetector(self.config)
        detector.hash_available = True
        
        # Mock available hash algorithms
        mock_imagehash.average_hash = Mock()
        mock_imagehash.perceptual_hash = Mock()
        mock_imagehash.difference_hash = Mock()
        mock_imagehash.wavelet_hash = Mock()
        
        info = detector.get_hash_algorithms_info()
        
        assert info['available'] is True
        assert len(info['algorithms']) == 4
        assert info['current_threshold'] == 80.0
        
        # Check that all expected algorithms are present
        algorithm_names = [alg['name'] for alg in info['algorithms']]
        expected_names = ['average_hash', 'perceptual_hash', 'difference_hash', 'wavelet_hash']
        assert all(name in algorithm_names for name in expected_names)
    
    def test_get_hash_algorithms_info_unavailable(self):
        """Test getting hash algorithms info when imagehash is unavailable."""
        with patch('backend.app.core.detection.algorithms.perceptual_detector.imagehash', side_effect=ImportError):
            detector = PerceptualHashDetector(self.config)
            
            info = detector.get_hash_algorithms_info()
            
            assert info['available'] is False
            assert info['algorithms'] == []
    
    @patch('backend.app.core.detection.algorithms.perceptual_detector.imagehash')
    def test_analyze_hash_distribution(self, mock_imagehash):
        """Test hash distribution analysis."""
        detector = PerceptualHashDetector(self.config)
        detector.hash_available = True
        
        files = [
            DuplicateFile(1, "/test/img1.jpg", "img1.jpg", 1024, file_type=".jpg", perceptual_hash="abcd1234"),
            DuplicateFile(2, "/test/img2.jpg", "img2.jpg", 1024, file_type=".jpg", perceptual_hash="efgh5678"),
            DuplicateFile(3, "/test/img3.jpg", "img3.jpg", 1024, file_type=".jpg", perceptual_hash="abcd1234"),  # Duplicate
            DuplicateFile(4, "/test/img4.jpg", "img4.jpg", 1024, file_type=".jpg", perceptual_hash=None),  # No hash
            DuplicateFile(5, "/test/doc.txt", "doc.txt", 1024, file_type=".txt", perceptual_hash="ijkl9012")  # Not image
        ]
        
        analysis = detector.analyze_hash_distribution(files)
        
        assert analysis['total_images'] == 4  # Only image files
        assert analysis['images_with_hash'] == 3  # Excluding the one without hash
        assert analysis['unique_hashes'] == 2  # "abcd1234" and "efgh5678"
        assert analysis['potential_exact_duplicates'] == 1  # 3 images - 2 unique hashes
        assert analysis['hash_length_distribution'][8] == 3  # Three 8-character hashes
    
    @patch('backend.app.core.detection.algorithms.perceptual_detector.imagehash')
    def test_filter_image_files(self, mock_imagehash):
        """Test filtering to only image files."""
        detector = PerceptualHashDetector(self.config)
        detector.hash_available = True
        
        files = [
            DuplicateFile(1, "/test/img1.jpg", "img1.jpg", 1024, file_type=".jpg", perceptual_hash="hash1"),
            DuplicateFile(2, "/test/doc.txt", "doc.txt", 1024, file_type=".txt", perceptual_hash="hash2"),
            DuplicateFile(3, "/test/img2.png", "img2.png", 1024, file_type=".png", perceptual_hash="hash3"),
            DuplicateFile(4, "/test/img3.jpg", "img3.jpg", 1024, file_type=".jpg", perceptual_hash=None)
        ]
        
        filtered = detector._filter_image_files(files)
        
        assert len(filtered) == 2  # Only the two valid image files
        assert all(f.file_type in [".jpg", ".png"] for f in filtered)
        assert all(f.perceptual_hash is not None for f in filtered)
    
    @patch('backend.app.core.detection.algorithms.perceptual_detector.imagehash')
    def test_create_similarity_group(self, mock_imagehash):
        """Test creating similarity group from files."""
        detector = PerceptualHashDetector(self.config)
        detector.hash_available = True
        
        file1 = DuplicateFile(1, "/test/img1.jpg", "img1.jpg", 1000)
        file2 = DuplicateFile(2, "/test/img2.jpg", "img2.jpg", 2000)
        files = [file1, file2]
        similarities = [100.0, 85.0]
        
        group = detector._create_similarity_group(files, similarities)
        
        assert group.detection_method == DetectionMethod.PERCEPTUAL_HASH
        assert group.confidence_score == 92.5  # Average of 100.0 and 85.0
        assert group.similarity_percentage == 92.5
        assert len(group.files) == 2
        
        # Check metadata
        assert group.metadata['avg_similarity'] == 92.5
        assert group.metadata['min_similarity'] == 85.0
        assert group.metadata['max_similarity'] == 100.0
        assert group.metadata['total_size'] == 3000
        assert group.metadata['threshold_used'] == 80.0