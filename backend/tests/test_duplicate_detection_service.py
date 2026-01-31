"""
Unit tests for duplicate detection service layer.
"""

import pytest
import tempfile
import sqlite3
import json
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime

from backend.app.services.duplicate_detection_service import DuplicateDetectionService
from backend.app.core.detection.models import DetectionConfig, DetectionMode, DetectionResults, DuplicateGroup, DuplicateFile, DetectionMethod
from backend.app.models.file import File


class TestDuplicateDetectionService:
    """Test DuplicateDetectionService functionality."""
    
    def setup_method(self):
        """Setup test fixtures."""
        # Create mock database session
        self.mock_db_session = Mock()
        self.mock_db_session.get_bind.return_value.url.database = ":memory:"
        
        # Create service instance
        self.service = DuplicateDetectionService(self.mock_db_session)
        
        # Create temporary database for testing storage operations
        self.temp_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        self.temp_db.close()
        self.temp_db_path = self.temp_db.name
        
        # Setup test database schema
        self._setup_test_database()
    
    def teardown_method(self):
        """Cleanup test fixtures."""
        import os
        if os.path.exists(self.temp_db_path):
            os.unlink(self.temp_db_path)
    
    def _setup_test_database(self):
        """Setup test database with required tables."""
        with sqlite3.connect(self.temp_db_path) as conn:
            # Create required tables for testing
            conn.execute("""
                CREATE TABLE detection_results (
                    id INTEGER PRIMARY KEY,
                    session_id TEXT UNIQUE,
                    detection_mode TEXT,
                    total_files_scanned INTEGER,
                    total_groups_found INTEGER,
                    total_duplicates_found INTEGER,
                    detection_time_ms INTEGER,
                    config_json TEXT,
                    algorithm_performance_json TEXT,
                    errors_json TEXT,
                    success_rate REAL,
                    duplicate_percentage REAL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            conn.execute("""
                CREATE TABLE algorithm_performance (
                    id INTEGER PRIMARY KEY,
                    session_id TEXT,
                    algorithm_name TEXT,
                    files_processed INTEGER,
                    execution_time_ms INTEGER,
                    groups_found INTEGER,
                    errors_encountered INTEGER,
                    files_per_second REAL,
                    error_rate REAL
                )
            """)
            
            conn.execute("""
                CREATE TABLE duplicate_groups (
                    id INTEGER PRIMARY KEY,
                    group_hash TEXT,
                    duplicate_type TEXT,
                    similarity_score REAL,
                    detection_method TEXT,
                    confidence_score REAL,
                    session_id TEXT,
                    metadata_json TEXT
                )
            """)
            
            conn.execute("""
                CREATE TABLE duplicate_files (
                    id INTEGER PRIMARY KEY,
                    group_id INTEGER,
                    file_id INTEGER,
                    is_original BOOLEAN
                )
            """)
            
            conn.execute("""
                CREATE TABLE files (
                    id INTEGER PRIMARY KEY,
                    file_path TEXT,
                    file_name TEXT,
                    file_size INTEGER,
                    file_type TEXT
                )
            """)
            
            conn.commit()
    
    def test_get_detection_engine(self):
        """Test getting detection engine with configuration."""
        config = DetectionConfig(perceptual_threshold=85.0)
        
        engine = self.service.get_detection_engine(config)
        
        assert engine is not None
        assert engine.config.perceptual_threshold == 85.0
        assert len(engine.algorithms) == 3  # SHA256, Perceptual, Metadata
    
    def test_get_detection_engine_reuse(self):
        """Test that detection engine is reused with same config."""
        config = DetectionConfig(perceptual_threshold=85.0)
        
        engine1 = self.service.get_detection_engine(config)
        engine2 = self.service.get_detection_engine(config)
        
        assert engine1 is engine2  # Should be the same instance
    
    def test_get_detection_engine_new_config(self):
        """Test that new engine is created with different config."""
        config1 = DetectionConfig(perceptual_threshold=85.0)
        config2 = DetectionConfig(perceptual_threshold=90.0)
        
        engine1 = self.service.get_detection_engine(config1)
        engine2 = self.service.get_detection_engine(config2)
        
        assert engine1 is not engine2  # Should be different instances
    
    @patch('backend.app.services.duplicate_detection_service.DuplicateDetectionEngine')
    def test_detect_duplicates_exact(self, mock_engine_class):
        """Test exact duplicate detection."""
        # Setup mock engine
        mock_engine = Mock()
        mock_results = Mock(spec=DetectionResults)
        mock_engine.detect_duplicates.return_value = mock_results
        mock_engine_class.return_value = mock_engine
        
        # Setup mock files
        self._setup_mock_files()
        
        # Mock storage method
        self.service._store_detection_results = Mock()
        
        results = self.service.detect_duplicates_exact()
        
        assert results == mock_results
        mock_engine.detect_duplicates.assert_called_once()
        args, kwargs = mock_engine.detect_duplicates.call_args
        assert args[1] == DetectionMode.EXACT  # Detection mode
        self.service._store_detection_results.assert_called_once_with(mock_results)
    
    @patch('backend.app.services.duplicate_detection_service.DuplicateDetectionEngine')
    def test_detect_duplicates_similar(self, mock_engine_class):
        """Test similar duplicate detection."""
        mock_engine = Mock()
        mock_results = Mock(spec=DetectionResults)
        mock_engine.detect_duplicates.return_value = mock_results
        mock_engine_class.return_value = mock_engine
        
        self._setup_mock_files()
        self.service._store_detection_results = Mock()
        
        results = self.service.detect_duplicates_similar(similarity_threshold=85.0)
        
        assert results == mock_results
        mock_engine.detect_duplicates.assert_called_once()
        args, kwargs = mock_engine.detect_duplicates.call_args
        assert args[1] == DetectionMode.SIMILAR
        self.service._store_detection_results.assert_called_once_with(mock_results)
    
    @patch('backend.app.services.duplicate_detection_service.DuplicateDetectionEngine')
    def test_detect_duplicates_comprehensive(self, mock_engine_class):
        """Test comprehensive duplicate detection."""
        mock_engine = Mock()
        mock_results = Mock(spec=DetectionResults)
        mock_engine.detect_duplicates.return_value = mock_results
        mock_engine_class.return_value = mock_engine
        
        self._setup_mock_files()
        self.service._store_detection_results = Mock()
        
        config = DetectionConfig(min_confidence_threshold=70.0)
        results = self.service.detect_duplicates_comprehensive(config=config)
        
        assert results == mock_results
        mock_engine.detect_duplicates.assert_called_once()
        args, kwargs = mock_engine.detect_duplicates.call_args
        assert args[1] == DetectionMode.COMPREHENSIVE
        self.service._store_detection_results.assert_called_once_with(mock_results)
    
    @patch('backend.app.services.duplicate_detection_service.DuplicateDetectionEngine')
    def test_detect_duplicates_metadata(self, mock_engine_class):
        """Test metadata-based duplicate detection."""
        mock_engine = Mock()
        mock_results = Mock(spec=DetectionResults)
        mock_engine.detect_duplicates.return_value = mock_results
        mock_engine_class.return_value = mock_engine
        
        self._setup_mock_files()
        self.service._store_detection_results = Mock()
        
        results = self.service.detect_duplicates_metadata(
            metadata_fields=['file_size', 'width', 'height']
        )
        
        assert results == mock_results
        mock_engine.detect_duplicates.assert_called_once()
        args, kwargs = mock_engine.detect_duplicates.call_args
        assert args[1] == DetectionMode.METADATA
        self.service._store_detection_results.assert_called_once_with(mock_results)
    
    def test_get_files_for_detection_no_filters(self):
        """Test getting files for detection without filters."""
        # Setup mock query
        mock_file1 = Mock(spec=File)
        mock_file1.id = 1
        mock_file1.file_path = "/test/file1.jpg"
        mock_file1.file_name = "file1.jpg"
        mock_file1.file_size = 1024
        mock_file1.sha256 = "abc123"
        mock_file1.perceptual_hash = "def456"
        mock_file1.file_type = ".jpg"
        mock_file1.mime_type = "image/jpeg"
        mock_file1.width = 1920
        mock_file1.height = 1080
        mock_file1.created_at = datetime.now()
        mock_file1.modified_at = datetime.now()
        
        mock_query = Mock()
        mock_query.all.return_value = [mock_file1]
        self.mock_db_session.query.return_value = mock_query
        
        files = self.service._get_files_for_detection()
        
        assert len(files) == 1
        assert isinstance(files[0], DuplicateFile)
        assert files[0].file_id == 1
        assert files[0].file_path == "/test/file1.jpg"
    
    def test_get_files_for_detection_with_filters(self):
        """Test getting files for detection with filters."""
        mock_query = Mock()
        mock_query.filter.return_value = mock_query
        mock_query.all.return_value = []
        self.mock_db_session.query.return_value = mock_query
        
        file_filters = {
            'file_types': ['.jpg', '.png'],
            'min_size': 1000,
            'max_size': 10000,
            'path_pattern': 'photos'
        }
        
        files = self.service._get_files_for_detection(file_filters)
        
        # Verify filters were applied
        assert mock_query.filter.call_count == 4  # One for each filter
        assert len(files) == 0  # Empty result from mock
    
    def test_store_detection_results(self):
        """Test storing detection results in database."""
        # Override database path for testing
        self.mock_db_session.get_bind.return_value.url.database = self.temp_db_path
        
        # Create test results
        file1 = DuplicateFile(1, "/test/file1.jpg", "file1.jpg", 1000)
        file2 = DuplicateFile(2, "/test/file2.jpg", "file2.jpg", 1000)
        
        group = DuplicateGroup(
            id="test_group",
            detection_method=DetectionMethod.SHA256,
            confidence_score=100.0,
            similarity_percentage=100.0,
            files=[file1, file2],
            metadata={'test': 'data'}
        )
        
        results = DetectionResults(
            session_id="test_session",
            detection_mode=DetectionMode.EXACT,
            groups=[group],
            total_files_scanned=2,
            total_groups_found=1,
            total_duplicates_found=2,
            detection_time_ms=1000,
            config=DetectionConfig(),
            algorithm_performance={'SHA256Detector': {'files_processed': 2}}
        )
        
        # Store results
        self.service._store_detection_results(results)
        
        # Verify storage
        with sqlite3.connect(self.temp_db_path) as conn:
            cursor = conn.execute("SELECT session_id FROM detection_results")
            assert cursor.fetchone()[0] == "test_session"
            
            cursor = conn.execute("SELECT algorithm_name FROM algorithm_performance")
            assert cursor.fetchone()[0] == "SHA256Detector"
            
            cursor = conn.execute("SELECT group_hash FROM duplicate_groups")
            assert cursor.fetchone()[0] == "test_group"
    
    def test_get_detection_results(self):
        """Test retrieving detection results by session ID."""
        # Override database path for testing
        self.mock_db_session.get_bind.return_value.url.database = self.temp_db_path
        
        # Insert test data
        with sqlite3.connect(self.temp_db_path) as conn:
            conn.execute("""
                INSERT INTO detection_results (
                    session_id, detection_mode, total_files_scanned,
                    total_groups_found, total_duplicates_found, detection_time_ms,
                    success_rate, duplicate_percentage
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, ("test_session", "exact", 10, 2, 5, 2000, 95.0, 50.0))
            
            conn.execute("""
                INSERT INTO files (id, file_path, file_name, file_size, file_type)
                VALUES (1, '/test/file1.jpg', 'file1.jpg', 1000, '.jpg')
            """)
            
            conn.execute("""
                INSERT INTO duplicate_groups (
                    id, group_hash, duplicate_type, similarity_score,
                    detection_method, confidence_score, session_id
                ) VALUES (1, 'group1', 'exact', 100.0, 'sha256', 100.0, 'test_session')
            """)
            
            conn.execute("""
                INSERT INTO duplicate_files (group_id, file_id, is_original)
                VALUES (1, 1, 1)
            """)
            
            conn.commit()
        
        results = self.service.get_detection_results("test_session")
        
        assert results is not None
        assert results['session_id'] == "test_session"
        assert results['detection_mode'] == "exact"
        assert results['summary']['total_files_scanned'] == 10
        assert len(results['groups']) == 1
        assert results['groups'][0]['id'] == 'group1'
    
    def test_get_detection_results_not_found(self):
        """Test retrieving non-existent detection results."""
        self.mock_db_session.get_bind.return_value.url.database = self.temp_db_path
        
        results = self.service.get_detection_results("nonexistent_session")
        
        assert results is None
    
    def test_list_detection_sessions(self):
        """Test listing detection sessions."""
        self.mock_db_session.get_bind.return_value.url.database = self.temp_db_path
        
        # Insert test sessions
        with sqlite3.connect(self.temp_db_path) as conn:
            conn.execute("""
                INSERT INTO detection_results (
                    session_id, detection_mode, total_files_scanned,
                    total_groups_found, total_duplicates_found, detection_time_ms,
                    success_rate
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """, ("session1", "exact", 10, 2, 5, 1000, 95.0))
            
            conn.execute("""
                INSERT INTO detection_results (
                    session_id, detection_mode, total_files_scanned,
                    total_groups_found, total_duplicates_found, detection_time_ms,
                    success_rate
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """, ("session2", "similar", 20, 3, 8, 2000, 90.0))
            
            conn.commit()
        
        sessions = self.service.list_detection_sessions()
        
        assert len(sessions) == 2
        assert sessions[0]['session_id'] in ['session1', 'session2']
        assert sessions[1]['session_id'] in ['session1', 'session2']
    
    def test_delete_detection_session(self):
        """Test deleting a detection session."""
        self.mock_db_session.get_bind.return_value.url.database = self.temp_db_path
        
        # Insert test data
        with sqlite3.connect(self.temp_db_path) as conn:
            conn.execute("""
                INSERT INTO detection_results (session_id, detection_mode, total_files_scanned)
                VALUES ('test_session', 'exact', 10)
            """)
            
            conn.execute("""
                INSERT INTO algorithm_performance (session_id, algorithm_name, files_processed)
                VALUES ('test_session', 'SHA256Detector', 10)
            """)
            
            conn.commit()
        
        # Delete session
        result = self.service.delete_detection_session("test_session")
        
        assert result is True
        
        # Verify deletion
        with sqlite3.connect(self.temp_db_path) as conn:
            cursor = conn.execute("SELECT COUNT(*) FROM detection_results WHERE session_id = ?", ("test_session",))
            assert cursor.fetchone()[0] == 0
            
            cursor = conn.execute("SELECT COUNT(*) FROM algorithm_performance WHERE session_id = ?", ("test_session",))
            assert cursor.fetchone()[0] == 0
    
    def test_get_detection_statistics(self):
        """Test getting detection statistics."""
        self.mock_db_session.get_bind.return_value.url.database = self.temp_db_path
        
        # Insert test data
        with sqlite3.connect(self.temp_db_path) as conn:
            conn.execute("""
                INSERT INTO detection_results (
                    session_id, detection_mode, total_files_scanned,
                    total_groups_found, detection_time_ms, success_rate
                ) VALUES ('session1', 'exact', 10, 2, 1000, 95.0)
            """)
            
            conn.execute("""
                INSERT INTO detection_results (
                    session_id, detection_mode, total_files_scanned,
                    total_groups_found, detection_time_ms, success_rate
                ) VALUES ('session2', 'similar', 20, 3, 2000, 90.0)
            """)
            
            conn.execute("""
                INSERT INTO algorithm_performance (
                    session_id, algorithm_name, files_per_second, error_rate
                ) VALUES ('session1', 'SHA256Detector', 10.0, 5.0)
            """)
            
            conn.commit()
        
        stats = self.service.get_detection_statistics()
        
        assert 'session_statistics' in stats
        assert 'detection_mode_distribution' in stats
        assert 'algorithm_performance' in stats
        
        session_stats = stats['session_statistics']
        assert session_stats['total_sessions'] == 2
        assert session_stats['avg_files_per_session'] == 15.0  # (10 + 20) / 2
        
        mode_dist = stats['detection_mode_distribution']
        assert mode_dist['exact'] == 1
        assert mode_dist['similar'] == 1
        
        algo_perf = stats['algorithm_performance']
        assert 'SHA256Detector' in algo_perf
    
    def test_config_to_dict(self):
        """Test converting DetectionConfig to dictionary."""
        config = DetectionConfig(
            perceptual_threshold=85.0,
            metadata_fields=['file_size', 'modified_at'],
            min_confidence_threshold=70.0
        )
        
        config_dict = self.service._config_to_dict(config)
        
        assert config_dict['perceptual_threshold'] == 85.0
        assert config_dict['metadata_fields'] == ['file_size', 'modified_at']
        assert config_dict['min_confidence_threshold'] == 70.0
        assert 'perceptual_hash_size' in config_dict
        assert 'enable_cross_algorithm_validation' in config_dict
    
    def _setup_mock_files(self):
        """Setup mock files for testing."""
        mock_query = Mock()
        mock_query.filter.return_value = mock_query
        mock_query.all.return_value = []
        self.mock_db_session.query.return_value = mock_query