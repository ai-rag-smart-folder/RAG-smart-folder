# Scanner Test Suite

This directory contains a comprehensive test suite for the RAG Smart Folder file scanner functionality. The tests validate the scanner fixes implemented to address the file scanning issues.

## Test Structure

### Test Files

- **`test_simple.py`** - Basic functionality tests and setup verification
- **`test_database_operations.py`** - Database operations and schema migration tests
- **`test_file_processing.py`** - File processing and metadata extraction tests
- **`test_integration.py`** - End-to-end scanning scenarios and integration tests
- **`test_error_handling.py`** - Error handling and recovery mechanism tests
- **`test_file_types.py`** - File type handling and folder structure tests

### Test Categories

#### Unit Tests
- Database operations (schema migration, column handling)
- File metadata extraction
- Hash computation (SHA256, perceptual)
- Image processing (dimensions, EXIF data)
- Error logging and reporting

#### Integration Tests
- Complete folder scanning workflows
- Mixed file type processing
- Duplicate detection
- Similarity detection
- Statistics reporting

#### Error Handling Tests
- Database connection failures
- File system permission errors
- Corrupted file handling
- Missing dependency scenarios
- Recovery mechanisms

## Requirements

### Required Dependencies
```bash
pytest>=7.0.0
pillow>=9.0.0
```

### Optional Dependencies (for full test coverage)
```bash
pytest-cov>=4.0.0
imagehash>=4.3.0
python-magic>=0.4.27
exifread>=3.0.0
numpy>=1.21.0
scikit-learn>=1.0.0
```

## Installation

Install test dependencies:
```bash
pip install -r requirements.txt
```

Or install minimal requirements:
```bash
pip install pytest pillow
```

## Running Tests

### Quick Test Run
```bash
# Run all tests
python3 -m pytest backend/tests/ -v

# Run specific test category
python3 -m pytest backend/tests/test_database_operations.py -v
python3 -m pytest backend/tests/test_integration.py -v
```

### Using Test Runner
```bash
# Run all tests with the custom test runner
python3 backend/tests/run_tests.py

# Run specific test types
python3 backend/tests/run_tests.py --type unit
python3 backend/tests/run_tests.py --type integration

# Run with coverage reporting
python3 backend/tests/run_tests.py --coverage

# Check dependencies
python3 backend/tests/run_tests.py --check-deps
```

### Advanced Options
```bash
# Run specific test
python3 -m pytest backend/tests/test_database_operations.py::TestDatabaseMigration::test_migrate_database_success -v

# Run with coverage
python3 -m pytest backend/tests/ --cov=backend/scripts --cov-report=html

# Run tests and stop on first failure
python3 -m pytest backend/tests/ -x

# Run tests in parallel (if pytest-xdist is installed)
python3 -m pytest backend/tests/ -n auto
```

## Test Coverage

The test suite covers the following requirements from the specification:

### Requirement 1.1 - File Processing Statistics
- ✅ Accurate file count reporting
- ✅ Processing statistics tracking
- ✅ Progress reporting during scanning

### Requirement 1.2 - Database Operations
- ✅ Successful file metadata insertion
- ✅ Schema compatibility handling
- ✅ Column existence checking

### Requirement 1.3 - Statistics Reporting
- ✅ Comprehensive scan statistics
- ✅ Error count reporting
- ✅ Processing summary generation

### Requirement 1.4 - Error Handling
- ✅ Detailed error logging
- ✅ Database error recovery
- ✅ File access error handling

### Requirement 2.1 & 2.2 - Database Schema
- ✅ Width and height column support
- ✅ Schema migration functionality
- ✅ Backward compatibility

### Requirement 2.3 - Database Insertion
- ✅ Graceful handling of missing columns
- ✅ Fallback insertion mechanisms
- ✅ Error recovery during insertion

### Requirement 3.1, 3.2, 3.3 - Error Reporting
- ✅ Specific error type logging
- ✅ Clear error messages
- ✅ Error categorization and summary

### Requirement 4.1, 4.2, 4.3, 4.4 - File Type Handling
- ✅ Image file processing (dimensions, hashes)
- ✅ Non-image file handling
- ✅ Unsupported file type handling
- ✅ Robust file processing without unnecessary skipping

## Test Fixtures

The test suite uses several fixtures for consistent test environments:

- **`temp_db`** - Temporary database with full schema
- **`temp_db_no_columns`** - Database without width/height columns (for migration testing)
- **`test_files_dir`** - Directory with various text files
- **`test_images_dir`** - Directory with test images
- **`mixed_files_dir`** - Directory with mixed file types
- **`sample_file_metadata`** - Sample metadata for testing

## Mocking and Isolation

Tests use mocking to:
- Simulate missing dependencies
- Test error conditions
- Isolate components for unit testing
- Speed up tests by avoiding real file I/O where appropriate

## Performance Considerations

- Tests use temporary files and databases
- Large file tests are limited in size to avoid slow test runs
- Optional dependencies are gracefully handled
- Tests clean up resources automatically

## Troubleshooting

### Common Issues

1. **Missing Dependencies**
   ```bash
   # Check what's missing
   python3 backend/tests/run_tests.py --check-deps
   
   # Install missing packages
   pip install pillow imagehash python-magic
   ```

2. **Permission Errors**
   - Ensure test directories are writable
   - Some permission tests may be skipped on certain systems

3. **Database Locked Errors**
   - Tests use temporary databases to avoid conflicts
   - Ensure no other processes are using test databases

4. **Import Errors**
   - Verify Python path includes the scripts directory
   - Check that all required modules are installed

### Debug Mode

Run tests with verbose output and no capture:
```bash
python3 -m pytest backend/tests/ -v -s --tb=long
```

## Contributing

When adding new tests:

1. Follow the existing test structure and naming conventions
2. Use appropriate fixtures for test data
3. Include both positive and negative test cases
4. Test error conditions and edge cases
5. Update this README if adding new test categories

## Test Results

Expected test results:
- All tests should pass with required dependencies
- Some tests may be skipped if optional dependencies are missing
- Tests should complete in under 30 seconds on modern hardware
- Coverage should be >90% for core scanner functionality