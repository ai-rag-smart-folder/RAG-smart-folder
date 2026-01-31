# Design Document

## Overview

The duplicate detection system has a critical disconnect between the backend detection results and the frontend display. The scan process successfully detects duplicates (showing "13 Duplicates" in the scan summary), but the frontend "Duplicates" tab displays "No duplicates found". This issue stems from a mismatch between the data structure expected by the frontend and the data structure returned by the backend API.

## Architecture

The fix involves three main components:

1. **Backend API Response Standardization**: Ensure the `/duplicates` endpoint returns data in the format expected by the frontend
2. **Frontend Data Processing**: Update the frontend to properly handle the backend response structure
3. **Session Management**: Implement proper session tracking to link scan results with duplicate display

## Components and Interfaces

### Current Problem Analysis

**Backend Response Structure** (from `/duplicates` endpoint):
```json
{
  "session_id": "basic_20241027_123456",
  "detection_mode": "basic",
  "summary": {
    "total_files_scanned": 32,
    "total_groups_found": 13,
    "total_duplicates_found": 30
  },
  "duplicate_groups": [
    {
      "id": "group_1_abc12345",
      "detection_method": "sha256",
      "confidence_score": 100.0,
      "file_count": 3,
      "files": [
        {
          "id": 1,
          "path": "/app/host_home/Pictures/image1.jpg",
          "name": "image1.jpg",
          "size": 1024000,
          "is_original": true
        }
      ]
    }
  ]
}
```

**Frontend Expected Structure** (in `displayDuplicatesList` function):
```javascript
// Frontend expects: duplicatesData.duplicates
// But backend returns: duplicatesData.duplicate_groups
```

### Backend API Fixes

**Updated `/duplicates` Endpoint Response**:
```python
@app.get("/duplicates")
async def find_duplicates():
    # ... existing logic ...
    
    return {
        "session_id": session_id,
        "detection_mode": "basic",
        "summary": {
            "total_files_scanned": total_files,
            "total_groups_found": len(duplicate_groups),
            "total_duplicates_found": total_duplicates
        },
        "duplicates": duplicate_groups,  # Frontend expects this key
        "duplicate_groups": duplicate_groups,  # Keep for backward compatibility
        "total_duplicate_groups": len(duplicate_groups)  # Frontend expects this
    }
```

**Enhanced Duplicate Group Structure**:
```python
duplicate_group = {
    "id": f"group_{i+1}_{sha256[:8]}",
    "detection_method": "sha256",
    "confidence_score": 100.0,
    "similarity_percentage": 100.0,
    "count": file_count,  # Frontend expects this key
    "file_count": file_count,  # Keep for consistency
    "total_size": sum(f["size"] for f in group_files if f["size"]),
    "files": group_files
}
```

### Frontend Display Fixes

**Updated `displayDuplicatesList` Function**:
```javascript
displayDuplicatesList(duplicatesData) {
    // Handle both old and new response formats
    const duplicates = duplicatesData.duplicates || duplicatesData.duplicate_groups || [];
    
    const list = document.getElementById('duplicatesList');
    list.innerHTML = duplicates.length === 0 ? 
        '<div class="file-item">No duplicates found</div>' : '';

    duplicates.forEach((group, index) => {
        const groupDiv = document.createElement('div');
        groupDiv.className = 'duplicate-group';

        const header = document.createElement('div');
        header.className = 'duplicate-header';
        // Handle both count and file_count properties
        const fileCount = group.count || group.file_count || group.files?.length || 0;
        header.textContent = `Group ${index + 1} (${fileCount} files)`;

        // ... rest of the display logic
    });
}
```

### Session Management Integration

**Enhanced Scan-to-Display Flow**:
```javascript
async startDuplicateScan() {
    // ... existing scan logic ...
    
    if (result.status === 'success') {
        // Store session ID for later retrieval
        this.lastScanSessionId = result.session_id;
        
        // Load results immediately after scan
        await this.loadResults();
    }
}

async loadResults() {
    try {
        // If we have a session ID, use enhanced detection service
        let duplicatesResponse;
        if (this.lastScanSessionId) {
            duplicatesResponse = await fetch(
                `${this.apiBase}/api/v1/duplicates/results/${this.lastScanSessionId}`
            );
        } else {
            // Fallback to basic duplicates endpoint
            duplicatesResponse = await fetch(`${this.apiBase}/duplicates`);
        }
        
        const duplicatesData = await duplicatesResponse.json();
        // ... rest of loading logic
    } catch (error) {
        this.log(`Failed to load results: ${error.message}`, 'error');
    }
}
```

## Data Models

### Standardized Duplicate Response Format

```typescript
interface DuplicateResponse {
  session_id: string;
  detection_mode: string;
  summary: {
    total_files_scanned: number;
    total_groups_found: number;
    total_duplicates_found: number;
    success_rate?: number;
    duplicate_percentage?: number;
  };
  duplicates: DuplicateGroup[];  // Primary key for frontend
  duplicate_groups?: DuplicateGroup[];  // Backward compatibility
  total_duplicate_groups: number;  // Frontend expects this
  errors?: string[];
}

interface DuplicateGroup {
  id: string;
  detection_method: string;
  confidence_score: number;
  similarity_percentage?: number;
  count: number;  // Primary key for frontend
  file_count?: number;  // Backward compatibility
  total_size?: number;
  files: DuplicateFile[];
}

interface DuplicateFile {
  id: number;
  path: string;
  name: string;
  size: number;
  type?: string;
  is_original: boolean;
  confidence_score?: number;
  detection_reasons?: string[];
}
```

