"""
Simple test to verify test suite setup.
"""

import pytest
import os
import sys

# Add the scripts directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'scripts'))

from scan_folder import FileScanner


def test_scanner_initialization():
    """Test that scanner can be initialized."""
    scanner = FileScanner(':memory:')
    assert scanner is not None
    assert scanner.db_path == ':memory:'
    assert scanner.stats['total_files'] == 0


def test_scanner_stats_initialization():
    """Test that scanner statistics are properly initialized."""
    scanner = FileScanner(':memory:')
    
    expected_stats = [
        'total_files', 'processed_files', 'skipped_files', 
        'duplicates_found', 'errors'
    ]
    
    for stat in expected_stats:
        assert stat in scanner.stats
        assert isinstance(scanner.stats[stat], int)


def test_error_logging():
    """Test basic error logging functionality."""
    scanner = FileScanner(':memory:')
    
    initial_errors = scanner.stats['errors']
    scanner._log_error('TEST_ERROR', '/test/path', 'Test message')
    
    assert scanner.stats['errors'] == initial_errors + 1
    assert len(scanner.error_details) == 1
    
    error = scanner.error_details[0]
    assert error['error_type'] == 'TEST_ERROR'
    assert error['file_path'] == '/test/path'
    assert error['error_message'] == 'Test message'


def test_dependency_checking():
    """Test dependency availability checking."""
    scanner = FileScanner(':memory:')
    
    # Test with a dependency that should exist (sqlite3 is built-in)
    # Note: We can't test specific optional dependencies as they may not be installed
    assert hasattr(scanner, '_is_dependency_available')
    
    # Test with non-existent dependency
    result = scanner._is_dependency_available('nonexistent_dependency')
    assert result is False