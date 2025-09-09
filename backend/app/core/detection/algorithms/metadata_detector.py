"""
Metadata-based duplicate detection algorithm.
"""

import uuid
from typing import List, Dict, Set, Optional, Any, Tuple
from collections import defaultdict
from datetime import datetime, timedelta
import logging

from ..algorithms import DetectionAlgorithm
from ..models import DuplicateGroup, DuplicateFile, DetectionMethod, DetectionConfig


class MetadataDetector(DetectionAlgorithm):
    """Detects potential duplicates using file metadata comparison."""
    
    def __init__(self, config: DetectionConfig, logger: Optional[logging.Logger] = None):
        super().__init__(config, logger)
        self.algorithm_name = "MetadataDetector"
        self.comparison_fields = config.metadata_fields
        self.size_tolerance = config.size_tolerance
        self.time_tolerance = config.time_tolerance
    
    def detect(self, files: List[DuplicateFile]) -> List[DuplicateGroup]:
        """
        Detect potential duplicates using metadata comparison.
        
        Args:
            files: List of files to analyze
            
        Returns:
            List of duplicate groups with similar metadata
        """
        if not files:
            return []
        
        if len(files) < 2:
            self.logger.info(f"MetadataDetector: Need at least 2 files, got {len(files)}")
            return []
        
        # Group files by metadata similarity
        metadata_groups = self._group_by_metadata_similarity(files)
        
        # Convert to duplicate groups
        duplicate_groups = []
        for group_files in metadata_groups:
            if len(group_files) >= 2:
                group = self._create_metadata_group(group_files)
                duplicate_groups.append(group)
        
        self.logger.info(f"MetadataDetector: Found {len(duplicate_groups)} potential duplicate groups "
                        f"from {len(files)} files")
        
        return duplicate_groups
    
    def get_algorithm_name(self) -> str:
        """Return the name of this algorithm."""
        return self.algorithm_name
    
    def get_supported_file_types(self) -> List[str]:
        """Return list of supported file extensions (all types for metadata)."""
        return []  # Empty list means all file types are supported
    
    def can_process_file(self, file: DuplicateFile) -> bool:
        """
        Check if this algorithm can process the given file.
        Metadata detector can process any file with relevant metadata.
        
        Args:
            file: File to check
            
        Returns:
            True if file has processable metadata
        """
        # Check if file has any of the required metadata fields
        for field in self.comparison_fields:
            if hasattr(file, field) and getattr(file, field) is not None:
                return True
        return False
    
    def _group_by_metadata_similarity(self, files: List[DuplicateFile]) -> List[List[DuplicateFile]]:
        """Group files by metadata similarity."""
        groups = []
        processed_files = set()
        
        for i, file1 in enumerate(files):
            if file1.file_id in processed_files:
                continue
            
            # Start a new group with this file
            similar_files = [file1]
            
            # Find files with similar metadata
            for j, file2 in enumerate(files[i+1:], i+1):
                if file2.file_id in processed_files:
                    continue
                
                if self._are_metadata_similar(file1, file2):
                    similar_files.append(file2)
                    processed_files.add(file2.file_id)
            
            # Add group if it has multiple files
            if len(similar_files) > 1:
                groups.append(similar_files)
                processed_files.add(file1.file_id)
        
        return groups
    
    def _are_metadata_similar(self, file1: DuplicateFile, file2: DuplicateFile) -> bool:
        """
        Check if two files have similar metadata.
        
        Args:
            file1: First file to compare
            file2: Second file to compare
            
        Returns:
            True if files have similar metadata
        """
        similarity_score = 0
        total_comparisons = 0
        
        for field in self.comparison_fields:
            value1 = getattr(file1, field, None)
            value2 = getattr(file2, field, None)
            
            # Skip if either file doesn't have this field
            if value1 is None or value2 is None:
                continue
            
            total_comparisons += 1
            
            if self._compare_field_values(field, value1, value2):
                similarity_score += 1
        
        # Require at least one comparison and majority similarity
        if total_comparisons == 0:
            return False
        
        similarity_ratio = similarity_score / total_comparisons
        return similarity_ratio >= 0.5  # At least 50% of fields must match
    
    def _compare_field_values(self, field: str, value1: Any, value2: Any) -> bool:
        """
        Compare two field values with appropriate tolerance.
        
        Args:
            field: Name of the field being compared
            value1: First value
            value2: Second value
            
        Returns:
            True if values are considered similar
        """
        if field == 'file_size':
            return self._compare_sizes(value1, value2)
        elif field in ['created_at', 'modified_at']:
            return self._compare_timestamps(value1, value2)
        elif field in ['width', 'height']:
            return self._compare_dimensions(value1, value2)
        else:
            # Default exact comparison for other fields
            return value1 == value2
    
    def _compare_sizes(self, size1: int, size2: int) -> bool:
        """Compare file sizes with tolerance."""
        if size1 is None or size2 is None:
            return False
        return abs(size1 - size2) <= self.size_tolerance
    
    def _compare_timestamps(self, time1: datetime, time2: datetime) -> bool:
        """Compare timestamps with tolerance."""
        if time1 is None or time2 is None:
            return False
        
        # Convert to datetime if needed
        if isinstance(time1, str):
            try:
                time1 = datetime.fromisoformat(time1.replace('Z', '+00:00'))
            except:
                return False
        
        if isinstance(time2, str):
            try:
                time2 = datetime.fromisoformat(time2.replace('Z', '+00:00'))
            except:
                return False
        
        time_diff = abs((time1 - time2).total_seconds())
        return time_diff <= self.time_tolerance
    
    def _compare_dimensions(self, dim1: int, dim2: int) -> bool:
        """Compare image dimensions (exact match for now)."""
        if dim1 is None or dim2 is None:
            return False
        return dim1 == dim2
    
    def _create_metadata_group(self, files: List[DuplicateFile]) -> DuplicateGroup:
        """Create a duplicate group from files with similar metadata."""
        group_id = f"metadata_{uuid.uuid4().hex[:8]}"
        
        # Calculate confidence based on metadata similarity strength
        confidence_score = self._calculate_group_confidence(files)
        
        # Set confidence scores and detection reasons for files
        for file in files:
            file.confidence_score = confidence_score
            file.detection_reasons.append("similar_metadata")
            
            # Add specific reasons based on matching fields
            matching_fields = self._get_matching_fields(file, files[0] if file != files[0] else files[1])
            for field in matching_fields:
                file.detection_reasons.append(f"matching_{field}")
        
        # Analyze the metadata patterns
        metadata_analysis = self._analyze_group_metadata(files)
        
        group = DuplicateGroup(
            id=group_id,
            detection_method=DetectionMethod.METADATA,
            confidence_score=confidence_score,
            similarity_percentage=confidence_score,  # Use same value for metadata
            files=files,
            metadata={
                'detection_algorithm': self.algorithm_name,
                'comparison_fields': self.comparison_fields,
                'size_tolerance': self.size_tolerance,
                'time_tolerance': self.time_tolerance,
                'file_count': len(files),
                'total_size': sum(f.file_size for f in files if f.file_size),
                'metadata_analysis': metadata_analysis,
                'recommendation': 'verify_content'  # Always recommend content verification
            }
        )
        
        return group
    
    def _calculate_group_confidence(self, files: List[DuplicateFile]) -> float:
        """Calculate confidence score for a metadata group."""
        if len(files) < 2:
            return 0.0
        
        total_similarity = 0.0
        comparisons = 0
        
        # Compare all pairs in the group
        for i, file1 in enumerate(files):
            for file2 in files[i+1:]:
                similarity = self._calculate_pairwise_similarity(file1, file2)
                total_similarity += similarity
                comparisons += 1
        
        if comparisons == 0:
            return 0.0
        
        avg_similarity = total_similarity / comparisons
        
        # Adjust confidence based on group size (larger groups are more confident)
        size_bonus = min(10.0, len(files) * 2.0)  # Up to 10% bonus
        
        # Adjust confidence based on number of matching fields
        field_bonus = self._calculate_field_diversity_bonus(files)
        
        final_confidence = min(95.0, avg_similarity + size_bonus + field_bonus)  # Cap at 95%
        return round(final_confidence, 1)
    
    def _calculate_pairwise_similarity(self, file1: DuplicateFile, file2: DuplicateFile) -> float:
        """Calculate similarity percentage between two files."""
        matching_fields = 0
        total_fields = 0
        
        for field in self.comparison_fields:
            value1 = getattr(file1, field, None)
            value2 = getattr(file2, field, None)
            
            if value1 is not None and value2 is not None:
                total_fields += 1
                if self._compare_field_values(field, value1, value2):
                    matching_fields += 1
        
        if total_fields == 0:
            return 0.0
        
        return (matching_fields / total_fields) * 100.0
    
    def _calculate_field_diversity_bonus(self, files: List[DuplicateFile]) -> float:
        """Calculate bonus based on diversity of matching fields."""
        all_matching_fields = set()
        
        for i, file1 in enumerate(files):
            for file2 in files[i+1:]:
                matching_fields = self._get_matching_fields(file1, file2)
                all_matching_fields.update(matching_fields)
        
        # More diverse field matches = higher confidence
        diversity_ratio = len(all_matching_fields) / len(self.comparison_fields)
        return diversity_ratio * 10.0  # Up to 10% bonus
    
    def _get_matching_fields(self, file1: DuplicateFile, file2: DuplicateFile) -> List[str]:
        """Get list of fields that match between two files."""
        matching_fields = []
        
        for field in self.comparison_fields:
            value1 = getattr(file1, field, None)
            value2 = getattr(file2, field, None)
            
            if value1 is not None and value2 is not None:
                if self._compare_field_values(field, value1, value2):
                    matching_fields.append(field)
        
        return matching_fields
    
    def _analyze_group_metadata(self, files: List[DuplicateFile]) -> Dict[str, Any]:
        """Analyze metadata patterns in the group."""
        analysis = {
            'field_statistics': {},
            'common_patterns': [],
            'anomalies': []
        }
        
        for field in self.comparison_fields:
            values = [getattr(f, field, None) for f in files if getattr(f, field, None) is not None]
            
            if not values:
                continue
            
            field_stats = {
                'field_name': field,
                'total_files_with_field': len(values),
                'unique_values': len(set(str(v) for v in values)),
                'most_common_value': None
            }
            
            # Find most common value
            value_counts = defaultdict(int)
            for value in values:
                value_counts[str(value)] += 1
            
            if value_counts:
                most_common = max(value_counts.items(), key=lambda x: x[1])
                field_stats['most_common_value'] = most_common[0]
                field_stats['most_common_count'] = most_common[1]
            
            analysis['field_statistics'][field] = field_stats
            
            # Identify patterns
            if field_stats['unique_values'] == 1:
                analysis['common_patterns'].append(f"All files have identical {field}")
            elif field_stats['unique_values'] == len(values):
                analysis['anomalies'].append(f"All files have different {field}")
        
        return analysis
    
    def get_metadata_comparison_report(self, files: List[DuplicateFile]) -> Dict[str, Any]:
        """
        Generate a detailed metadata comparison report.
        
        Args:
            files: List of files to analyze
            
        Returns:
            Detailed metadata comparison report
        """
        report = {
            'total_files': len(files),
            'processable_files': len([f for f in files if self.can_process_file(f)]),
            'field_coverage': {},
            'similarity_matrix': {},
            'potential_groups': []
        }
        
        # Analyze field coverage
        for field in self.comparison_fields:
            files_with_field = [f for f in files if getattr(f, field, None) is not None]
            report['field_coverage'][field] = {
                'files_with_field': len(files_with_field),
                'coverage_percentage': len(files_with_field) / len(files) * 100 if files else 0
            }
        
        # Generate similarity matrix for small sets
        if len(files) <= 20:  # Limit to prevent performance issues
            for i, file1 in enumerate(files):
                for j, file2 in enumerate(files[i+1:], i+1):
                    similarity = self._calculate_pairwise_similarity(file1, file2)
                    if similarity > 0:
                        report['similarity_matrix'][(file1.file_id, file2.file_id)] = similarity
        
        # Find potential groups
        groups = self._group_by_metadata_similarity(files)
        for group_files in groups:
            if len(group_files) >= 2:
                group_info = {
                    'file_ids': [f.file_id for f in group_files],
                    'file_count': len(group_files),
                    'confidence': self._calculate_group_confidence(group_files),
                    'matching_fields': self._get_group_matching_fields(group_files)
                }
                report['potential_groups'].append(group_info)
        
        return report
    
    def _get_group_matching_fields(self, files: List[DuplicateFile]) -> List[str]:
        """Get fields that match across all files in the group."""
        if len(files) < 2:
            return []
        
        matching_fields = []
        
        for field in self.comparison_fields:
            # Check if all files have the same value for this field
            values = [getattr(f, field, None) for f in files]
            non_null_values = [v for v in values if v is not None]
            
            if len(non_null_values) >= 2:  # At least 2 files must have this field
                # Check if all non-null values are similar
                first_value = non_null_values[0]
                if all(self._compare_field_values(field, first_value, v) for v in non_null_values[1:]):
                    matching_fields.append(field)
        
        return matching_fields


# Register the algorithm
from ..algorithms import algorithm_registry
algorithm_registry.register(MetadataDetector)