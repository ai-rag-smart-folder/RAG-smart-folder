"""
Unit tests for database migration system.
"""

import pytest
import sqlite3
import tempfile
import os
from pathlib import Path
from unittest.mock import patch, mock_open

from backend.app.db.migrations import MigrationManager, init_migrations


class TestMigrationManager:
    """Test MigrationManager functionality."""
    
    def setup_method(self):
        """Setup test fixtures."""
        # Create temporary database
        self.temp_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        self.temp_db.close()
        self.db_path = self.temp_db.name
        
        # Create temporary migrations directory
        self.temp_migrations_dir = tempfile.mkdtemp()
        
        self.manager = MigrationManager(self.db_path, self.temp_migrations_dir)
    
    def teardown_method(self):
        """Cleanup test fixtures."""
        if os.path.exists(self.db_path):
            os.unlink(self.db_path)
        
        # Clean up migrations directory
        import shutil
        if os.path.exists(self.temp_migrations_dir):
            shutil.rmtree(self.temp_migrations_dir)
    
    def test_ensure_migration_table(self):
        """Test creation of schema_migrations table."""
        self.manager.ensure_migration_table()
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='schema_migrations'"
            )
            result = cursor.fetchone()
            assert result is not None
            assert result[0] == 'schema_migrations'
    
    def test_get_applied_migrations_empty(self):
        """Test getting applied migrations from empty database."""
        applied = self.manager.get_applied_migrations()
        assert applied == []
    
    def test_get_applied_migrations_with_data(self):
        """Test getting applied migrations with existing data."""
        self.manager.ensure_migration_table()
        
        # Insert test migration records
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "INSERT INTO schema_migrations (version, description) VALUES (?, ?)",
                ("001", "Test migration 1")
            )
            conn.execute(
                "INSERT INTO schema_migrations (version, description) VALUES (?, ?)",
                ("002", "Test migration 2")
            )
            conn.commit()
        
        applied = self.manager.get_applied_migrations()
        assert applied == ["001", "002"]
    
    def test_get_available_migrations(self):
        """Test getting available migration files."""
        # Create test migration files
        migration1_path = Path(self.temp_migrations_dir) / "001_first_migration.sql"
        migration2_path = Path(self.temp_migrations_dir) / "002_second_migration.sql"
        
        migration1_path.write_text("-- First migration")
        migration2_path.write_text("-- Second migration")
        
        available = self.manager.get_available_migrations()
        
        assert len(available) == 2
        assert available[0]['version'] == '001'
        assert available[0]['description'] == 'First Migration'
        assert available[1]['version'] == '002'
        assert available[1]['description'] == 'Second Migration'
    
    def test_get_available_migrations_empty_dir(self):
        """Test getting available migrations from empty directory."""
        available = self.manager.get_available_migrations()
        assert available == []
    
    def test_get_available_migrations_nonexistent_dir(self):
        """Test getting available migrations from non-existent directory."""
        manager = MigrationManager(self.db_path, "/nonexistent/path")
        available = manager.get_available_migrations()
        assert available == []
    
    def test_get_pending_migrations(self):
        """Test getting pending migrations."""
        # Create migration files
        migration1_path = Path(self.temp_migrations_dir) / "001_first_migration.sql"
        migration2_path = Path(self.temp_migrations_dir) / "002_second_migration.sql"
        
        migration1_path.write_text("-- First migration")
        migration2_path.write_text("-- Second migration")
        
        # Mark first migration as applied
        self.manager.ensure_migration_table()
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "INSERT INTO schema_migrations (version, description) VALUES (?, ?)",
                ("001", "First migration")
            )
            conn.commit()
        
        pending = self.manager.get_pending_migrations()
        
        assert len(pending) == 1
        assert pending[0]['version'] == '002'
    
    def test_apply_migration_success(self):
        """Test successful migration application."""
        # Create test migration file
        migration_path = Path(self.temp_migrations_dir) / "001_test_migration.sql"
        migration_sql = """
        CREATE TABLE test_table (
            id INTEGER PRIMARY KEY,
            name TEXT
        );
        INSERT INTO schema_migrations (version, description) 
        VALUES ('001', 'Test migration');
        """
        migration_path.write_text(migration_sql)
        
        migration = {
            'version': '001',
            'description': 'Test migration',
            'file_path': str(migration_path)
        }
        
        result = self.manager.apply_migration(migration)
        assert result is True
        
        # Verify table was created
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='test_table'"
            )
            assert cursor.fetchone() is not None
    
    def test_apply_migration_failure(self):
        """Test migration application failure."""
        # Create migration file with invalid SQL
        migration_path = Path(self.temp_migrations_dir) / "001_bad_migration.sql"
        migration_path.write_text("INVALID SQL STATEMENT;")
        
        migration = {
            'version': '001',
            'description': 'Bad migration',
            'file_path': str(migration_path)
        }
        
        result = self.manager.apply_migration(migration)
        assert result is False
    
    def test_apply_migration_file_not_found(self):
        """Test migration application with missing file."""
        migration = {
            'version': '001',
            'description': 'Missing migration',
            'file_path': '/nonexistent/migration.sql'
        }
        
        result = self.manager.apply_migration(migration)
        assert result is False
    
    def test_apply_all_pending_migrations_success(self):
        """Test applying all pending migrations successfully."""
        # Create multiple migration files
        migration1_path = Path(self.temp_migrations_dir) / "001_first.sql"
        migration2_path = Path(self.temp_migrations_dir) / "002_second.sql"
        
        migration1_sql = """
        CREATE TABLE table1 (id INTEGER PRIMARY KEY);
        INSERT INTO schema_migrations (version, description) VALUES ('001', 'First');
        """
        migration2_sql = """
        CREATE TABLE table2 (id INTEGER PRIMARY KEY);
        INSERT INTO schema_migrations (version, description) VALUES ('002', 'Second');
        """
        
        migration1_path.write_text(migration1_sql)
        migration2_path.write_text(migration2_sql)
        
        result = self.manager.apply_all_pending_migrations()
        assert result is True
        
        # Verify both tables were created
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name IN ('table1', 'table2')"
            )
            tables = [row[0] for row in cursor.fetchall()]
            assert 'table1' in tables
            assert 'table2' in tables
    
    def test_apply_all_pending_migrations_no_pending(self):
        """Test applying migrations when none are pending."""
        result = self.manager.apply_all_pending_migrations()
        assert result is True
    
    def test_apply_all_pending_migrations_partial_failure(self):
        """Test applying migrations with partial failure."""
        # Create migrations where second one fails
        migration1_path = Path(self.temp_migrations_dir) / "001_good.sql"
        migration2_path = Path(self.temp_migrations_dir) / "002_bad.sql"
        
        migration1_sql = """
        CREATE TABLE good_table (id INTEGER PRIMARY KEY);
        INSERT INTO schema_migrations (version, description) VALUES ('001', 'Good');
        """
        migration2_sql = "INVALID SQL;"
        
        migration1_path.write_text(migration1_sql)
        migration2_path.write_text(migration2_sql)
        
        result = self.manager.apply_all_pending_migrations()
        assert result is False
        
        # Verify first migration was applied but second wasn't
        applied = self.manager.get_applied_migrations()
        assert '001' in applied
        assert '002' not in applied
    
    def test_rollback_migration_success(self):
        """Test successful migration rollback."""
        # Create migration and rollback files
        migration_path = Path(self.temp_migrations_dir) / "001_test.sql"
        rollback_path = Path(self.temp_migrations_dir) / "001_rollback.sql"
        
        migration_sql = """
        CREATE TABLE test_table (id INTEGER PRIMARY KEY);
        INSERT INTO schema_migrations (version, description) VALUES ('001', 'Test');
        """
        rollback_sql = "DROP TABLE test_table;"
        
        migration_path.write_text(migration_sql)
        rollback_path.write_text(rollback_sql)
        
        # Apply migration first
        migration = {
            'version': '001',
            'description': 'Test',
            'file_path': str(migration_path)
        }
        self.manager.apply_migration(migration)
        
        # Rollback migration
        result = self.manager.rollback_migration('001')
        assert result is True
        
        # Verify table was dropped and migration record removed
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='test_table'"
            )
            assert cursor.fetchone() is None
        
        applied = self.manager.get_applied_migrations()
        assert '001' not in applied
    
    def test_rollback_migration_no_rollback_file(self):
        """Test rollback when rollback file doesn't exist."""
        result = self.manager.rollback_migration('001')
        assert result is False
    
    def test_get_migration_status(self):
        """Test getting comprehensive migration status."""
        # Create migration files
        migration1_path = Path(self.temp_migrations_dir) / "001_first.sql"
        migration2_path = Path(self.temp_migrations_dir) / "002_second.sql"
        
        migration1_path.write_text("-- First")
        migration2_path.write_text("-- Second")
        
        # Apply first migration
        self.manager.ensure_migration_table()
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "INSERT INTO schema_migrations (version, description) VALUES (?, ?)",
                ("001", "First")
            )
            conn.commit()
        
        status = self.manager.get_migration_status()
        
        assert status['applied_count'] == 1
        assert status['available_count'] == 2
        assert status['pending_count'] == 1
        assert status['applied_migrations'] == ['001']
        assert status['pending_migrations'] == ['002']
        assert status['is_up_to_date'] is False
    
    def test_get_migration_status_up_to_date(self):
        """Test migration status when up to date."""
        status = self.manager.get_migration_status()
        
        assert status['applied_count'] == 0
        assert status['available_count'] == 0
        assert status['pending_count'] == 0
        assert status['is_up_to_date'] is True
    
    def test_validate_database_schema_valid(self):
        """Test database schema validation with valid schema."""
        # Create required tables
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("CREATE TABLE files (id INTEGER PRIMARY KEY)")
            conn.execute("CREATE TABLE duplicate_groups (id INTEGER PRIMARY KEY)")
            conn.execute("CREATE TABLE duplicate_files (id INTEGER PRIMARY KEY)")
            conn.execute("CREATE TABLE quarantine_log (id INTEGER PRIMARY KEY)")
            conn.execute("CREATE TABLE detection_results (id INTEGER PRIMARY KEY)")
            conn.execute("CREATE TABLE algorithm_performance (id INTEGER PRIMARY KEY)")
            conn.execute("CREATE TABLE detection_config (id INTEGER PRIMARY KEY)")
            conn.execute("CREATE TABLE file_analysis (id INTEGER PRIMARY KEY)")
            conn.execute("CREATE TABLE duplicate_relationships (id INTEGER PRIMARY KEY)")
            
            # Create some required indexes
            conn.execute("CREATE INDEX idx_files_sha256 ON files(id)")
            conn.execute("CREATE INDEX idx_files_perceptual_hash ON files(id)")
            conn.execute("CREATE INDEX idx_detection_results_session ON detection_results(id)")
            conn.execute("CREATE INDEX idx_algorithm_performance_session ON algorithm_performance(id)")
            
            conn.commit()
        
        validation = self.manager.validate_database_schema()
        
        assert validation['valid'] is True
        assert len(validation['issues']) == 0
        assert all(status == 'exists' for status in validation['table_checks'].values())
    
    def test_validate_database_schema_missing_tables(self):
        """Test database schema validation with missing tables."""
        validation = self.manager.validate_database_schema()
        
        assert validation['valid'] is False
        assert len(validation['issues']) > 0
        assert any('Missing table' in issue for issue in validation['issues'])
    
    def test_validate_database_schema_database_error(self):
        """Test database schema validation with database error."""
        # Use invalid database path
        manager = MigrationManager("/invalid/path/db.sqlite")
        validation = manager.validate_database_schema()
        
        assert validation['valid'] is False
        assert any('Database validation error' in issue for issue in validation['issues'])


class TestInitMigrations:
    """Test init_migrations function."""
    
    def setup_method(self):
        """Setup test fixtures."""
        self.temp_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        self.temp_db.close()
        self.db_path = self.temp_db.name
    
    def teardown_method(self):
        """Cleanup test fixtures."""
        if os.path.exists(self.db_path):
            os.unlink(self.db_path)
    
    @patch('backend.app.db.migrations.MigrationManager')
    def test_init_migrations_success(self, mock_manager_class):
        """Test successful initialization of migrations."""
        mock_manager = mock_manager_class.return_value
        mock_manager.apply_all_pending_migrations.return_value = True
        
        result = init_migrations(self.db_path)
        
        assert result == mock_manager
        mock_manager_class.assert_called_once_with(self.db_path)
        mock_manager.apply_all_pending_migrations.assert_called_once()
    
    @patch('backend.app.db.migrations.MigrationManager')
    def test_init_migrations_failure(self, mock_manager_class):
        """Test initialization failure when migrations fail."""
        mock_manager = mock_manager_class.return_value
        mock_manager.apply_all_pending_migrations.return_value = False
        
        with pytest.raises(RuntimeError, match="Failed to apply database migrations"):
            init_migrations(self.db_path)