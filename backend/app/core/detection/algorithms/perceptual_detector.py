"""
Perceptual hash-based similarity detection algorithm for images.
"""

import uuid
from typing import List, Dict, Optional, Tuple
from collections import defaultdict
import logging

from ..algorithms import DetectionAlgorithm
from ..models import DuplicateGroup, DuplicateFile, DetectionMethod, DetectionConfig


class PerceptualHashDetector(DetectionAlgorithm):
    """Detects similar images using perceptual hash comparison."""
    
    def __init__(self, config: DetectionConfig, logger: Optional[logging.Logger] = None):
        super().__init__(config, logger)
        self.algorithm_name = "PerceptualHashDetector"
        self.threshold = config.perceptual_threshold
        
        # Try to import imagehash for hash comparison
        try:
            import imagehash
            self.imagehash = imagehash
            self.hash_available = True
        except ImportError:
            self.logger.warning("imagehash library not available - perceptual detection disabled")
            self.imagehash = None
            self.hash_available = False
    
    def detect(self, files: List[DuplicateFile]) -> List[DuplicateGroup]:
        """
        Detect similar images using perceptual hash comparison.
        
        Args:
            files: List of files to analyze (should be images)
            
        Returns:
            List of duplicate groups with similar perceptual hashes
        """
        if not self.hash_available:
            self.logger.warning("PerceptualHashDetector: imagehash not available")
            return []
        
        if not files:
            return []
        
        # Filter to only image files with perceptual hashes
        image_files = self._filter_image_files(files)
        
        if len(image_files) < 2:
            self.logger.info(f"PerceptualHashDetector: Need at least 2 image files, got {len(image_files)}")
            return []
        
        # Find similar groups using perceptual hash comparison
        similar_groups = self._find_similar_groups(image_files)
        
        self.logger.info(f"PerceptualHashDetector: Found {len(similar_groups)} similar groups "
                        f"from {len(image_files)} images")
        
        return similar_groups
    
    def get_algorithm_name(self) -> str:
        """Return the name of this algorithm."""
        return self.algorithm_name
    
    def get_supported_file_types(self) -> List[str]:
        """Return list of supported image file extensions."""
        return ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff', '.webp']
    
    def can_process_file(self, file: DuplicateFile) -> bool:
        """
        Check if this algorithm can process the given file.
        
        Args:
            file: File to check
            
        Returns:
            True if file is an image with perceptual hash
        """
        if not self.hash_available:
            return False
        
        # Check if it's an image file type
        if not file.file_type:
            return False
        
        supported_types = [t.lower() for t in self.get_supported_file_types()]
        if file.file_type.lower() not in supported_types:
            return False
        
        # Check if it has a perceptual hash
        return bool(file.perceptual_hash and file.perceptual_hash.strip())
    
    def _filter_image_files(self, files: List[DuplicateFile]) -> List[DuplicateFile]:
        """Filter files to only processable image files."""
        return [f for f in files if self.can_process_file(f)]
    
    def _find_similar_groups(self, files: List[DuplicateFile]) -> List[DuplicateGroup]:
        """Find groups of similar images based on perceptual hash comparison."""
        if not files:
            return []
        
        groups = []
        processed_files = set()
        
        for i, file1 in enumerate(files):
            if file1.file_id in processed_files:
                continue
            
            # Start a new potential group with this file
            similar_files = [file1]
            similarities = [100.0]  # Self-similarity is 100%
            
            # Compare with remaining files
            for j, file2 in enumerate(files[i+1:], i+1):
                if file2.file_id in processed_files:
                    continue
                
                similarity = self._calculate_similarity(file1.perceptual_hash, file2.perceptual_hash)
                
                if similarity >= self.threshold:
                    similar_files.append(file2)
                    similarities.append(similarity)
                    processed_files.add(file2.file_id)
            
            # Create group if we found similar files
            if len(similar_files) > 1:
                group = self._create_similarity_group(similar_files, similarities)
                groups.append(group)
                processed_files.add(file1.file_id)
        
        return groups
    
    def _calculate_similarity(self, hash1: str, hash2: str) -> float:
        """
        Calculate similarity percentage between two perceptual hashes.
        
        Args:
            hash1: First perceptual hash
            hash2: Second perceptual hash
            
        Returns:
            Similarity percentage (0-100)
        """
        if not hash1 or not hash2:
            return 0.0
        
        try:
            # Convert hex strings to imagehash objects
            h1 = self.imagehash.hex_to_hash(hash1)
            h2 = self.imagehash.hex_to_hash(hash2)
            
            # Calculate Hamming distance
            hamming_distance = h1 - h2
            
            # Convert to similarity percentage
            # Maximum possible distance is the hash size * 4 (for hex representation)
            max_distance = len(str(h1)) * 4
            similarity = max(0, (max_distance - hamming_distance) / max_distance * 100)
            
            return round(similarity, 1)
            
        except Exception as e:
            self.logger.error(f"Error calculating similarity between {hash1} and {hash2}: {e}")
            return 0.0
    
    def _create_similarity_group(self, files: List[DuplicateFile], 
                               similarities: List[float]) -> DuplicateGroup:
        """Create a duplicate group from similar files."""
        group_id = f"perceptual_{uuid.uuid4().hex[:8]}"
        
        # Calculate group confidence and similarity
        avg_similarity = sum(similarities) / len(similarities)
        min_similarity = min(similarities)
        max_similarity = max(similarities)
        
        # Set confidence scores and detection reasons for files
        for i, file in enumerate(files):
            file.confidence_score = similarities[i]
            file.detection_reasons.append("similar_perceptual_hash")
            if similarities[i] == 100.0:
                file.detection_reasons.append("identical_perceptual_hash")
        
        # Create the group
        group = DuplicateGroup(
            id=group_id,
            detection_method=DetectionMethod.PERCEPTUAL_HASH,
            confidence_score=avg_similarity,
            similarity_percentage=avg_similarity,
            files=files,
            metadata={
                'detection_algorithm': self.algorithm_name,
                'threshold_used': self.threshold,
                'avg_similarity': avg_similarity,
                'min_similarity': min_similarity,
                'max_similarity': max_similarity,
                'file_count': len(files),
                'total_size': sum(f.file_size for f in files if f.file_size),
                'similarity_distribution': similarities
            }
        )
        
        return group
    
    def get_similarity_matrix(self, files: List[DuplicateFile]) -> Dict[Tuple[int, int], float]:
        """
        Calculate similarity matrix for all file pairs.
        
        Args:
            files: List of files to compare
            
        Returns:
            Dictionary mapping (file_id1, file_id2) to similarity percentage
        """
        if not self.hash_available:
            return {}
        
        image_files = self._filter_image_files(files)
        similarity_matrix = {}
        
        for i, file1 in enumerate(image_files):
            for j, file2 in enumerate(image_files[i+1:], i+1):
                similarity = self._calculate_similarity(file1.perceptual_hash, file2.perceptual_hash)
                similarity_matrix[(file1.file_id, file2.file_id)] = similarity
                similarity_matrix[(file2.file_id, file1.file_id)] = similarity  # Symmetric
        
        return similarity_matrix
    
    def get_hash_algorithms_info(self) -> Dict[str, any]:
        """
        Get information about available perceptual hash algorithms.
        
        Returns:
            Dictionary with hash algorithm information
        """
        if not self.hash_available:
            return {'available': False, 'algorithms': []}
        
        algorithms = []
        
        # Check which hash algorithms are available
        hash_types = ['average_hash', 'perceptual_hash', 'difference_hash', 'wavelet_hash']
        
        for hash_type in hash_types:
            if hasattr(self.imagehash, hash_type):
                algorithms.append({
                    'name': hash_type,
                    'description': self._get_hash_description(hash_type),
                    'recommended_for': self._get_hash_use_case(hash_type)
                })
        
        return {
            'available': True,
            'algorithms': algorithms,
            'current_threshold': self.threshold,
            'hash_size': self.config.perceptual_hash_size
        }
    
    def _get_hash_description(self, hash_type: str) -> str:
        """Get description for hash algorithm type."""
        descriptions = {
            'average_hash': 'Average hash - good for detecting scaled/cropped images',
            'perceptual_hash': 'Perceptual hash - robust against color changes and minor edits',
            'difference_hash': 'Difference hash - sensitive to structural changes',
            'wavelet_hash': 'Wavelet hash - good for detecting rotated/flipped images'
        }
        return descriptions.get(hash_type, 'Unknown hash algorithm')
    
    def _get_hash_use_case(self, hash_type: str) -> str:
        """Get recommended use case for hash algorithm type."""
        use_cases = {
            'average_hash': 'Scaled or cropped versions',
            'perceptual_hash': 'Color-adjusted or lightly edited images',
            'difference_hash': 'Structurally similar images',
            'wavelet_hash': 'Rotated or flipped images'
        }
        return use_cases.get(hash_type, 'General similarity detection')
    
    def analyze_hash_distribution(self, files: List[DuplicateFile]) -> Dict[str, any]:
        """
        Analyze the distribution of perceptual hashes in the file set.
        
        Args:
            files: List of files to analyze
            
        Returns:
            Dictionary with hash distribution analysis
        """
        image_files = self._filter_image_files(files)
        
        if not image_files:
            return {'total_images': 0, 'images_with_hash': 0}
        
        hash_lengths = defaultdict(int)
        unique_hashes = set()
        
        for file in image_files:
            if file.perceptual_hash:
                hash_lengths[len(file.perceptual_hash)] += 1
                unique_hashes.add(file.perceptual_hash)
        
        return {
            'total_images': len(image_files),
            'images_with_hash': len([f for f in image_files if f.perceptual_hash]),
            'unique_hashes': len(unique_hashes),
            'hash_length_distribution': dict(hash_lengths),
            'potential_exact_duplicates': len(image_files) - len(unique_hashes)
        }


# Register the algorithm
from ..algorithms import algorithm_registry
algorithm_registry.register(PerceptualHashDetector)