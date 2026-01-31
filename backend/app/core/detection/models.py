"""
Data models for duplicate detection system.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from datetime import datetime
from enum import Enum


class DetectionMode(Enum):
    """Detection modes supported by the engine."""
    EXACT = "exact"
    SIMILAR = "similar"
    METADATA = "metadata"
    COMPREHENSIVE = "comprehensive"


class DetectionMethod(Enum):
    """Detection methods used by algorithms."""
    SHA256 = "sha256"
    PERCEPTUAL_HASH = "perceptual_hash"
    METADATA = "metadata"
    ADVANCED_SIMILARITY = "advanced_similarity"


@dataclass
class DetectionConfig:
    """Configuration for duplicate detection algorithms."""
    
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
    
    def validate(self) -> List[str]:
        """Validate configuration and return list of errors."""
        errors = []
        
        if not 0 <= self.perceptual_threshold <= 100:
            errors.append("perceptual_threshold must be between 0 and 100")
            
        if self.perceptual_hash_size not in [8, 16, 32]:
            errors.append("perceptual_hash_size must be 8, 16, or 32")
            
        if self.size_tolerance < 0:
            errors.append("size_tolerance must be non-negative")
            
        if self.time_tolerance < 0:
            errors.append("time_tolerance must be non-negative")
            
        if not 0 <= self.min_confidence_threshold <= 100:
            errors.append("min_confidence_threshold must be between 0 and 100")
            
        if self.max_results_per_group <= 0:
            errors.append("max_results_per_group must be positive")
            
        # Validate feature weights sum to 1.0
        total_weight = (self.feature_weight_perceptual + 
                       self.feature_weight_color + 
                       self.feature_weight_edge)
        if abs(total_weight - 1.0) > 0.01:
            errors.append("feature weights must sum to 1.0")
            
        return errors


@dataclass
class DuplicateFile:
    """Represents a file in a duplicate group."""
    
    file_id: int
    file_path: str
    file_name: str
    file_size: int
    sha256: Optional[str] = None
    perceptual_hash: Optional[str] = None
    file_type: Optional[str] = None
    mime_type: Optional[str] = None
    width: Optional[int] = None
    height: Optional[int] = None
    created_at: Optional[datetime] = None
    modified_at: Optional[datetime] = None
    is_original: bool = False
    confidence_score: float = 0.0
    detection_reasons: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class DuplicateGroup:
    """Represents a group of duplicate files."""
    
    id: str
    detection_method: DetectionMethod
    confidence_score: float
    similarity_percentage: float
    files: List[DuplicateFile]
    created_at: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        """Post-initialization validation."""
        if not self.files:
            raise ValueError("DuplicateGroup must contain at least one file")
        if len(self.files) < 2:
            raise ValueError("DuplicateGroup must contain at least two files")
    
    @property
    def file_count(self) -> int:
        """Number of files in the group."""
        return len(self.files)
    
    @property
    def total_size(self) -> int:
        """Total size of all files in the group."""
        return sum(f.file_size for f in self.files)
    
    @property
    def suggested_original(self) -> Optional[DuplicateFile]:
        """Get the suggested original file."""
        originals = [f for f in self.files if f.is_original]
        return originals[0] if originals else None


@dataclass
class DetectionResults:
    """Results from a duplicate detection run."""
    
    session_id: str
    detection_mode: DetectionMode
    groups: List[DuplicateGroup]
    total_files_scanned: int
    total_groups_found: int
    total_duplicates_found: int
    detection_time_ms: int
    config: DetectionConfig
    created_at: datetime = field(default_factory=datetime.now)
    algorithm_performance: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    errors: List[str] = field(default_factory=list)
    
    @property
    def success_rate(self) -> float:
        """Calculate success rate based on files scanned vs errors."""
        if self.total_files_scanned == 0:
            return 0.0
        error_count = len(self.errors)
        return max(0.0, (self.total_files_scanned - error_count) / self.total_files_scanned * 100)
    
    @property
    def duplicate_percentage(self) -> float:
        """Percentage of files that are duplicates."""
        if self.total_files_scanned == 0:
            return 0.0
        return self.total_duplicates_found / self.total_files_scanned * 100


@dataclass
class AlgorithmPerformance:
    """Performance metrics for a detection algorithm."""
    
    algorithm_name: str
    files_processed: int
    execution_time_ms: int
    groups_found: int
    errors_encountered: int
    memory_usage_mb: Optional[float] = None
    
    @property
    def files_per_second(self) -> float:
        """Calculate processing rate."""
        if self.execution_time_ms == 0:
            return 0.0
        return self.files_processed / (self.execution_time_ms / 1000.0)
    
    @property
    def error_rate(self) -> float:
        """Calculate error rate percentage."""
        if self.files_processed == 0:
            return 0.0
        return self.errors_encountered / self.files_processed * 100