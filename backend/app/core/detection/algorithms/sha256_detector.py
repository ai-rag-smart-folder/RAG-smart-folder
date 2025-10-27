"""
SHA256-based exact duplicate detection algorithm.
"""

import uuid
from typing import List, Dict, Set
from collections import defaultdict

from ..algorithms import DetectionAlgorithm
from ..models import DuplicateGroup, DuplicateFile, DetectionMethod, DetectionConfig


class SHA256Detector(DetectionAlgorithm):
    """Detects exact duplicates using SHA256 hash comparison."""
    
    def __init__(self, config: DetectionConfig, logger=None):
        super().__init__(config, logger)
        self.algorithm_name = "SHA256Detector"
    
    def detect(self, files: List[DuplicateFile]) -> List[DuplicateGroup]:
        """
        Detect exact duplicates using SHA256 hash comparison.
        
        Args:
            files: List of files to analyze
            
        Returns:
            List of duplicate groups with identical SHA256 hashes
        """
        if not files:
            return []
        
        # Group files by SHA256 hash
        hash_groups = defaultdict(list)
        files_without_hash = []
        
        for file in files:
            if file.sha256 and file.sha256.strip():
                hash_groups[file.sha256].append(file)
            else:
                files_without_hash.append(file)
        
        if files_without_hash:
            self.logger.warning(f"SHA256Detector: {len(files_without_hash)} files without SHA256 hash")
        
        # Create duplicate groups for hashes with multiple files
        duplicate_groups = []
        
        for sha256_hash, file_list in hash_groups.items():
            if len(file_list) < 2:
                continue  # Not a duplicate group
            
            # Create duplicate group
            group_id = f"sha256_{uuid.uuid4().hex[:8]}"
            
            # Set confidence scores for all files (100% for exact matches)
            for file in file_list:
                file.confidence_score = 100.0
                file.detection_reasons.append("identical_sha256_hash")
            
            group = DuplicateGroup(
                id=group_id,
                detection_method=DetectionMethod.SHA256,
                confidence_score=100.0,  # Always 100% for exact matches
                similarity_percentage=100.0,  # Always 100% for exact matches
                files=file_list,
                metadata={
                    'sha256_hash': sha256_hash,
                    'detection_algorithm': self.algorithm_name,
                    'file_count': len(file_list),
                    'total_size': sum(f.file_size for f in file_list if f.file_size)
                }
            )
            
            duplicate_groups.append(group)
            self.logger.debug(f"SHA256Detector: Found duplicate group with {len(file_list)} files "
                            f"(hash: {sha256_hash[:16]}...)")
        
        self.logger.info(f"SHA256Detector: Found {len(duplicate_groups)} duplicate groups "
                        f"from {len(files)} files")
        
        return duplicate_groups
    
    def get_algorithm_name(self) -> str:
        """Return the name of this algorithm."""
        return self.algorithm_name
    
    def get_supported_file_types(self) -> List[str]:
        """Return list of supported file extensions (all types for SHA256)."""
        return []  # Empty list means all file types are supported
    
    def can_process_file(self, file: DuplicateFile) -> bool:
        """
        Check if this algorithm can process the given file.
        SHA256 detector can process any file that has a SHA256 hash.
        
        Args:
            file: File to check
            
        Returns:
            True if file has SHA256 hash, False otherwise
        """
        return bool(file.sha256 and file.sha256.strip())
    
    def get_statistics(self, groups: List[DuplicateGroup]) -> Dict[str, any]:
        """
        Get statistics about the detection results.
        
        Args:
            groups: List of duplicate groups found
            
        Returns:
            Dictionary with statistics
        """
        if not groups:
            return {
                'total_groups': 0,
                'total_duplicates': 0,
                'total_size_duplicated': 0,
                'largest_group_size': 0,
                'average_group_size': 0.0
            }
        
        total_duplicates = sum(len(group.files) for group in groups)
        total_size_duplicated = sum(group.total_size for group in groups)
        group_sizes = [len(group.files) for group in groups]
        
        return {
            'total_groups': len(groups),
            'total_duplicates': total_duplicates,
            'total_size_duplicated': total_size_duplicated,
            'largest_group_size': max(group_sizes),
            'average_group_size': sum(group_sizes) / len(group_sizes),
            'size_savings_potential': total_size_duplicated - sum(
                max(f.file_size for f in group.files) for group in groups
            )
        }


# Register the algorithm
from ..algorithms import algorithm_registry
algorithm_registry.register(SHA256Detector)