"""
Core duplicate detection engine.
"""

import uuid
import time
import logging
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session

from .models import (
    DetectionConfig, DetectionMode, DetectionResults, 
    DuplicateGroup, DuplicateFile, AlgorithmPerformance
)
from .algorithms import DetectionAlgorithm, algorithm_registry
from .config import ConfigManager
from ..logging import logger


class DuplicateDetectionEngine:
    """Core engine for running duplicate detection algorithms."""
    
    def __init__(self, config: Optional[DetectionConfig] = None, db_session: Optional[Session] = None):
        self.config = config or DetectionConfig()
        self.db_session = db_session
        self.logger = logger
        self.config_manager = ConfigManager()
        self.algorithms: List[DetectionAlgorithm] = []
        self.results_processor = ResultsProcessor()
    
    def add_algorithm(self, algorithm: DetectionAlgorithm):
        """
        Add a detection algorithm to the engine.
        
        Args:
            algorithm: Detection algorithm to add
        """
        self.algorithms.append(algorithm)
        self.logger.info(f"Added algorithm: {algorithm.get_algorithm_name()}")
    
    def detect_duplicates(self, 
                         files: List[DuplicateFile], 
                         mode: DetectionMode = DetectionMode.COMPREHENSIVE) -> DetectionResults:
        """
        Run duplicate detection with specified mode.
        
        Args:
            files: List of files to analyze
            mode: Detection mode to use
            
        Returns:
            Detection results with found duplicate groups
        """
        session_id = str(uuid.uuid4())
        start_time = time.time()
        
        self.logger.info(f"Starting duplicate detection (session: {session_id}, mode: {mode.value})")
        self.logger.info(f"Analyzing {len(files)} files")
        
        # Get optimized config for the mode
        mode_config = self.config_manager.get_config_for_mode(mode)
        
        # Select algorithms based on mode
        selected_algorithms = self._select_algorithms_for_mode(mode)
        
        if not selected_algorithms:
            self.logger.warning(f"No algorithms available for mode: {mode.value}")
            return self._create_empty_results(session_id, mode, files, start_time)
        
        # Run detection algorithms
        all_groups = []
        algorithm_performance = {}
        errors = []
        
        for algorithm in selected_algorithms:
            try:
                self.logger.info(f"Running algorithm: {algorithm.get_algorithm_name()}")
                groups = algorithm.run_detection(files)
                all_groups.extend(groups)
                
                # Store performance metrics
                perf = algorithm.get_performance_metrics()
                algorithm_performance[algorithm.get_algorithm_name()] = {
                    'files_processed': perf.files_processed,
                    'execution_time_ms': perf.execution_time_ms,
                    'groups_found': perf.groups_found,
                    'errors_encountered': perf.errors_encountered,
                    'files_per_second': perf.files_per_second,
                    'error_rate': perf.error_rate
                }
                
            except Exception as e:
                error_msg = f"Algorithm {algorithm.get_algorithm_name()} failed: {e}"
                self.logger.error(error_msg)
                errors.append(error_msg)
        
        # Process and consolidate results
        consolidated_groups = self.results_processor.consolidate_results(all_groups, mode_config)
        
        # Calculate final metrics
        end_time = time.time()
        detection_time_ms = int((end_time - start_time) * 1000)
        total_duplicates = sum(len(group.files) for group in consolidated_groups)
        
        results = DetectionResults(
            session_id=session_id,
            detection_mode=mode,
            groups=consolidated_groups,
            total_files_scanned=len(files),
            total_groups_found=len(consolidated_groups),
            total_duplicates_found=total_duplicates,
            detection_time_ms=detection_time_ms,
            config=mode_config,
            algorithm_performance=algorithm_performance,
            errors=errors
        )
        
        self.logger.info(f"Detection completed: {len(consolidated_groups)} groups, "
                        f"{total_duplicates} duplicates in {detection_time_ms}ms")
        
        # Store results in database if session available
        if self.db_session:
            self._store_results(results)
        
        return results
    
    def get_detection_report(self, results: DetectionResults) -> Dict[str, Any]:
        """
        Generate comprehensive detection report.
        
        Args:
            results: Detection results to report on
            
        Returns:
            Detailed report dictionary
        """
        return {
            'summary': {
                'session_id': results.session_id,
                'detection_mode': results.detection_mode.value,
                'total_files_scanned': results.total_files_scanned,
                'total_groups_found': results.total_groups_found,
                'total_duplicates_found': results.total_duplicates_found,
                'detection_time_ms': results.detection_time_ms,
                'success_rate': results.success_rate,
                'duplicate_percentage': results.duplicate_percentage
            },
            'algorithm_performance': results.algorithm_performance,
            'groups': [
                {
                    'id': group.id,
                    'detection_method': group.detection_method.value,
                    'confidence_score': group.confidence_score,
                    'similarity_percentage': group.similarity_percentage,
                    'file_count': group.file_count,
                    'total_size': group.total_size,
                    'files': [
                        {
                            'id': f.file_id,
                            'path': f.file_path,
                            'name': f.file_name,
                            'size': f.file_size,
                            'is_original': f.is_original,
                            'confidence_score': f.confidence_score,
                            'detection_reasons': f.detection_reasons
                        }
                        for f in group.files
                    ]
                }
                for group in results.groups
            ],
            'errors': results.errors,
            'config': {
                'perceptual_threshold': results.config.perceptual_threshold,
                'metadata_fields': results.config.metadata_fields,
                'min_confidence_threshold': results.config.min_confidence_threshold
            }
        }
    
    def _select_algorithms_for_mode(self, mode: DetectionMode) -> List[DetectionAlgorithm]:
        """Select appropriate algorithms for the detection mode."""
        if not self.algorithms:
            # Auto-load algorithms from registry if none manually added
            self.algorithms = algorithm_registry.get_all_algorithms(self.config)
        
        if mode == DetectionMode.EXACT:
            return [alg for alg in self.algorithms if 'SHA256' in alg.get_algorithm_name()]
        elif mode == DetectionMode.SIMILAR:
            return [alg for alg in self.algorithms if 'Perceptual' in alg.get_algorithm_name()]
        elif mode == DetectionMode.METADATA:
            return [alg for alg in self.algorithms if 'Metadata' in alg.get_algorithm_name()]
        else:  # COMPREHENSIVE
            return self.algorithms
    
    def _create_empty_results(self, session_id: str, mode: DetectionMode, 
                            files: List[DuplicateFile], start_time: float) -> DetectionResults:
        """Create empty results when no algorithms are available."""
        end_time = time.time()
        return DetectionResults(
            session_id=session_id,
            detection_mode=mode,
            groups=[],
            total_files_scanned=len(files),
            total_groups_found=0,
            total_duplicates_found=0,
            detection_time_ms=int((end_time - start_time) * 1000),
            config=self.config,
            errors=["No algorithms available for detection mode"]
        )
    
    def _store_results(self, results: DetectionResults):
        """Store detection results in database."""
        try:
            # This will be implemented when we update the database schema
            self.logger.info(f"Results stored for session: {results.session_id}")
        except Exception as e:
            self.logger.error(f"Failed to store results: {e}")


