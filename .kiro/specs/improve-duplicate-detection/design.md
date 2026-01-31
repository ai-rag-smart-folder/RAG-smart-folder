# Design Document

## Overview

The current duplicate detection system has a solid foundation with SHA256 hashing and perceptual hashing capabilities, but lacks comprehensive integration and advanced detection algorithms. This design enhances the system to provide multi-layered duplicate detection with configurable sensitivity, detailed reporting, and improved accuracy through the combination of multiple detection methods.

## Architecture

The enhanced duplicate detection system will consist of several key components:

1. **Detection Engine**: Core logic for running multiple detection algorithms
2. **Algorithm Modules**: Individual detection methods (SHA256, perceptual, metadata)
3. **Configuration Manager**: Handles detection settings and thresholds
4. **Results Processor**: Consolidates and ranks detection results
5. **Reporting System**: Generates detailed duplicate reports with confidence scores

## Components and Interfaces

### Detection Engine

**Core Detection Service**:
```python
class DuplicateDetectionEngine:
    def __init__(self, config: DetectionConfig):
        self.config = config
        self.algorithms = []
        self.results_processor = ResultsProcessor()
    
    def detect_duplicates(self, mode: str = 'comprehensive') -> DetectionResults:
        """Run duplicate detection with specified mode"""
        
    def add_algorithm(self, algorithm: DetectionAlgorithm):
        """Add detection algorithm to the engine"""
        
    def get_detection_report(self) -> DetectionReport:
        """Generate comprehensive detection report"""
```

**Detection Modes**:
- `exact`: SHA256-based exact duplicate detection only
- `similar`: Perceptual hash-based similarity detection for images
- `metadata`: Metadata-based potential duplicate detection
- `comprehensive`: All methods combined with confidence scoring

### Algorithm Modules

**SHA256 Content Detection**:
```python
class SHA256Detector(DetectionAlgorithm):
    def detect(self, files: List[File]) -> List[DuplicateGroup]:
        """Find exact duplicates using SHA256 hash comparison"""
        # Groups files by identical SHA256 hashes
        # Confidence: 100% for matches
```

**Perceptual Hash Detection**:
```python
class PerceptualHashDetector(DetectionAlgorithm):
    def __init__(self, threshold: float = 80.0):
        self.threshold = threshold
    
    def detect(self, files: List[File]) -> List[DuplicateGroup]:
        """Find visually similar images using perceptual hashing"""
        # Compares perceptual hashes with configurable threshold
        # Confidence: Based on similarity percentage
```

**Metadata Comparison Detection**:
```python
class MetadataDetector(DetectionAlgorithm):
    def __init__(self, fields: List[str] = ['file_size', 'modified_at']):
        self.comparison_fields = fields
    
    def detect(self, files: List[File]) -> List[DuplicateGroup]:
        """Find potential duplicates using metadata comparison"""
        # Compares file size, timestamps, dimensions
        # Confidence: Lower, requires verification
```

**Advanced Similarity Detection**:
```python
class AdvancedSimilarityDetector(DetectionAlgorithm):
    def detect(self, files: List[File]) -> List[DuplicateGroup]:
        """Advanced similarity using multiple image features"""
        # Combines perceptual hash, color histograms, edge detection
        # Higher accuracy for complex similarity detection
```

### Configuration System

**Detection Configuration**:
```python
@dataclass
class DetectionConfig:
    # Perceptual hash settings
    perceptual_threshold: float = 80.0
    perceptual_hash_size: int = 16
    
    # Metadata comparison settings
    metadata_fields: List[str] = field(default_factory=lambda: ['file_size', 'modified_at'])
    size_tolerance: int = 0  # bytes
    time_tolerance: int = 60  # seconds
    
    # Advanced similarity settings
    use_color_histogram: bool = True
    use_edge_detection: bool = True
    feature_weight_perceptual: float = 0.6
    feature_weight_color: float = 0.3
    feature_weight_edge: float = 0.1
    
    # General settings
    min_confidence_threshold: float = 50.0
    max_results_per_group: int = 100
    enable_cross_algorithm_validation: bool = True
```

### Results Processing

**Duplicate Group Structure**:
```python
@dataclass
class DuplicateGroup:
    id: str
    detection_method: str
    confidence_score: float
    similarity_percentage: float
    files: List[DuplicateFile]
    metadata: Dict[str, Any]
    
@dataclass
class DuplicateFile:
    file_id: int
    file_path: str
    file_name: str
    file_size: int
    is_original: bool
    confidence_score: float
    detection_reasons: List[str]
```

**Results Consolidation**:
```python
class ResultsProcessor:
    def consolidate_results(self, algorithm_results: List[DetectionResults]) -> ConsolidatedResults:
        """Merge results from multiple algorithms"""
        # Remove duplicates between algorithms
        # Rank by confidence scores
        # Identify consensus matches
        
    def rank_duplicates(self, groups: List[DuplicateGroup]) -> List[DuplicateGroup]:
        """Rank duplicate groups by confidence and evidence"""
        
    def suggest_originals(self, group: DuplicateGroup) -> DuplicateFile:
        """Suggest which file to keep as original"""
        # Based on: earliest timestamp, largest size, best quality
```

