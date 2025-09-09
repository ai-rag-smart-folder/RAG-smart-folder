#!/usr/bin/env python3
"""
Database Migration Script for RAG Smart Folder
Adds width and height columns to the files table for image metadata storage.
"""

import sqlite3
import os
import sys
import logging
from pathlib import Path

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def check_column_exists(cursor, table_name, column_name):
    """
    Check if a column exists in the specified table.
    
    Args:
        cursor: SQLite cursor object
        table_name: Name of the table to check
        column_name: Name of the column to check for
        
    Returns:
        bool: True if column exists, False otherwise
    """
    try:
        cursor.execute(f"PRAGMA table_info({table_name})")
        columns = cursor.fetchall()
        column_names = [column[1] for column in columns]
        return column_name in column_names
    except sqlite3.Error as e:
        logger.error(f"Error checking column existence: {e}")
        return False

def add_column_if_not_exists(cursor, table_name, column_name, column_type):
    """
    Add a column to a table if it doesn't already exist.
    
    Args:
        cursor: SQLite cursor object
        table_name: Name of the table
        column_name: Name of the column to add
        column_type: SQL type of the column
        
    Returns:
        bool: True if column was added or already exists, False on error
    """
    try:
        if check_column_exists(cursor, table_name, column_name):
            logger.info(f"Column '{column_name}' already exists in table '{table_name}', skipping")
            return True
        
        # Add the column
        alter_sql = f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_type}"
        cursor.execute(alter_sql)
        logger.info(f"Successfully added column '{column_name}' to table '{table_name}'")
        return True
        
    except sqlite3.Error as e:
        logger.error(f"Error adding column '{column_name}' to table '{table_name}': {e}")
        return False

def migrate_database(db_path):
    """
    Perform database migration to add width and height columns.
    
    Args:
        db_path: Path to the SQLite database file
        
    Returns:
        bool: True if migration successful, False otherwise
    """
    if not os.path.exists(db_path):
        logger.error(f"Database file not found: {db_path}")
        return False
    
    logger.info(f"Starting migration for database: {db_path}")
    
    try:
        # Connect to database
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Check if files table exists
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='files'")
        if not cursor.fetchone():
            logger.error("Files table not found in database")
            return False
        
        # Add width column
        if not add_column_if_not_exists(cursor, 'files', 'width', 'INTEGER'):
            return False
            
        # Add height column
        if not add_column_if_not_exists(cursor, 'files', 'height', 'INTEGER'):
            return False
        
        # Commit changes
        conn.commit()
        logger.info("Migration completed successfully")
        
        # Verify the changes
        cursor.execute("PRAGMA table_info(files)")
        columns = cursor.fetchall()
        column_names = [column[1] for column in columns]
        
        if 'width' in column_names and 'height' in column_names:
            logger.info("Verification successful: width and height columns are present")
            return True
        else:
            logger.error("Verification failed: columns not found after migration")
            return False
            
    except sqlite3.Error as e:
        logger.error(f"Database error during migration: {e}")
        return False
    except Exception as e:
        logger.error(f"Unexpected error during migration: {e}")
        return False
    finally:
        if 'conn' in locals():
            conn.close()

def backup_database(db_path):
    """
    Create a backup of the database before migration.
    
    Args:
        db_path: Path to the database file
        
    Returns:
        str: Path to backup file, or None if backup failed
    """
    try:
        backup_path = f"{db_path}.backup"
        
        # Remove existing backup if it exists
        if os.path.exists(backup_path):
            os.remove(backup_path)
        
        # Create backup using SQLite's backup API
        source_conn = sqlite3.connect(db_path)
        backup_conn = sqlite3.connect(backup_path)
        
        source_conn.backup(backup_conn)
        
        source_conn.close()
        backup_conn.close()
        
        logger.info(f"Database backup created: {backup_path}")
        return backup_path
        
    except Exception as e:
        logger.error(f"Failed to create database backup: {e}")
        return None

def main():
    """Main migration function."""
    # Default database paths
    default_paths = [
        "backend/data/dev.db",
        "data/dev.db",
        "dev.db"
    ]
    
    # Check command line arguments
    if len(sys.argv) > 1:
        db_paths = sys.argv[1:]
    else:
        # Use default paths that exist
        db_paths = [path for path in default_paths if os.path.exists(path)]
        
        if not db_paths:
            logger.error("No database files found. Please specify database path as argument.")
            logger.info("Usage: python migrate_database.py [database_path1] [database_path2] ...")
            sys.exit(1)
    
    success_count = 0
    total_count = len(db_paths)
    
    for db_path in db_paths:
        logger.info(f"\n{'='*50}")
        logger.info(f"Processing database: {db_path}")
        logger.info(f"{'='*50}")
        
        # Create backup
        backup_path = backup_database(db_path)
        if not backup_path:
            logger.warning(f"Proceeding without backup for {db_path}")
        
        # Perform migration
        if migrate_database(db_path):
            success_count += 1
            logger.info(f"✓ Migration successful for {db_path}")
        else:
            logger.error(f"✗ Migration failed for {db_path}")
            if backup_path and os.path.exists(backup_path):
                logger.info(f"Backup available at: {backup_path}")
    
    # Summary
    logger.info(f"\n{'='*50}")
    logger.info(f"Migration Summary: {success_count}/{total_count} databases migrated successfully")
    logger.info(f"{'='*50}")
    
    if success_count == total_count:
        logger.info("All migrations completed successfully!")
        sys.exit(0)
    else:
        logger.error("Some migrations failed. Check logs above for details.")
        sys.exit(1)

if __name__ == "__main__":
    main()