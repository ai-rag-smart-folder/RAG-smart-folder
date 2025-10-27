# Design Document

## Overview

The file scanning issue is caused by a mismatch between the database schema and the scanner code. The scanner attempts to insert `width` and `height` columns that don't exist in the database, causing silent failures. Additionally, error handling needs improvement to provide better visibility into scanning issues.

## Architecture

The fix involves three main components:

1. **Database Schema Update**: Add missing columns to support image metadata
2. **Scanner Error Handling**: Improve error reporting and logging
3. **File Processing Logic**: Ensure robust handling of different file types

## Components and Interfaces

### Database Schema Changes

**Modified Files Table**:
```sql
ALTER TABLE files ADD COLUMN width INTEGER;
ALTER TABLE files ADD COLUMN height INTEGER;
```

**Schema Migration Strategy**:
- Check if columns exist before adding them
- Ensure backward compatibility with existing data
- Update the main schema.sql file for new installations

### Scanner Improvements

**FileScanner Class Enhancements**:
- Add column existence checking before insertion
- Improve error logging with specific details
- Add validation for database operations
- Better handling of missing dependencies

**Error Handling Strategy**:
- Catch and log specific database errors
- Provide detailed error messages for debugging
- Continue processing other files when individual files fail
- Report comprehensive statistics at the end

### File Processing Logic

**Robust File Handling**:
- Validate file existence before processing
- Handle permission errors gracefully
- Skip system/hidden files with clear logging
- Process files in batches for better performance

## Data Models

### Updated Files Table Schema

```sql
CREATE TABLE IF NOT EXISTS files (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    file_path TEXT NOT NULL,
    file_name TEXT NOT NULL,
    file_size INTEGER,
    sha256 TEXT,
    perceptual_hash TEXT,
    file_type TEXT(50),
    mime_type TEXT(100),
    width INTEGER,           -- NEW: Image width
    height INTEGER,          -- NEW: Image height
    created_at TIMESTAMP,
    modified_at TIMESTAMP,
    metadata_json TEXT,
    added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### Scanner Statistics Model

```python
{
    'total_files': int,      # Total files found
    'processed_files': int,  # Successfully processed
    'skipped_files': int,    # Skipped (hidden, system, etc.)
    'duplicates_found': int, # Duplicate files detected
    'errors': int,           # Processing errors
    'error_details': []      # List of specific errors
}
```

## Error Handling

### Database Error Handling

1. **Column Missing Errors**: Detect missing columns and add them automatically
2. **Insertion Errors**: Log specific SQL errors with file context
3. **Connection Errors**: Provide clear database connection status

### File Processing Errors

1. **Permission Errors**: Log and continue with other files
2. **Corrupted Files**: Handle gracefully without stopping scan
3. **Missing Dependencies**: Warn about missing optional features

### User Feedback

1. **Progress Reporting**: Show real-time processing status
2. **Error Summary**: Provide detailed error report at completion
3. **Recommendations**: Suggest fixes for common issues

## Testing Strategy

### Unit Tests

1. **Database Operations**: Test schema updates and insertions
2. **File Processing**: Test various file types and edge cases
3. **Error Handling**: Test error scenarios and recovery

### Integration Tests

1. **End-to-End Scanning**: Test complete folder scanning workflow
2. **Database Migration**: Test schema updates on existing databases
3. **Error Recovery**: Test system behavior under various failure conditions

### Manual Testing

1. **Different File Types**: Test with images, documents, and other files
2. **Large Folders**: Test performance with many files
3. **Permission Issues**: Test with restricted access folders

## Implementation Approach

### Phase 1: Database Schema Fix
- Add migration script to update existing databases
- Update schema.sql for new installations
- Test schema changes with existing data

### Phase 2: Scanner Improvements
- Add column existence checking
- Improve error logging and reporting
- Add validation for all database operations

### Phase 3: Enhanced File Processing
- Improve file type detection and handling
- Add better progress reporting
- Optimize performance for large folders

### Phase 4: Testing and Validation
- Comprehensive testing with various scenarios
- Performance optimization
- User experience improvements