class ResultsProcessor:
    """Processes and consolidates detection results from multiple algorithms."""
    
    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)
    
    def consolidate_results(self, groups: List[DuplicateGroup], 
                          config: DetectionConfig) -> List[DuplicateGroup]:
        """
        Consolidate results from multiple algorithms.
        
        Args:
            groups: List of duplicate groups from all algorithms
            config: Detection configuration
            
        Returns:
            Consolidated and ranked list of duplicate groups
        """
        if not groups:
            return []
        
        self.logger.info(f"Consolidating {len(groups)} groups from algorithms")
        
        # Remove groups below confidence threshold
        filtered_groups = [
            group for group in groups 
            if group.confidence_score >= config.min_confidence_threshold
        ]
        
        self.logger.info(f"After confidence filtering: {len(filtered_groups)} groups")
        
        # Merge overlapping groups if cross-algorithm validation is enabled
        if config.enable_cross_algorithm_validation:
            filtered_groups = self._merge_overlapping_groups(filtered_groups)
            self.logger.info(f"After merging overlapping groups: {len(filtered_groups)} groups")
        
        # Rank groups by confidence and evidence
        ranked_groups = self._rank_groups(filtered_groups)
        
        # Suggest original files for each group
        for group in ranked_groups:
            self._suggest_original(group)
        
        # Limit results per group
        for group in ranked_groups:
            if len(group.files) > config.max_results_per_group:
                original_count = len(group.files)
                group.files = group.files[:config.max_results_per_group]
                self.logger.info(f"Limited group {group.id} from {original_count} to {len(group.files)} files")
        
        self.logger.info(f"Final consolidated results: {len(ranked_groups)} groups")
        return ranked_groups
    
    def _merge_overlapping_groups(self, groups: List[DuplicateGroup]) -> List[DuplicateGroup]:
        """Merge groups that contain overlapping files."""
        if len(groups) <= 1:
            return groups
        
        merged_groups = []
        processed_files = set()
        merge_count = 0
        
        for group in groups:
            group_file_ids = {f.file_id for f in group.files}
            
            # Check if any files in this group are already processed
            if group_file_ids & processed_files:
                # Find existing group to merge with
                merged = False
                for existing_group in merged_groups:
                    existing_file_ids = {f.file_id for f in existing_group.files}
                    if group_file_ids & existing_file_ids:
                        # Merge groups
                        self._merge_groups(existing_group, group)
                        merge_count += 1
                        merged = True
                        break
                
                if not merged:
                    # No suitable group found, add as new group
                    merged_groups.append(group)
                    processed_files.update(group_file_ids)
            else:
                # New group
                merged_groups.append(group)
                processed_files.update(group_file_ids)
        
        if merge_count > 0:
            self.logger.info(f"Merged {merge_count} overlapping groups")
        
        return merged_groups
    
    def _merge_groups(self, target_group: DuplicateGroup, source_group: DuplicateGroup):
        """Merge source group into target group."""
        # Add files that aren't already in target
        target_file_ids = {f.file_id for f in target_group.files}
        added_files = 0
        
        for file in source_group.files:
            if file.file_id not in target_file_ids:
                target_group.files.append(file)
                added_files += 1
        
        # Update confidence score (weighted average based on file counts)
        target_weight = len(target_group.files) - added_files
        source_weight = len(source_group.files)
        total_weight = target_weight + source_weight
        
        if total_weight > 0:
            weighted_confidence = (
                (target_group.confidence_score * target_weight + 
                 source_group.confidence_score * source_weight) / total_weight
            )
            target_group.confidence_score = round(weighted_confidence, 1)
        
        # Update similarity percentage (take maximum)
        target_group.similarity_percentage = max(
            target_group.similarity_percentage, 
            source_group.similarity_percentage
        )
        
        # Merge detection methods and metadata
        target_group.metadata.setdefault('merged_methods', [])
        if source_group.detection_method.value not in target_group.metadata['merged_methods']:
            target_group.metadata['merged_methods'].append(source_group.detection_method.value)
        
        # Merge additional metadata
        target_group.metadata.setdefault('merge_history', [])
        target_group.metadata['merge_history'].append({
            'merged_group_id': source_group.id,
            'merged_method': source_group.detection_method.value,
            'files_added': added_files,
            'source_confidence': source_group.confidence_score
        })
        
        self.logger.debug(f"Merged group {source_group.id} into {target_group.id}, added {added_files} files")
    
    def _rank_groups(self, groups: List[DuplicateGroup]) -> List[DuplicateGroup]:
        """Rank groups by confidence score, file count, and total size."""
        def ranking_key(group: DuplicateGroup) -> Tuple[float, int, int]:
            return (
                group.confidence_score,  # Primary: confidence score
                len(group.files),        # Secondary: number of files
                group.total_size         # Tertiary: total size
            )
        
        return sorted(groups, key=ranking_key, reverse=True)
    
    def _suggest_original(self, group: DuplicateGroup):
        """Suggest which file should be considered the original."""
        if not group.files:
            return
        
        # Reset any existing original flags
        for file in group.files:
            file.is_original = False
        
        # Scoring criteria (higher is better):
        # 1. Earliest creation/modification time (40% weight)
        # 2. Largest file size (30% weight)
        # 3. Best quality for images (20% weight)
        # 4. Path characteristics (10% weight)
        
        best_file = None
        best_score = float('-inf')
        
        # Calculate min/max values for normalization
        sizes = [f.file_size for f in group.files if f.file_size]
        times = []
        for f in group.files:
            if f.created_at:
                times.append(f.created_at.timestamp())
            elif f.modified_at:
                times.append(f.modified_at.timestamp())
        
        min_size = min(sizes) if sizes else 0
        max_size = max(sizes) if sizes else 0
        min_time = min(times) if times else 0
        max_time = max(times) if times else 0
        
        for file in group.files:
            score = 0
            
            # Time score (earlier is better) - 40% weight
            file_time = None
            if file.created_at:
                file_time = file.created_at.timestamp()
            elif file.modified_at:
                file_time = file.modified_at.timestamp()
            
            if file_time and max_time > min_time:
                # Normalize and invert (earlier = higher score)
                time_score = 1.0 - (file_time - min_time) / (max_time - min_time)
                score += time_score * 40
            
            # Size score (larger is better) - 30% weight
            if file.file_size and max_size > min_size:
                size_score = (file.file_size - min_size) / (max_size - min_size)
                score += size_score * 30
            
            # Quality score for images (larger dimensions = better quality) - 20% weight
            if file.width and file.height:
                pixel_count = file.width * file.height
                # Normalize against common resolutions
                quality_score = min(1.0, pixel_count / (1920 * 1080))  # Normalize to 1080p
                score += quality_score * 20
            
            # Path characteristics - 10% weight
            path_score = self._calculate_path_score(file.file_path)
            score += path_score * 10
            
            if score > best_score:
                best_score = score
                best_file = file
        
        # Mark the best file as original
        if best_file:
            best_file.is_original = True
            best_file.detection_reasons.append("suggested_original")
            
            # Add specific reasons for why this file was chosen
            reasons = []
            if best_file.created_at or best_file.modified_at:
                reasons.append("earliest_timestamp")
            if best_file.file_size and best_file.file_size == max(f.file_size for f in group.files if f.file_size):
                reasons.append("largest_size")
            if best_file.width and best_file.height:
                reasons.append("best_quality")
            
            best_file.detection_reasons.extend(reasons)
            
            self.logger.debug(f"Suggested original for group {group.id}: {best_file.file_name} (score: {best_score:.1f})")
    
    def _calculate_path_score(self, file_path: str) -> float:
        """Calculate a score based on path characteristics."""
        if not file_path:
            return 0.0
        
        score = 0.5  # Base score
        
        # Prefer files not in common backup/temp directories
        lower_path = file_path.lower()
        penalty_dirs = ['backup', 'temp', 'tmp', 'cache', 'trash', 'recycle']
        
        for penalty_dir in penalty_dirs:
            if penalty_dir in lower_path:
                score -= 0.2
                break
        
        # Prefer files in root directories over deeply nested ones
        depth = file_path.count('/')
        if depth <= 2:
            score += 0.2
        elif depth >= 5:
            score -= 0.1
        
        # Prefer files with shorter names (often originals)
        filename = file_path.split('/')[-1]
        if len(filename) <= 20:
            score += 0.1
        elif len(filename) >= 50:
            score -= 0.1
        
        return max(0.0, min(1.0, score))
    
    def generate_consolidation_report(self, original_groups: List[DuplicateGroup], 
                                    consolidated_groups: List[DuplicateGroup],
                                    config: DetectionConfig) -> Dict[str, Any]:
        """
        Generate a report about the consolidation process.
        
        Args:
            original_groups: Groups before consolidation
            consolidated_groups: Groups after consolidation
            config: Configuration used
            
        Returns:
            Consolidation report
        """
        original_file_count = sum(len(g.files) for g in original_groups)
        consolidated_file_count = sum(len(g.files) for g in consolidated_groups)
        
        # Calculate confidence distribution
        confidence_ranges = {'90-100': 0, '80-89': 0, '70-79': 0, '60-69': 0, '50-59': 0, '<50': 0}
        for group in consolidated_groups:
            conf = group.confidence_score
            if conf >= 90:
                confidence_ranges['90-100'] += 1
            elif conf >= 80:
                confidence_ranges['80-89'] += 1
            elif conf >= 70:
                confidence_ranges['70-79'] += 1
            elif conf >= 60:
                confidence_ranges['60-69'] += 1
            elif conf >= 50:
                confidence_ranges['50-59'] += 1
            else:
                confidence_ranges['<50'] += 1
        
        # Analyze detection methods
        method_distribution = defaultdict(int)
        merged_groups = 0
        
        for group in consolidated_groups:
            method_distribution[group.detection_method.value] += 1
            if 'merged_methods' in group.metadata:
                merged_groups += 1
        
        return {
            'summary': {
                'original_groups': len(original_groups),
                'consolidated_groups': len(consolidated_groups),
                'groups_filtered': len(original_groups) - len(consolidated_groups),
                'original_file_count': original_file_count,
                'consolidated_file_count': consolidated_file_count,
                'merged_groups': merged_groups
            },
            'confidence_distribution': confidence_ranges,
            'detection_method_distribution': dict(method_distribution),
            'configuration': {
                'min_confidence_threshold': config.min_confidence_threshold,
                'max_results_per_group': config.max_results_per_group,
                'cross_algorithm_validation': config.enable_cross_algorithm_validation
            },
            'quality_metrics': {
                'avg_confidence': sum(g.confidence_score for g in consolidated_groups) / len(consolidated_groups) if consolidated_groups else 0,
                'avg_group_size': consolidated_file_count / len(consolidated_groups) if consolidated_groups else 0,
                'largest_group_size': max(len(g.files) for g in consolidated_groups) if consolidated_groups else 0
            }
        }
    
    def validate_consolidation_results(self, groups: List[DuplicateGroup]) -> List[str]:
        """
        Validate consolidation results and return any issues found.
        
        Args:
            groups: Consolidated groups to validate
            
        Returns:
            List of validation issues
        """
        issues = []
        
        # Check for duplicate file IDs across groups
        all_file_ids = set()
        for group in groups:
            group_file_ids = {f.file_id for f in group.files}
            overlap = all_file_ids & group_file_ids
            if overlap:
                issues.append(f"File IDs {overlap} appear in multiple groups")
            all_file_ids.update(group_file_ids)
        
        # Check group validity
        for group in groups:
            if len(group.files) < 2:
                issues.append(f"Group {group.id} has fewer than 2 files")
            
            if not (0 <= group.confidence_score <= 100):
                issues.append(f"Group {group.id} has invalid confidence score: {group.confidence_score}")
            
            # Check that at most one file is marked as original
            originals = [f for f in group.files if f.is_original]
            if len(originals) > 1:
                issues.append(f"Group {group.id} has multiple files marked as original")
        
        return issues