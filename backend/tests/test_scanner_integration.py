"""
Integration tests for enhanced scanner functionality.
"""

import os
import sys
import tempfile
import shutil
import sqlite3
import subprocess
from pathlib import Path
from datetime import datetime
import pytest

# Add backend to path for imports
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from scripts.scan_folder import FileScanner
from app.core.detection import DetectionMode, DetectionConfig


class TestScannerIntegration:
    """Integration tests for scanner with enhanced duplicate detection."""
    
    @pytest.fixture
    def temp_dir(self):
        """Create temporary directory for test files."""
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        shutil.rmtree(temp_dir)
    
    @pytest.fixture
    def test_db(self):
        """Create temporary test database."""
        db_fd, db_path = tempfile.mkstemp(suffix='.db')
        os.close(db_fd)
        yield db_path
        if os.path.exists(db_path):
            os.unlink(db_path)
    
    @pytest.fixture
    def scanner(self, test_db):
        """Create FileScanner instance."""
        scanner = FileScanner(test_db, dry_run=False)
        scanner.connect_db()
        yield scanner
        scanner.close()
    
    @pytest.fixture
    def sample_files(self, temp_dir):
        """Create sample files for testing."""
        files = {}
        
        # Create identical files (exact duplicates)
        content1 = b"This is test content for duplicate detection"
        files['file1.txt'] = os.path.join(temp_dir, 'file1.txt')
        files['file1_copy.txt'] = os.path.join(temp_dir, 'file1_copy.txt')
        
        with open(files['file1.txt'], 'wb') as f:
            f.write(content1)
        with open(files['file1_copy.txt'], 'wb') as f:
            f.write(content1)
        
        # Create different file
        content2 = b"This is different content"
        files['file2.txt'] = os.path.join(temp_dir, 'file2.txt')
        with open(files['file2.txt'], 'wb') as f:
            f.write(content2)
        
        # Create subdirectory with another duplicate
        subdir = os.path.join(temp_dir, 'subdir')
        os.makedirs(subdir)
        files['file1_sub.txt'] = os.path.join(subdir, 'file1_sub.txt')
        with open(files['file1_sub.txt'], 'wb') as f:
            f.write(content1)
        
        return files
    
    def test_scanner_basic_functionality(self, scanner, sample_files, temp_dir):
        """Test basic scanner functionality."""
        # Scan the directory
        scanner.scan_folder(temp_dir, recursive=True)
        
        # Check that files were processed
        assert scanner.stats['total_files'] == 4
        assert scanner.stats['processed_files'] == 4
        assert scanner.stats['errors'] == 0
        
        # Check database contains files
        count = scanner.cursor.execute("SELECT COUNT(*) FROM files").fetchone()[0]
        assert count == 4
    
    def test_legacy_duplicate_detection(self, scanner, sample_files, temp_dir):
        """Test legacy duplicate detection functionality."""
        # Scan and detect duplicates
        scanner.scan_folder(temp_dir, recursive=True)
        duplicates = scanner.find_duplicates()
        
        # Should find one group with 3 identical files
        assert len(duplicates) == 1
        assert duplicates[0]['count'] == 3
        
        # Check file paths
        file_paths = [f['file_path'] for f in duplicates[0]['files']]
        expected_files = [sample_files['file1.txt'], sample_files['file1_copy.txt'], sample_files['file1_sub.txt']]
        
        for expected_file in expected_files:
            assert expected_file in file_paths
    
    @pytest.mark.skipif(not hasattr(sys.modules.get('scripts.scan_folder', None), 'ENHANCED_DETECTION_AVAILABLE') or 
                       not getattr(sys.modules.get('scripts.scan_folder', None), 'ENHANCED_DETECTION_AVAILABLE', False),
                       reason="Enhanced detection not available")
    def test_enhanced_duplicate_detection_exact(self, scanner, sample_files, temp_dir):
        """Test enhanced duplicate detection in exact mode."""
        # Scan files first
        scanner.scan_folder(temp_dir, recursive=True)
        
        # Run enhanced detection
        results = scanner.detect_duplicates_enhanced(mode='exact')
        
        assert results is not None
        assert results.detection_mode == DetectionMode.EXACT
        assert results.total_files_scanned == 4
        assert results.total_groups_found == 1
        assert results.total_duplicates_found == 3
        
        # Check the duplicate group
        group = results.groups[0]
        assert group.confidence_score == 100.0  # Exact matches should have 100% confidence
        assert len(group.files) == 3
        
        # Check that one file is marked as original
        originals = [f for f in group.files if f.is_original]
        assert len(originals) == 1
    
    @pytest.mark.skipif(not hasattr(sys.modules.get('scripts.scan_folder', None), 'ENHANCED_DETECTION_AVAILABLE') or 
                       not getattr(sys.modules.get('scripts.scan_folder', None), 'ENHANCED_DETECTION_AVAILABLE', False),
                       reason="Enhanced detection not available")
    def test_enhanced_duplicate_detection_comprehensive(self, scanner, sample_files, temp_dir):
        """Test enhanced duplicate detection in comprehensive mode."""
        # Scan files first
        scanner.scan_folder(temp_dir, recursive=True)
        
        # Run enhanced detection
        results = scanner.detect_duplicates_enhanced(mode='comprehensive')
        
        assert results is not None
        assert results.detection_mode == DetectionMode.COMPREHENSIVE
        assert results.total_files_scanned == 4
        assert results.total_groups_found >= 1  # Should find at least the exact duplicates
        
        # Check algorithm performance data
        assert len(results.algorithm_performance) > 0
        
        # Should have SHA256 algorithm results
        assert any('SHA256' in algo_name for algo_name in results.algorithm_performance.keys())
    
    @pytest.mark.skipif(not hasattr(sys.modules.get('scripts.scan_folder', None), 'ENHANCED_DETECTION_AVAILABLE') or 
                       not getattr(sys.modules.get('scripts.scan_folder', None), 'ENHANCED_DETECTION_AVAILABLE', False),
                       reason="Enhanced detection not available")
    def test_enhanced_detection_with_config(self, scanner, sample_files, temp_dir):
        """Test enhanced detection with custom configuration."""
        # Scan files first
        scanner.scan_folder(temp_dir, recursive=True)
        
        # Custom configuration
        config = {
            'min_confidence_threshold': 90.0,
            'max_results_per_group': 50
        }
        
        # Run enhanced detection
        results = scanner.detect_duplicates_enhanced(mode='exact', config=config)
        
        assert results is not None
        assert results.config.min_confidence_threshold == 90.0
        assert results.config.max_results_per_group == 50
    
    @pytest.mark.skipif(not hasattr(sys.modules.get('scripts.scan_folder', None), 'ENHANCED_DETECTION_AVAILABLE') or 
                       not getattr(sys.modules.get('scripts.scan_folder', None), 'ENHANCED_DETECTION_AVAILABLE', False),
                       reason="Enhanced detection not available")
    def test_enhanced_detection_with_filters(self, scanner, sample_files, temp_dir):
        """Test enhanced detection with file filters."""
        # Scan files first
        scanner.scan_folder(temp_dir, recursive=True)
        
        # Filter for only .txt files
        file_filters = {
            'file_types': ['.txt'],
            'min_size': 10  # Minimum 10 bytes
        }
        
        # Run enhanced detection
        results = scanner.detect_duplicates_enhanced(mode='exact', file_filters=file_filters)
        
        assert results is not None
        # Should still find the duplicates since all test files are .txt
        assert results.total_groups_found == 1
    
    def test_progress_reporting(self, scanner, sample_files, temp_dir):
        """Test progress reporting functionality."""
        # Scan files first
        scanner.scan_folder(temp_dir, recursive=True)
        
        progress_messages = []
        
        def progress_callback(message: str, percentage: int):
            progress_messages.append((message, percentage))
        
        # Run detection with progress callback
        if hasattr(scanner, 'detect_duplicates_enhanced'):
            results = scanner.detect_duplicates_enhanced(
                mode='exact',
                progress_callback=progress_callback
            )
            
            # Should have received progress messages
            assert len(progress_messages) >= 2  # At least start and end
            assert progress_messages[0][1] == 0  # Start at 0%
            assert progress_messages[-1][1] == 100  # End at 100%
    
    def test_cli_integration_basic(self, temp_dir, test_db):
        """Test CLI integration with basic scanning."""
        # Create a simple test file
        test_file = os.path.join(temp_dir, 'test.txt')
        with open(test_file, 'w') as f:
            f.write('test content')
        
        # Run scanner via CLI
        script_path = os.path.join(os.path.dirname(__file__), '..', 'scripts', 'scan_folder.py')
        cmd = [
            sys.executable, script_path,
            '--path', temp_dir,
            '--db', test_db,
            '--verbose'
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        # Check that it ran successfully
        assert result.returncode == 0
        assert 'Scan completed successfully' in result.stdout or 'SCAN COMPLETE' in result.stdout
    
    @pytest.mark.skipif(not hasattr(sys.modules.get('scripts.scan_folder', None), 'ENHANCED_DETECTION_AVAILABLE') or 
                       not getattr(sys.modules.get('scripts.scan_folder', None), 'ENHANCED_DETECTION_AVAILABLE', False),
                       reason="Enhanced detection not available")
    def test_cli_integration_enhanced(self, sample_files, temp_dir, test_db):
        """Test CLI integration with enhanced duplicate detection."""
        # Run scanner via CLI with enhanced detection
        script_path = os.path.join(os.path.dirname(__file__), '..', 'scripts', 'scan_folder.py')
        cmd = [
            sys.executable, script_path,
            '--path', temp_dir,
            '--db', test_db,
            '--use-enhanced',
            '--detection-mode', 'exact',
            '--verbose'
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        # Check that it ran successfully
        assert result.returncode == 0
        assert 'ENHANCED DUPLICATE DETECTION' in result.stdout
        assert 'Groups Found:' in result.stdout
    
    def test_cli_integration_with_filters(self, sample_files, temp_dir, test_db):
        """Test CLI integration with file filters."""
        # Run scanner via CLI with file type filter
        script_path = os.path.join(os.path.dirname(__file__), '..', 'scripts', 'scan_folder.py')
        cmd = [
            sys.executable, script_path,
            '--path', temp_dir,
            '--db', test_db,
            '--use-enhanced',
            '--detection-mode', 'exact',
            '--file-types', '.txt',
            '--min-file-size', '10',
            '--verbose'
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        # Check that it ran successfully
        assert result.returncode == 0
        assert 'File Types Filter: .txt' in result.stdout
        assert 'Size Filter: min: 10 bytes' in result.stdout
    
    def test_error_handling(self, scanner, temp_dir):
        """Test error handling in enhanced detection."""
        # Try to run enhanced detection without scanning first (no files in DB)
        results = scanner.detect_duplicates_enhanced(mode='exact')
        
        # Should handle gracefully
        if results:
            assert results.total_files_scanned == 0
            assert results.total_groups_found == 0
    
    def test_detection_mode_validation(self, scanner, sample_files, temp_dir):
        """Test detection mode validation."""
        # Scan files first
        scanner.scan_folder(temp_dir, recursive=True)
        
        # Test valid modes
        valid_modes = ['exact', 'similar', 'metadata', 'comprehensive']
        for mode in valid_modes:
            results = scanner.detect_duplicates_enhanced(mode=mode)
            if results:  # Only check if enhanced detection is available
                assert results.detection_mode.value == mode
        
        # Test invalid mode should raise ValueError or return None
        try:
            results = scanner.detect_duplicates_enhanced(mode='invalid_mode')
            # If it doesn't raise an exception, it should return None
            assert results is None
        except ValueError:
            # This is also acceptable
            pass
    
    def test_configuration_validation(self, scanner, sample_files, temp_dir):
        """Test configuration validation."""
        # Scan files first
        scanner.scan_folder(temp_dir, recursive=True)
        
        # Test with invalid configuration
        invalid_config = {
            'perceptual_threshold': 150.0,  # Invalid: > 100
            'min_confidence_threshold': -10.0  # Invalid: < 0
        }
        
        # Should handle invalid config gracefully
        results = scanner.detect_duplicates_enhanced(mode='exact', config=invalid_config)
        
        # Either should return None or use default config
        if results:
            # Should have used default or corrected values
            assert 0 <= results.config.perceptual_threshold <= 100
            assert 0 <= results.config.min_confidence_threshold <= 100


class TestScannerPerformance:
    """Performance tests for scanner integration."""
    
    @pytest.fixture
    def large_file_set(self, temp_dir):
        """Create a larger set of test files."""
        files = []
        
        # Create 50 files with some duplicates
        for i in range(50):
            file_path = os.path.join(temp_dir, f'file_{i:03d}.txt')
            
            # Create some duplicates by reusing content
            content_id = i % 10  # This will create 10 groups of 5 duplicates each
            content = f"Content for group {content_id}\n" * 100  # Make files larger
            
            with open(file_path, 'w') as f:
                f.write(content)
            
            files.append(file_path)
        
        return files
    
    @pytest.mark.skipif(not hasattr(sys.modules.get('scripts.scan_folder', None), 'ENHANCED_DETECTION_AVAILABLE') or 
                       not getattr(sys.modules.get('scripts.scan_folder', None), 'ENHANCED_DETECTION_AVAILABLE', False),
                       reason="Enhanced detection not available")
    def test_performance_with_many_files(self, scanner, large_file_set, temp_dir):
        """Test performance with a larger number of files."""
        # Scan files
        start_time = datetime.now()
        scanner.scan_folder(temp_dir, recursive=True)
        scan_time = (datetime.now() - start_time).total_seconds()
        
        # Should complete scanning in reasonable time (< 30 seconds for 50 files)
        assert scan_time < 30.0
        assert scanner.stats['processed_files'] == 50
        
        # Run enhanced detection
        start_time = datetime.now()
        results = scanner.detect_duplicates_enhanced(mode='exact')
        detection_time = (datetime.now() - start_time).total_seconds()
        
        if results:
            # Should complete detection in reasonable time
            assert detection_time < 10.0
            assert results.total_files_scanned == 50
            assert results.total_groups_found == 10  # Should find 10 groups of duplicates
            
            # Check performance metrics
            assert results.detection_time_ms > 0
            for algo_perf in results.algorithm_performance.values():
                assert algo_perf.get('files_per_second', 0) > 0
    
    def test_memory_usage(self, scanner, large_file_set, temp_dir):
        """Test that memory usage remains reasonable."""
        import psutil
        import os
        
        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        # Scan files
        scanner.scan_folder(temp_dir, recursive=True)
        
        # Run detection if available
        if hasattr(scanner, 'detect_duplicates_enhanced'):
            results = scanner.detect_duplicates_enhanced(mode='comprehensive')
        
        final_memory = process.memory_info().rss / 1024 / 1024  # MB
        memory_increase = final_memory - initial_memory
        
        # Memory increase should be reasonable (< 100MB for this test)
        assert memory_increase < 100.0, f"Memory increased by {memory_increase:.1f}MB"


if __name__ == '__main__':
    pytest.main([__file__, '-v'])