## Data Models

### Enhanced Database Schema

**Duplicate Detection Results Table**:
```sql
CREATE TABLE IF NOT EXISTS detection_results (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT NOT NULL,
    detection_mode TEXT NOT NULL,
    total_files_scanned INTEGER,
    total_groups_found INTEGER,
    total_duplicates_found INTEGER,
    detection_time_ms INTEGER,
    config_json TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

**Enhanced Duplicate Groups Table**:
```sql
ALTER TABLE duplicate_groups ADD COLUMN detection_method TEXT;
ALTER TABLE duplicate_groups ADD COLUMN confidence_score REAL;
ALTER TABLE duplicate_groups ADD COLUMN session_id TEXT;
ALTER TABLE duplicate_groups ADD COLUMN metadata_json TEXT;
```

**Algorithm Performance Tracking**:
```sql
CREATE TABLE IF NOT EXISTS algorithm_performance (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    algorithm_name TEXT NOT NULL,
    files_processed INTEGER,
    execution_time_ms INTEGER,
    groups_found INTEGER,
    session_id TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

## Error Handling

### Detection Algorithm Failures

1. **SHA256 Computation Errors**: Log error, continue with other algorithms
2. **Perceptual Hash Failures**: Skip problematic images, process others
3. **Metadata Access Errors**: Use available metadata fields, skip missing ones
4. **Memory Limitations**: Process files in batches, implement streaming

### Configuration Validation

1. **Invalid Thresholds**: Use defaults, log warnings
2. **Missing Dependencies**: Disable affected algorithms, notify user
3. **Database Errors**: Graceful degradation, temporary storage

### Performance Optimization

1. **Large File Sets**: Implement pagination and batch processing
2. **Memory Management**: Stream processing for large images
3. **Database Optimization**: Use prepared statements, connection pooling
4. **Caching**: Cache computed hashes and metadata

## Testing Strategy

### Unit Tests

1. **Algorithm Testing**: Test each detection algorithm independently
2. **Configuration Validation**: Test various configuration scenarios
3. **Results Processing**: Test consolidation and ranking logic
4. **Error Handling**: Test failure scenarios and recovery

### Integration Tests

1. **End-to-End Detection**: Test complete detection workflows
2. **Multi-Algorithm Integration**: Test algorithm combination and consolidation
3. **Database Integration**: Test result storage and retrieval
4. **Performance Testing**: Test with large file sets

### Manual Testing Scenarios

1. **Exact Duplicates**: Files with identical content, different names
2. **Similar Images**: Images with minor modifications or different formats
3. **False Positives**: Files that appear similar but are different
4. **Edge Cases**: Corrupted files, permission issues, large files

## Implementation Approach

### Phase 1: Core Detection Engine
- Implement base detection engine and algorithm interface
- Create SHA256 and perceptual hash detectors
- Add configuration management system
- Implement basic results processing

### Phase 2: Advanced Algorithms
- Add metadata comparison detector
- Implement advanced similarity detection
- Add cross-algorithm validation
- Enhance results consolidation

### Phase 3: API Integration
- Update existing `/duplicates` endpoint
- Add new detection mode endpoints
- Implement configuration API
- Add detailed reporting endpoints

### Phase 4: Performance and Optimization
- Implement batch processing for large datasets
- Add caching for computed hashes
- Optimize database queries and indexes
- Add progress reporting for long-running operations

### Phase 5: User Interface Enhancements
- Update desktop app to support new detection modes
- Add configuration UI for detection settings
- Implement detailed duplicate reports display
- Add batch operations for duplicate management

## API Design

### Enhanced Duplicate Detection Endpoints

**POST /api/v1/duplicates/detect**:
```json
{
  "mode": "comprehensive",
  "config": {
    "perceptual_threshold": 85.0,
    "metadata_fields": ["file_size", "modified_at"],
    "min_confidence": 60.0
  },
  "file_filters": {
    "file_types": [".jpg", ".png", ".pdf"],
    "min_size": 1024,
    "max_size": 104857600
  }
}
```

**GET /api/v1/duplicates/results/{session_id}**:
```json
{
  "session_id": "uuid",
  "detection_mode": "comprehensive",
  "summary": {
    "total_files": 1000,
    "total_groups": 25,
    "total_duplicates": 75,
    "detection_time_ms": 5000
  },
  "groups": [
    {
      "id": "group_1",
      "detection_method": "sha256",
      "confidence_score": 100.0,
      "files": [...],
      "suggested_action": "keep_original"
    }
  ]
}
```

**POST /api/v1/duplicates/config**:
```json
{
  "perceptual_threshold": 80.0,
  "metadata_fields": ["file_size", "modified_at", "width", "height"],
  "advanced_similarity": {
    "enabled": true,
    "color_histogram_weight": 0.3,
    "edge_detection_weight": 0.1
  }
}
```

This design provides a comprehensive, configurable, and extensible duplicate detection system that addresses the limitations of filename-based comparison and leverages multiple sophisticated algorithms for accurate duplicate identification.