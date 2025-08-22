-- RAG Smart Folder Database Schema
-- This file creates the initial database structure

-- Files table for storing file metadata
CREATE TABLE IF NOT EXISTS files (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    file_path TEXT NOT NULL,
    file_name TEXT NOT NULL,
    file_size INTEGER,
    sha256 TEXT,
    perceptual_hash TEXT,
    file_type TEXT(50),
    mime_type TEXT(100),
    created_at TIMESTAMP,
    modified_at TIMESTAMP,
    metadata_json TEXT,
    added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_files_sha256 ON files(sha256);
CREATE INDEX IF NOT EXISTS idx_files_perceptual_hash ON files(perceptual_hash);
CREATE INDEX IF NOT EXISTS idx_files_path ON files(file_path);
CREATE INDEX IF NOT EXISTS idx_files_type ON files(file_type);

-- Quarantine log table for tracking moved/removed files
CREATE TABLE IF NOT EXISTS quarantine_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    original_path TEXT NOT NULL,
    quarantine_path TEXT NOT NULL,
    action TEXT NOT NULL, -- 'moved', 'deleted'
    reason TEXT,
    file_id INTEGER,
    processed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (file_id) REFERENCES files(id)
);

-- Duplicate groups table for tracking duplicate relationships
CREATE TABLE IF NOT EXISTS duplicate_groups (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    group_hash TEXT NOT NULL, -- SHA256 or perceptual hash
    duplicate_type TEXT NOT NULL, -- 'exact', 'near', 'similar'
    similarity_score REAL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Duplicate files mapping table
CREATE TABLE IF NOT EXISTS duplicate_files (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    group_id INTEGER NOT NULL,
    file_id INTEGER NOT NULL,
    is_original BOOLEAN DEFAULT FALSE, -- Mark one as original
    FOREIGN KEY (group_id) REFERENCES duplicate_groups(id),
    FOREIGN KEY (file_id) REFERENCES files(id)
);

-- Indexes for duplicate tables
CREATE INDEX IF NOT EXISTS idx_duplicate_groups_hash ON duplicate_groups(group_hash);
CREATE INDEX IF NOT EXISTS idx_duplicate_files_group ON duplicate_files(group_id);
CREATE INDEX IF NOT EXISTS idx_duplicate_files_file ON duplicate_files(file_id);
