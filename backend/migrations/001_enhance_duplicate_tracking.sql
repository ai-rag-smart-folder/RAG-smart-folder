-- Migration: Enhance duplicate tracking schema
-- Version: 001
-- Description: Add enhanced duplicate detection tables and update existing schema

-- Add new columns to existing duplicate_groups table
ALTER TABLE duplicate_groups ADD COLUMN detection_method TEXT;
ALTER TABLE duplicate_groups ADD COLUMN confidence_score REAL;
ALTER TABLE duplicate_groups ADD COLUMN session_id TEXT;
ALTER TABLE duplicate_groups ADD COLUMN metadata_json TEXT;

-- Create detection_results table for tracking detection sessions
CREATE TABLE IF NOT EXISTS detection_results (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT NOT NULL UNIQUE,
    detection_mode TEXT NOT NULL,
    total_files_scanned INTEGER NOT NULL DEFAULT 0,
    total_groups_found INTEGER NOT NULL DEFAULT 0,
    total_duplicates_found INTEGER NOT NULL DEFAULT 0,
    detection_time_ms INTEGER NOT NULL DEFAULT 0,
    config_json TEXT,
    algorithm_performance_json TEXT,
    errors_json TEXT,
    success_rate REAL,
    duplicate_percentage REAL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create algorithm_performance table for tracking individual algorithm metrics
CREATE TABLE IF NOT EXISTS algorithm_performance (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT NOT NULL,
    algorithm_name TEXT NOT NULL,
    files_processed INTEGER NOT NULL DEFAULT 0,
    execution_time_ms INTEGER NOT NULL DEFAULT 0,
    groups_found INTEGER NOT NULL DEFAULT 0,
    errors_encountered INTEGER NOT NULL DEFAULT 0,
    memory_usage_mb REAL,
    files_per_second REAL,
    error_rate REAL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (session_id) REFERENCES detection_results(session_id)
);

-- Create detection_config table for storing configuration snapshots
CREATE TABLE IF NOT EXISTS detection_config (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT NOT NULL,
    config_name TEXT,
    perceptual_threshold REAL,
    perceptual_hash_size INTEGER,
    metadata_fields_json TEXT,
    size_tolerance INTEGER,
    time_tolerance INTEGER,
    use_color_histogram BOOLEAN,
    use_edge_detection BOOLEAN,
    feature_weight_perceptual REAL,
    feature_weight_color REAL,
    feature_weight_edge REAL,
    min_confidence_threshold REAL,
    max_results_per_group INTEGER,
    enable_cross_algorithm_validation BOOLEAN,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (session_id) REFERENCES detection_results(session_id)
);

-- Create file_analysis table for storing detailed file analysis results
CREATE TABLE IF NOT EXISTS file_analysis (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    file_id INTEGER NOT NULL,
    session_id TEXT NOT NULL,
    analysis_type TEXT NOT NULL, -- 'hash', 'metadata', 'similarity'
    analysis_data_json TEXT,
    confidence_score REAL,
    processing_time_ms INTEGER,
    error_message TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (file_id) REFERENCES files(id),
    FOREIGN KEY (session_id) REFERENCES detection_results(session_id)
);

-- Create duplicate_relationships table for tracking relationships between files
CREATE TABLE IF NOT EXISTS duplicate_relationships (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    file1_id INTEGER NOT NULL,
    file2_id INTEGER NOT NULL,
    relationship_type TEXT NOT NULL, -- 'exact', 'similar', 'metadata'
    similarity_score REAL,
    detection_method TEXT,
    session_id TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (file1_id) REFERENCES files(id),
    FOREIGN KEY (file2_id) REFERENCES files(id),
    FOREIGN KEY (session_id) REFERENCES detection_results(session_id),
    UNIQUE(file1_id, file2_id, detection_method, session_id)
);

-- Update indexes for performance
CREATE INDEX IF NOT EXISTS idx_detection_results_session ON detection_results(session_id);
CREATE INDEX IF NOT EXISTS idx_detection_results_mode ON detection_results(detection_mode);
CREATE INDEX IF NOT EXISTS idx_detection_results_created ON detection_results(created_at);

CREATE INDEX IF NOT EXISTS idx_algorithm_performance_session ON algorithm_performance(session_id);
CREATE INDEX IF NOT EXISTS idx_algorithm_performance_algorithm ON algorithm_performance(algorithm_name);

CREATE INDEX IF NOT EXISTS idx_detection_config_session ON detection_config(session_id);

CREATE INDEX IF NOT EXISTS idx_file_analysis_file ON file_analysis(file_id);
CREATE INDEX IF NOT EXISTS idx_file_analysis_session ON file_analysis(session_id);
CREATE INDEX IF NOT EXISTS idx_file_analysis_type ON file_analysis(analysis_type);

CREATE INDEX IF NOT EXISTS idx_duplicate_relationships_file1 ON duplicate_relationships(file1_id);
CREATE INDEX IF NOT EXISTS idx_duplicate_relationships_file2 ON duplicate_relationships(file2_id);
CREATE INDEX IF NOT EXISTS idx_duplicate_relationships_session ON duplicate_relationships(session_id);
CREATE INDEX IF NOT EXISTS idx_duplicate_relationships_method ON duplicate_relationships(detection_method);

-- Update existing indexes for enhanced duplicate_groups table
CREATE INDEX IF NOT EXISTS idx_duplicate_groups_session ON duplicate_groups(session_id);
CREATE INDEX IF NOT EXISTS idx_duplicate_groups_method ON duplicate_groups(detection_method);
CREATE INDEX IF NOT EXISTS idx_duplicate_groups_confidence ON duplicate_groups(confidence_score);

-- Create view for easy duplicate analysis
CREATE VIEW IF NOT EXISTS duplicate_analysis_view AS
SELECT 
    dg.id as group_id,
    dg.group_hash,
    dg.duplicate_type,
    dg.similarity_score,
    dg.detection_method,
    dg.confidence_score,
    dg.session_id,
    COUNT(df.file_id) as file_count,
    GROUP_CONCAT(f.file_path) as file_paths,
    SUM(f.file_size) as total_size,
    AVG(f.file_size) as avg_size,
    MIN(f.created_at) as earliest_created,
    MAX(f.modified_at) as latest_modified
FROM duplicate_groups dg
LEFT JOIN duplicate_files df ON dg.id = df.group_id
LEFT JOIN files f ON df.file_id = f.id
GROUP BY dg.id;

-- Create view for detection session summary
CREATE VIEW IF NOT EXISTS detection_session_summary AS
SELECT 
    dr.session_id,
    dr.detection_mode,
    dr.total_files_scanned,
    dr.total_groups_found,
    dr.total_duplicates_found,
    dr.detection_time_ms,
    dr.success_rate,
    dr.duplicate_percentage,
    dr.created_at,
    COUNT(DISTINCT ap.algorithm_name) as algorithms_used,
    AVG(ap.files_per_second) as avg_processing_speed,
    SUM(ap.errors_encountered) as total_errors
FROM detection_results dr
LEFT JOIN algorithm_performance ap ON dr.session_id = ap.session_id
GROUP BY dr.session_id;

-- Insert migration record
INSERT OR IGNORE INTO schema_migrations (version, description, applied_at) 
VALUES ('001', 'Enhance duplicate tracking schema', CURRENT_TIMESTAMP);