### Database Integration

**Enhanced Duplicate Retrieval Query**:
```sql
-- Get duplicate groups with file details
SELECT 
    dg.id as group_id,
    dg.group_hash,
    dg.detection_method,
    dg.confidence_score,
    dg.similarity_score,
    COUNT(df.file_id) as file_count,
    SUM(f.file_size) as total_size
FROM duplicate_groups dg
JOIN duplicate_files df ON dg.id = df.group_id
JOIN files f ON df.file_id = f.id
WHERE dg.session_id = ? OR dg.session_id IS NULL
GROUP BY dg.id
HAVING COUNT(df.file_id) > 1
ORDER BY dg.confidence_score DESC;
```

## Error Handling

### Backend Error Handling

1. **Empty Results**: Return proper empty structure instead of null/undefined
2. **Database Errors**: Graceful fallback to basic SHA256 grouping
3. **Session Not Found**: Fall back to latest available results

```python
def get_duplicates_with_fallback(session_id: Optional[str] = None):
    try:
        if session_id:
            results = get_detection_results(session_id)
            if results:
                return format_duplicate_response(results)
        
        # Fallback to basic duplicate detection
        return find_basic_duplicates()
    except Exception as e:
        logger.error(f"Error getting duplicates: {e}")
        return {
            "duplicates": [],
            "total_duplicate_groups": 0,
            "summary": {"total_files_scanned": 0, "total_groups_found": 0},
            "errors": [str(e)]
        }
```

### Frontend Error Handling

1. **API Failures**: Show meaningful error messages
2. **Empty Responses**: Display "No duplicates found" appropriately
3. **Data Format Issues**: Handle both old and new response formats

```javascript
async loadDuplicates() {
    try {
        const response = await fetch(`${this.apiBase}/duplicates`);
        
        if (!response.ok) {
            throw new Error(`API error: ${response.status}`);
        }
        
        const data = await response.json();
        
        // Validate response structure
        if (!data || typeof data !== 'object') {
            throw new Error('Invalid response format');
        }
        
        // Handle both response formats
        const duplicates = data.duplicates || data.duplicate_groups || [];
        this.displayDuplicatesList({ duplicates, ...data });
        
    } catch (error) {
        this.log(`Failed to load duplicates: ${error.message}`, 'error');
        this.displayDuplicatesList({ duplicates: [] });
    }
}
```

## Testing Strategy

### Unit Tests

1. **Backend Response Format**: Test that `/duplicates` endpoint returns expected structure
2. **Frontend Data Processing**: Test duplicate display with various data formats
3. **Error Scenarios**: Test handling of empty results and API failures

### Integration Tests

1. **End-to-End Flow**: Test complete scan-to-display workflow
2. **Session Management**: Test session tracking and result retrieval
3. **Data Consistency**: Verify scan results match display results

### Manual Testing Scenarios

1. **Successful Scan**: Scan folder with known duplicates, verify display
2. **Empty Results**: Scan folder with no duplicates, verify "No duplicates found"
3. **API Failures**: Test with backend down, verify error handling
4. **Mixed File Types**: Test with images and non-images

## Implementation Approach

### Phase 1: Backend API Standardization
- Update `/duplicates` endpoint response format
- Ensure backward compatibility with existing clients
- Add proper error handling and empty result handling

### Phase 2: Frontend Display Fixes
- Update `displayDuplicatesList` to handle new response format
- Add fallback handling for old response format
- Improve error display and user feedback

### Phase 3: Session Management
- Implement session tracking in scan workflow
- Add enhanced duplicate retrieval using session IDs
- Integrate with existing duplicate detection service

### Phase 4: Testing and Validation
- Comprehensive testing of scan-to-display flow
- Performance testing with large duplicate sets
- User experience validation and refinement

## API Design

### Updated Duplicate Detection Endpoints

**GET /duplicates** (Enhanced):
```json
{
  "session_id": "scan_20241027_123456",
  "detection_mode": "basic",
  "summary": {
    "total_files_scanned": 32,
    "total_groups_found": 13,
    "total_duplicates_found": 30,
    "success_rate": 97.0,
    "duplicate_percentage": 93.75
  },
  "duplicates": [
    {
      "id": "group_1_abc12345",
      "detection_method": "sha256",
      "confidence_score": 100.0,
      "count": 3,
      "total_size": 3072000,
      "files": [
        {
          "id": 1,
          "path": "/Users/shankaraswal/Pictures/image1.jpg",
          "name": "image1.jpg",
          "size": 1024000,
          "type": ".jpg",
          "is_original": true,
          "detection_reasons": ["sha256_match", "smallest_file"]
        }
      ]
    }
  ],
  "total_duplicate_groups": 13,
  "errors": []
}
```

**POST /scan** (Enhanced Response):
```json
{
  "status": "success",
  "message": "Folder scanned successfully",
  "session_id": "scan_20241027_123456",
  "statistics": {
    "total_files": 32,
    "processed_files": 31,
    "duplicate_groups_found": 13,
    "total_duplicates": 30
  },
  "folder_path": "/Users/shankaraswal/Pictures",
  "scan_mode": "duplicates"
}
```

This design addresses the core disconnect between backend detection and frontend display by standardizing the API response format and ensuring the frontend can properly process and display the duplicate results.