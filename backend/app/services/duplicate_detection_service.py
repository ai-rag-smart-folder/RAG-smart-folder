"""
Service layer for duplicate detection operations.
"""

import uuid
import json
import sqlite3
from typing import List, Dict, Any, Optional
from datetime import datetime
from sqlalchemy.orm import Session

from ..core.detection import (
    DuplicateDetectionEngine, DetectionConfig, DetectionMode, 
    DuplicateFile, DetectionResults
)
from ..core.detection.algorithms import SHA256Detector, PerceptualHashDetector, MetadataDetector
from ..models.file import File
from ..core.logging import logger


class DuplicateDetectionService:
    """Service for managing duplicate detection operations."""
    
    def __init__(self, db_session: Session):
        self.db_session = db_session
        self.logger = logger
        self._engine = None
    
    def get_detection_engine(self, config: Optional[DetectionConfig] = None) -> DuplicateDetectionEngine:
        """Get or create detection engine with specified configuration."""
        if not self._engine or (config and config != self._engine.config):
            self._engine = DuplicateDetectionEngine(config, self.db_session)
            
            # Add all available algorithms
            if config:
                self._engine.add_algorithm(SHA256Detector(config))
                self._engine.add_algorithm(PerceptualHashDetector(config))
                self._engine.add_algorithm(MetadataDetector(config))
        
        return self._engine
    
    def detect_duplicates_exact(self, file_filters: Optional[Dict[str, Any]] = None) -> DetectionResults:
        """
        Detect exact duplicates using SHA256 hash comparison.
        
        Args:
            file_filters: Optional filters for file selection
            
        Returns:
            Detection results with exact duplicate groups
        """
        config = DetectionConfig(min_confidence_threshold=100.0)
        files = self._get_files_for_detection(file_filters)
        
        engine = self.get_detection_engine(config)
        results = engine.detect_duplicates(files, DetectionMode.EXACT)
        
        # Store results in database
        self._store_detection_results(results)
        
        return results
    
    def detect_duplicates_similar(self, 
                                similarity_threshold: float = 80.0,
                                file_filters: Optional[Dict[str, Any]] = None) -> DetectionResults:
        """
        Detect similar files using perceptual hash comparison.
        
        Args:
            similarity_threshold: Similarity threshold percentage (0-100)
            file_filters: Optional filters for file selection
            
        Returns:
            Detection results with similar file groups
        """
        config = DetectionConfig(
            perceptual_threshold=similarity_threshold,
            min_confidence_threshold=similarity_threshold
        )
        files = self._get_files_for_detection(file_filters)
        
        engine = self.get_detection_engine(config)
        results = engine.detect_duplicates(files, DetectionMode.SIMILAR)
        
        # Store results in database
        self._store_detection_results(results)
        
        return results
    
    def detect_duplicates_comprehensive(self, 
                                      config: Optional[DetectionConfig] = None,
                                      file_filters: Optional[Dict[str, Any]] = None) -> DetectionResults:
        """
        Detect duplicates using all available algorithms.
        
        Args:
            config: Detection configuration (uses default if not provided)
            file_filters: Optional filters for file selection
            
        Returns:
            Detection results with comprehensive duplicate analysis
        """
        if not config:
            config = DetectionConfig()
        
        files = self._get_files_for_detection(file_filters)
        
        engine = self.get_detection_engine(config)
        results = engine.detect_duplicates(files, DetectionMode.COMPREHENSIVE)
        
        # Store results in database
        self._store_detection_results(results)
        
        return results
    
    def detect_duplicates_metadata(self, 
                                 metadata_fields: Optional[List[str]] = None,
                                 file_filters: Optional[Dict[str, Any]] = None) -> DetectionResults:
        """
        Detect potential duplicates using metadata comparison.
        
        Args:
            metadata_fields: List of metadata fields to compare
            file_filters: Optional filters for file selection
            
        Returns:
            Detection results with metadata-based potential duplicates
        """
        config = DetectionConfig(
            metadata_fields=metadata_fields or ['file_size', 'modified_at'],
            min_confidence_threshold=50.0
        )
        files = self._get_files_for_detection(file_filters)
        
        engine = self.get_detection_engine(config)
        results = engine.detect_duplicates(files, DetectionMode.METADATA)
        
        # Store results in database
        self._store_detection_results(results)
        
        return results
    
    def get_detection_results(self, session_id: str) -> Optional[Dict[str, Any]]:
        """
        Get stored detection results by session ID.
        
        Args:
            session_id: Detection session ID
            
        Returns:
            Detection results dictionary or None if not found
        """
        try:
            # Query detection_results table
            db_path = self.db_session.get_bind().url.database
            with sqlite3.connect(db_path) as conn:
                cursor = conn.execute("""
                    SELECT session_id, detection_mode, total_files_scanned, 
                           total_groups_found, total_duplicates_found, detection_time_ms,
                           config_json, algorithm_performance_json, errors_json,
                           success_rate, duplicate_percentage, created_at
                    FROM detection_results 
                    WHERE session_id = ?
                """, (session_id,))
                
                row = cursor.fetchone()
                if not row:
                    return None
                
                # Parse JSON fields
                config_json = json.loads(row[6]) if row[6] else {}
                performance_json = json.loads(row[7]) if row[7] else {}
                errors_json = json.loads(row[8]) if row[8] else []
                
                # Get duplicate groups for this session
                groups = self._get_duplicate_groups_for_session(session_id, conn)
                
                return {
                    'session_id': row[0],
                    'detection_mode': row[1],
                    'summary': {
                        'total_files_scanned': row[2],
                        'total_groups_found': row[3],
                        'total_duplicates_found': row[4],
                        'detection_time_ms': row[5],
                        'success_rate': row[9],
                        'duplicate_percentage': row[10]
                    },
                    'config': config_json,
                    'algorithm_performance': performance_json,
                    'errors': errors_json,
                    'groups': groups,
                    'created_at': row[11]
                }
                
        except Exception as e:
            self.logger.error(f"Failed to get detection results for session {session_id}: {e}")
            return None
    
    def list_detection_sessions(self, limit: int = 50) -> List[Dict[str, Any]]:
        """
        List recent detection sessions.
        
        Args:
            limit: Maximum number of sessions to return
            
        Returns:
            List of detection session summaries
        """
        try:
            db_path = self.db_session.get_bind().url.database
            with sqlite3.connect(db_path) as conn:
                cursor = conn.execute("""
                    SELECT session_id, detection_mode, total_files_scanned,
                           total_groups_found, total_duplicates_found, 
                           detection_time_ms, success_rate, created_at
                    FROM detection_results 
                    ORDER BY created_at DESC 
                    LIMIT ?
                """, (limit,))
                
                sessions = []
                for row in cursor.fetchall():
                    sessions.append({
                        'session_id': row[0],
                        'detection_mode': row[1],
                        'total_files_scanned': row[2],
                        'total_groups_found': row[3],
                        'total_duplicates_found': row[4],
                        'detection_time_ms': row[5],
                        'success_rate': row[6],
                        'created_at': row[7]
                    })
                
                return sessions
                
        except Exception as e:
            self.logger.error(f"Failed to list detection sessions: {e}")
            return []
    
    def delete_detection_session(self, session_id: str) -> bool:
        """
        Delete a detection session and all associated data.
        
        Args:
            session_id: Session ID to delete
            
        Returns:
            True if successful, False otherwise
        """
        try:
            db_path = self.db_session.get_bind().url.database
            with sqlite3.connect(db_path) as conn:
                # Delete in order to respect foreign key constraints
                conn.execute("DELETE FROM file_analysis WHERE session_id = ?", (session_id,))
                conn.execute("DELETE FROM duplicate_relationships WHERE session_id = ?", (session_id,))
                conn.execute("DELETE FROM algorithm_performance WHERE session_id = ?", (session_id,))
                conn.execute("DELETE FROM detection_config WHERE session_id = ?", (session_id,))
                
                # Delete duplicate groups and files for this session
                conn.execute("""
                    DELETE FROM duplicate_files 
                    WHERE group_id IN (
                        SELECT id FROM duplicate_groups WHERE session_id = ?
                    )
                """, (session_id,))
                conn.execute("DELETE FROM duplicate_groups WHERE session_id = ?", (session_id,))
                
                # Finally delete the main session record
                conn.execute("DELETE FROM detection_results WHERE session_id = ?", (session_id,))
                
                conn.commit()
                
            self.logger.info(f"Deleted detection session: {session_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to delete detection session {session_id}: {e}")
            return False
    
    def get_detection_statistics(self) -> Dict[str, Any]:
        """
        Get overall detection statistics.
        
        Returns:
            Dictionary with detection statistics
        """
        try:
            db_path = self.db_session.get_bind().url.database
            with sqlite3.connect(db_path) as conn:
                # Get session statistics
                cursor = conn.execute("""
                    SELECT 
                        COUNT(*) as total_sessions,
                        AVG(total_files_scanned) as avg_files_per_session,
                        AVG(total_groups_found) as avg_groups_per_session,
                        AVG(detection_time_ms) as avg_detection_time,
                        AVG(success_rate) as avg_success_rate,
                        MAX(created_at) as last_detection
                    FROM detection_results
                """)
                
                session_stats = cursor.fetchone()
                
                # Get detection mode distribution
                cursor = conn.execute("""
                    SELECT detection_mode, COUNT(*) as count
                    FROM detection_results
                    GROUP BY detection_mode
                """)
                
                mode_distribution = {row[0]: row[1] for row in cursor.fetchall()}
                
                # Get algorithm performance statistics
                cursor = conn.execute("""
                    SELECT 
                        algorithm_name,
                        AVG(files_per_second) as avg_speed,
                        AVG(error_rate) as avg_error_rate,
                        COUNT(*) as usage_count
                    FROM algorithm_performance
                    GROUP BY algorithm_name
                """)
                
                algorithm_stats = {}
                for row in cursor.fetchall():
                    algorithm_stats[row[0]] = {
                        'avg_speed': row[1],
                        'avg_error_rate': row[2],
                        'usage_count': row[3]
                    }
                
                return {
                    'session_statistics': {
                        'total_sessions': session_stats[0] or 0,
                        'avg_files_per_session': round(session_stats[1] or 0, 1),
                        'avg_groups_per_session': round(session_stats[2] or 0, 1),
                        'avg_detection_time_ms': round(session_stats[3] or 0, 1),
                        'avg_success_rate': round(session_stats[4] or 0, 1),
                        'last_detection': session_stats[5]
                    },
                    'detection_mode_distribution': mode_distribution,
                    'algorithm_performance': algorithm_stats
                }
                
        except Exception as e:
            self.logger.error(f"Failed to get detection statistics: {e}")
            return {
                'session_statistics': {},
                'detection_mode_distribution': {},
                'algorithm_performance': {}
            }
    
    def _get_files_for_detection(self, file_filters: Optional[Dict[str, Any]] = None) -> List[DuplicateFile]:
        """Get files from database for duplicate detection."""
        query = self.db_session.query(File)
        
        # Apply filters if provided
        if file_filters:
            if 'file_types' in file_filters:
                query = query.filter(File.file_type.in_(file_filters['file_types']))
            
            if 'min_size' in file_filters:
                query = query.filter(File.file_size >= file_filters['min_size'])
            
            if 'max_size' in file_filters:
                query = query.filter(File.file_size <= file_filters['max_size'])
            
            if 'path_pattern' in file_filters:
                query = query.filter(File.file_path.like(f"%{file_filters['path_pattern']}%"))
        
        # Convert to DuplicateFile objects
        duplicate_files = []
        for file in query.all():
            duplicate_file = DuplicateFile(
                file_id=file.id,
                file_path=file.file_path,
                file_name=file.file_name,
                file_size=file.file_size,
                sha256=file.sha256,
                perceptual_hash=file.perceptual_hash,
                file_type=file.file_type,
                mime_type=file.mime_type,
                width=file.width,
                height=file.height,
                created_at=file.created_at,
                modified_at=file.modified_at
            )
            duplicate_files.append(duplicate_file)
        
        return duplicate_files
    
    def _store_detection_results(self, results: DetectionResults):
        """Store detection results in database."""
        try:
            db_path = self.db_session.get_bind().url.database
            with sqlite3.connect(db_path) as conn:
                # Store main detection results
                conn.execute("""
                    INSERT INTO detection_results (
                        session_id, detection_mode, total_files_scanned,
                        total_groups_found, total_duplicates_found, detection_time_ms,
                        config_json, algorithm_performance_json, errors_json,
                        success_rate, duplicate_percentage
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    results.session_id,
                    results.detection_mode.value,
                    results.total_files_scanned,
                    results.total_groups_found,
                    results.total_duplicates_found,
                    results.detection_time_ms,
                    json.dumps(self._config_to_dict(results.config)),
                    json.dumps(results.algorithm_performance),
                    json.dumps(results.errors),
                    results.success_rate,
                    results.duplicate_percentage
                ))
                
                # Store algorithm performance data
                for algo_name, perf_data in results.algorithm_performance.items():
                    conn.execute("""
                        INSERT INTO algorithm_performance (
                            session_id, algorithm_name, files_processed,
                            execution_time_ms, groups_found, errors_encountered,
                            files_per_second, error_rate
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        results.session_id,
                        algo_name,
                        perf_data.get('files_processed', 0),
                        perf_data.get('execution_time_ms', 0),
                        perf_data.get('groups_found', 0),
                        perf_data.get('errors_encountered', 0),
                        perf_data.get('files_per_second', 0.0),
                        perf_data.get('error_rate', 0.0)
                    ))
                
                # Store duplicate groups
                for group in results.groups:
                    # Insert group
                    conn.execute("""
                        INSERT INTO duplicate_groups (
                            group_hash, duplicate_type, similarity_score,
                            detection_method, confidence_score, session_id,
                            metadata_json
                        ) VALUES (?, ?, ?, ?, ?, ?, ?)
                    """, (
                        group.id,  # Use group ID as hash
                        'exact' if group.confidence_score == 100.0 else 'similar',
                        group.similarity_percentage,
                        group.detection_method.value,
                        group.confidence_score,
                        results.session_id,
                        json.dumps(group.metadata)
                    ))
                    
                    group_db_id = conn.lastrowid
                    
                    # Insert group files
                    for file in group.files:
                        conn.execute("""
                            INSERT INTO duplicate_files (
                                group_id, file_id, is_original
                            ) VALUES (?, ?, ?)
                        """, (
                            group_db_id,
                            file.file_id,
                            file.is_original
                        ))
                
                conn.commit()
                
            self.logger.info(f"Stored detection results for session: {results.session_id}")
            
        except Exception as e:
            self.logger.error(f"Failed to store detection results: {e}")
    
    def _get_duplicate_groups_for_session(self, session_id: str, conn: sqlite3.Connection) -> List[Dict[str, Any]]:
        """Get duplicate groups for a specific session."""
        cursor = conn.execute("""
            SELECT dg.id, dg.group_hash, dg.duplicate_type, dg.similarity_score,
                   dg.detection_method, dg.confidence_score, dg.metadata_json
            FROM duplicate_groups dg
            WHERE dg.session_id = ?
            ORDER BY dg.confidence_score DESC
        """, (session_id,))
        
        groups = []
        for row in cursor.fetchall():
            group_id, group_hash, duplicate_type, similarity_score, detection_method, confidence_score, metadata_json = row
            
            # Get files for this group
            file_cursor = conn.execute("""
                SELECT f.id, f.file_path, f.file_name, f.file_size, 
                       f.file_type, df.is_original
                FROM duplicate_files df
                JOIN files f ON df.file_id = f.id
                WHERE df.group_id = ?
            """, (group_id,))
            
            files = []
            for file_row in file_cursor.fetchall():
                files.append({
                    'id': file_row[0],
                    'path': file_row[1],
                    'name': file_row[2],
                    'size': file_row[3],
                    'type': file_row[4],
                    'is_original': bool(file_row[5])
                })
            
            groups.append({
                'id': group_hash,
                'detection_method': detection_method,
                'confidence_score': confidence_score,
                'similarity_percentage': similarity_score,
                'file_count': len(files),
                'files': files,
                'metadata': json.loads(metadata_json) if metadata_json else {}
            })
        
        return groups
    
    def _config_to_dict(self, config: DetectionConfig) -> Dict[str, Any]:
        """Convert DetectionConfig to dictionary for JSON storage."""
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