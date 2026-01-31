"""
Base classes and interfaces for detection algorithms.
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
import logging
import time
from .models import DuplicateGroup, DuplicateFile, DetectionConfig, AlgorithmPerformance


class DetectionAlgorithm(ABC):
    """Abstract base class for duplicate detection algorithms."""
    
    def __init__(self, config: DetectionConfig, logger: Optional[logging.Logger] = None):
        self.config = config
        self.logger = logger or logging.getLogger(self.__class__.__name__)
        self.performance = AlgorithmPerformance(
            algorithm_name=self.__class__.__name__,
            files_processed=0,
            execution_time_ms=0,
            groups_found=0,
            errors_encountered=0
        )
    
    @abstractmethod
    def detect(self, files: List[DuplicateFile]) -> List[DuplicateGroup]:
        """
        Detect duplicates among the given files.
        
        Args:
            files: List of files to analyze for duplicates
            
        Returns:
            List of duplicate groups found by this algorithm
        """
        pass
    
    @abstractmethod
    def get_algorithm_name(self) -> str:
        """Return the name of this algorithm."""
        pass
    
    @abstractmethod
    def get_supported_file_types(self) -> List[str]:
        """Return list of file extensions this algorithm supports."""
        pass
    
    def can_process_file(self, file: DuplicateFile) -> bool:
        """
        Check if this algorithm can process the given file.
        
        Args:
            file: File to check
            
        Returns:
            True if the algorithm can process this file type
        """
        if not file.file_type:
            return False
        
        supported_types = self.get_supported_file_types()
        if not supported_types:  # Empty list means all types supported
            return True
            
        return file.file_type.lower() in [t.lower() for t in supported_types]
    
    def filter_files(self, files: List[DuplicateFile]) -> List[DuplicateFile]:
        """
        Filter files to only those this algorithm can process.
        
        Args:
            files: List of files to filter
            
        Returns:
            Filtered list of files this algorithm can process
        """
        return [f for f in files if self.can_process_file(f)]
    
    def run_detection(self, files: List[DuplicateFile]) -> List[DuplicateGroup]:
        """
        Run detection with performance tracking and error handling.
        
        Args:
            files: List of files to analyze
            
        Returns:
            List of duplicate groups found
        """
        start_time = time.time()
        self.performance.files_processed = len(files)
        
        try:
            # Filter files this algorithm can process
            processable_files = self.filter_files(files)
            
            if not processable_files:
                self.logger.info(f"{self.get_algorithm_name()}: No processable files found")
                return []
            
            self.logger.info(f"{self.get_algorithm_name()}: Processing {len(processable_files)} files")
            
            # Run the actual detection
            groups = self.detect(processable_files)
            
            self.performance.groups_found = len(groups)
            self.logger.info(f"{self.get_algorithm_name()}: Found {len(groups)} duplicate groups")
            
            return groups
            
        except Exception as e:
            self.performance.errors_encountered += 1
            self.logger.error(f"{self.get_algorithm_name()}: Detection failed: {e}")
            return []
            
        finally:
            end_time = time.time()
            self.performance.execution_time_ms = int((end_time - start_time) * 1000)
    
    def get_performance_metrics(self) -> AlgorithmPerformance:
        """Get performance metrics for this algorithm."""
        return self.performance
    
    def reset_performance_metrics(self):
        """Reset performance metrics."""
        self.performance = AlgorithmPerformance(
            algorithm_name=self.__class__.__name__,
            files_processed=0,
            execution_time_ms=0,
            groups_found=0,
            errors_encountered=0
        )


class AlgorithmRegistry:
    """Registry for managing detection algorithms."""
    
    def __init__(self):
        self._algorithms: Dict[str, type] = {}
        self.logger = logging.getLogger(self.__class__.__name__)
    
    def register(self, algorithm_class: type):
        """
        Register a detection algorithm.
        
        Args:
            algorithm_class: Class that extends DetectionAlgorithm
        """
        if not issubclass(algorithm_class, DetectionAlgorithm):
            raise ValueError(f"Algorithm must extend DetectionAlgorithm: {algorithm_class}")
        
        name = algorithm_class.__name__
        self._algorithms[name] = algorithm_class
        self.logger.info(f"Registered algorithm: {name}")
    
    def get_algorithm(self, name: str, config: DetectionConfig) -> Optional[DetectionAlgorithm]:
        """
        Get an instance of a registered algorithm.
        
        Args:
            name: Name of the algorithm
            config: Configuration for the algorithm
            
        Returns:
            Algorithm instance or None if not found
        """
        algorithm_class = self._algorithms.get(name)
        if not algorithm_class:
            self.logger.error(f"Algorithm not found: {name}")
            return None
        
        try:
            return algorithm_class(config)
        except Exception as e:
            self.logger.error(f"Failed to create algorithm {name}: {e}")
            return None
    
    def list_algorithms(self) -> List[str]:
        """Get list of registered algorithm names."""
        return list(self._algorithms.keys())
    
    def get_all_algorithms(self, config: DetectionConfig) -> List[DetectionAlgorithm]:
        """
        Get instances of all registered algorithms.
        
        Args:
            config: Configuration for the algorithms
            
        Returns:
            List of algorithm instances
        """
        algorithms = []
        for name in self._algorithms:
            algorithm = self.get_algorithm(name, config)
            if algorithm:
                algorithms.append(algorithm)
        return algorithms


# Global algorithm registry
algorithm_registry = AlgorithmRegistry()