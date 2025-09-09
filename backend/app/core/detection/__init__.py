"""
Core duplicate detection engine module.
"""

from .engine import DuplicateDetectionEngine
from .algorithms import DetectionAlgorithm
from .models import DuplicateGroup, DuplicateFile, DetectionConfig, DetectionResults
from .config import ConfigManager

__all__ = [
    'DuplicateDetectionEngine',
    'DetectionAlgorithm', 
    'DuplicateGroup',
    'DuplicateFile',
    'DetectionConfig',
    'DetectionResults',
    'ConfigManager'
]