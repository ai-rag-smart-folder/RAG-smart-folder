"""
Configuration management for duplicate detection system.
"""

import json
import os
from typing import Dict, Any, Optional, List
import logging
from .models import DetectionConfig, DetectionMode


class ConfigManager:
    """Manages configuration for duplicate detection system."""
    
    def __init__(self, config_file: Optional[str] = None):
        self.config_file = config_file or "detection_config.json"
        self.logger = logging.getLogger(self.__class__.__name__)
        self._default_config = DetectionConfig()
    
    def load_config(self, config_data: Optional[Dict[str, Any]] = None) -> DetectionConfig:
        """
        Load configuration from file or provided data.
        
        Args:
            config_data: Optional configuration dictionary to use instead of file
            
        Returns:
            DetectionConfig instance
        """
        if config_data:
            return self._create_config_from_dict(config_data)
        
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r') as f:
                    data = json.load(f)
                return self._create_config_from_dict(data)
            except Exception as e:
                self.logger.error(f"Failed to load config from {self.config_file}: {e}")
                self.logger.info("Using default configuration")
        
        return self._default_config
    
    def save_config(self, config: DetectionConfig) -> bool:
        """
        Save configuration to file.
        
        Args:
            config: Configuration to save
            
        Returns:
            True if saved successfully, False otherwise
        """
        try:
            config_dict = self._config_to_dict(config)
            with open(self.config_file, 'w') as f:
                json.dump(config_dict, f, indent=2)
            self.logger.info(f"Configuration saved to {self.config_file}")
            return True
        except Exception as e:
            self.logger.error(f"Failed to save config to {self.config_file}: {e}")
            return False
    
    def validate_config(self, config: DetectionConfig) -> List[str]:
        """
        Validate configuration and return list of errors.
        
        Args:
            config: Configuration to validate
            
        Returns:
            List of validation error messages
        """
        return config.validate()
    
    def get_default_config(self) -> DetectionConfig:
        """Get default configuration."""
        return DetectionConfig()
    
    def get_config_for_mode(self, mode: DetectionMode) -> DetectionConfig:
        """
        Get optimized configuration for specific detection mode.
        
        Args:
            mode: Detection mode
            
        Returns:
            Optimized configuration for the mode
        """
        config = DetectionConfig()
        
        if mode == DetectionMode.EXACT:
            # Optimize for exact matches only
            config.perceptual_threshold = 100.0
            config.min_confidence_threshold = 100.0
            config.enable_cross_algorithm_validation = False
            
        elif mode == DetectionMode.SIMILAR:
            # Optimize for similarity detection
            config.perceptual_threshold = 80.0
            config.min_confidence_threshold = 70.0
            config.use_color_histogram = True
            config.use_edge_detection = True
            
        elif mode == DetectionMode.METADATA:
            # Optimize for metadata-based detection
            config.min_confidence_threshold = 60.0
            config.metadata_fields = ['file_size', 'modified_at', 'width', 'height']
            config.size_tolerance = 1024  # 1KB tolerance
            config.time_tolerance = 300   # 5 minute tolerance
            
        elif mode == DetectionMode.COMPREHENSIVE:
            # Use balanced settings for all algorithms
            config.perceptual_threshold = 80.0
            config.min_confidence_threshold = 50.0
            config.enable_cross_algorithm_validation = True
            config.use_color_histogram = True
            config.use_edge_detection = True
        
        return config
    
    def _create_config_from_dict(self, data: Dict[str, Any]) -> DetectionConfig:
        """Create DetectionConfig from dictionary."""
        try:
            # Filter out unknown keys and use defaults for missing ones
            valid_keys = {
                'perceptual_threshold', 'perceptual_hash_size', 'metadata_fields',
                'size_tolerance', 'time_tolerance', 'use_color_histogram',
                'use_edge_detection', 'feature_weight_perceptual', 'feature_weight_color',
                'feature_weight_edge', 'min_confidence_threshold', 'max_results_per_group',
                'enable_cross_algorithm_validation'
            }
            
            filtered_data = {k: v for k, v in data.items() if k in valid_keys}
            config = DetectionConfig(**filtered_data)
            
            # Validate the configuration
            errors = self.validate_config(config)
            if errors:
                self.logger.warning(f"Configuration validation errors: {errors}")
                self.logger.info("Using default configuration")
                return self._default_config
            
            return config
            
        except Exception as e:
            self.logger.error(f"Failed to create config from data: {e}")
            return self._default_config
    
    def _config_to_dict(self, config: DetectionConfig) -> Dict[str, Any]:
        """Convert DetectionConfig to dictionary."""
        return {
            'perceptual_threshold': config.perceptual_threshold,
            'perceptual_hash_size': config.perceptual_hash_size,
            'metadata_fields': config.metadata_fields,
            'size_tolerance': config.size_tolerance,
            'time_tolerance': config.time_tolerance,
            'use_color_histogram': config.use_color_histogram,
            'use_edge_detection': config.use_edge_detection,
            'feature_weight_perceptual': config.feature_weight_perceptual,
            'feature_weight_color': config.feature_weight_color,
            'feature_weight_edge': config.feature_weight_edge,
            'min_confidence_threshold': config.min_confidence_threshold,
            'max_results_per_group': config.max_results_per_group,
            'enable_cross_algorithm_validation': config.enable_cross_algorithm_validation
        }
    
    def merge_configs(self, base_config: DetectionConfig, override_data: Dict[str, Any]) -> DetectionConfig:
        """
        Merge base configuration with override data.
        
        Args:
            base_config: Base configuration
            override_data: Data to override base config
            
        Returns:
            Merged configuration
        """
        base_dict = self._config_to_dict(base_config)
        base_dict.update(override_data)
        return self._create_config_from_dict(base_dict)