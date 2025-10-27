"""
Database migration management system.
"""

import os
import sqlite3
import logging
from typing import List, Dict, Any
from pathlib import Path


class MigrationManager:
    """Manages database schema migrations."""
    
    def __init__(self, db_path: str, migrations_dir: str = None):
        self.db_path = db_path
        self.migrations_dir = migrations_dir or os.path.join(
            os.path.dirname(__file__), '..', '..', 'migrations'
        )
        self.logger = logging.getLogger(self.__class__.__name__)
    
    def ensure_migration_table(self):
        """Ensure the schema_migrations table exists."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS schema_migrations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    version TEXT NOT NULL UNIQUE,
                    description TEXT,
                    applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            conn.commit()
    
    def get_applied_migrations(self) -> List[str]:
        """Get list of applied migration versions."""
        self.ensure_migration_table()
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("SELECT version FROM schema_migrations ORDER BY version")
            return [row[0] for row in cursor.fetchall()]
    
    def get_available_migrations(self) -> List[Dict[str, str]]:
        """Get list of available migration files."""
        migrations = []
        migrations_path = Path(self.migrations_dir)
        
        if not migrations_path.exists():
            self.logger.warning(f"Migrations directory not found: {migrations_path}")
            return migrations
        
        for file_path in sorted(migrations_path.glob("*.sql")):
            # Extract version from filename (e.g., "001_enhance_duplicate_tracking.sql" -> "001")
            filename = file_path.stem
            parts = filename.split('_', 1)
            
            if len(parts) >= 2:
                version = parts[0]
                description = parts[1].replace('_', ' ').title()
                
                migrations.append({
                    'version': version,
                    'description': description,
                    'file_path': str(file_path)
                })
        
        return migrations
    
    def get_pending_migrations(self) -> List[Dict[str, str]]:
        """Get list of migrations that haven't been applied yet."""
        applied = set(self.get_applied_migrations())
        available = self.get_available_migrations()
        
        return [m for m in available if m['version'] not in applied]
    
    def apply_migration(self, migration: Dict[str, str]) -> bool:
        """
        Apply a single migration.
        
        Args:
            migration: Migration dictionary with version, description, and file_path
            
        Returns:
            True if successful, False otherwise
        """
        try:
            self.logger.info(f"Applying migration {migration['version']}: {migration['description']}")
            
            # Read migration SQL
            with open(migration['file_path'], 'r') as f:
                sql_content = f.read()
            
            # Apply migration
            with sqlite3.connect(self.db_path) as conn:
                # Enable foreign key constraints
                conn.execute("PRAGMA foreign_keys = ON")
                
                # Execute migration SQL
                conn.executescript(sql_content)
                conn.commit()
            
            self.logger.info(f"Successfully applied migration {migration['version']}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to apply migration {migration['version']}: {e}")
            return False
    
    def apply_all_pending_migrations(self) -> bool:
        """
        Apply all pending migrations.
        
        Returns:
            True if all migrations applied successfully, False otherwise
        """
        pending = self.get_pending_migrations()
        
        if not pending:
            self.logger.info("No pending migrations to apply")
            return True
        
        self.logger.info(f"Found {len(pending)} pending migrations")
        
        success_count = 0
        for migration in pending:
            if self.apply_migration(migration):
                success_count += 1
            else:
                self.logger.error(f"Migration {migration['version']} failed, stopping migration process")
                break
        
        if success_count == len(pending):
            self.logger.info(f"Successfully applied all {success_count} pending migrations")
            return True
        else:
            self.logger.error(f"Applied {success_count}/{len(pending)} migrations")
            return False
    
    def rollback_migration(self, version: str) -> bool:
        """
        Rollback a specific migration (if rollback SQL is available).
        
        Args:
            version: Version of migration to rollback
            
        Returns:
            True if successful, False otherwise
        """
        # Look for rollback file
        rollback_file = os.path.join(self.migrations_dir, f"{version}_rollback.sql")
        
        if not os.path.exists(rollback_file):
            self.logger.error(f"No rollback file found for migration {version}")
            return False
        
        try:
            self.logger.info(f"Rolling back migration {version}")
            
            # Read rollback SQL
            with open(rollback_file, 'r') as f:
                sql_content = f.read()
            
            # Apply rollback
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("PRAGMA foreign_keys = ON")
                conn.executescript(sql_content)
                
                # Remove from migrations table
                conn.execute("DELETE FROM schema_migrations WHERE version = ?", (version,))
                conn.commit()
            
            self.logger.info(f"Successfully rolled back migration {version}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to rollback migration {version}: {e}")
            return False
    
    def get_migration_status(self) -> Dict[str, Any]:
        """Get comprehensive migration status."""
        applied = self.get_applied_migrations()
        available = self.get_available_migrations()
        pending = self.get_pending_migrations()
        
        return {
            'database_path': self.db_path,
            'migrations_directory': self.migrations_dir,
            'applied_count': len(applied),
            'available_count': len(available),
            'pending_count': len(pending),
            'applied_migrations': applied,
            'pending_migrations': [m['version'] for m in pending],
            'is_up_to_date': len(pending) == 0
        }
    
    def validate_database_schema(self) -> Dict[str, Any]:
        """Validate current database schema against expected structure."""
        validation_results = {
            'valid': True,
            'issues': [],
            'table_checks': {},
            'index_checks': {}
        }
        
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Check for required tables
                required_tables = [
                    'files', 'duplicate_groups', 'duplicate_files', 'quarantine_log',
                    'detection_results', 'algorithm_performance', 'detection_config',
                    'file_analysis', 'duplicate_relationships'
                ]
                
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
                existing_tables = {row[0] for row in cursor.fetchall()}
                
                for table in required_tables:
                    if table in existing_tables:
                        validation_results['table_checks'][table] = 'exists'
                    else:
                        validation_results['table_checks'][table] = 'missing'
                        validation_results['issues'].append(f"Missing table: {table}")
                        validation_results['valid'] = False
                
                # Check for required indexes
                cursor.execute("SELECT name FROM sqlite_master WHERE type='index'")
                existing_indexes = {row[0] for row in cursor.fetchall()}
                
                required_indexes = [
                    'idx_files_sha256', 'idx_files_perceptual_hash',
                    'idx_detection_results_session', 'idx_algorithm_performance_session'
                ]
                
                for index in required_indexes:
                    if index in existing_indexes:
                        validation_results['index_checks'][index] = 'exists'
                    else:
                        validation_results['index_checks'][index] = 'missing'
                        validation_results['issues'].append(f"Missing index: {index}")
                
        except Exception as e:
            validation_results['valid'] = False
            validation_results['issues'].append(f"Database validation error: {e}")
        
        return validation_results


def init_migrations(db_path: str) -> MigrationManager:
    """Initialize migration manager and apply pending migrations."""
    manager = MigrationManager(db_path)
    
    # Apply all pending migrations
    if not manager.apply_all_pending_migrations():
        raise RuntimeError("Failed to apply database migrations")
    
    return manager