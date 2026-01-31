# Database Migration Script

## Overview

The `migrate_database.py` script adds the required `width` and `height` columns to existing RAG Smart Folder databases. This migration is necessary to support image metadata storage in the file scanning functionality.

## Usage

### Basic Usage

```bash
# Migrate specific database file
python3 backend/scripts/migrate_database.py path/to/database.db

# Migrate multiple databases
python3 backend/scripts/migrate_database.py db1.db db2.db db3.db

# Auto-discover and migrate all databases in standard locations
python3 backend/scripts/migrate_database.py
```

### Standard Database Locations

The script automatically looks for databases in these locations when run without arguments:
- `backend/data/dev.db`
- `data/dev.db`
- `dev.db`

## Features

- **Safe Migration**: Creates automatic backups before making changes
- **Duplicate Prevention**: Checks if columns already exist before adding them
- **Multiple Database Support**: Can migrate multiple databases in one run
- **Comprehensive Logging**: Detailed logging of all operations
- **Verification**: Confirms successful migration after completion
- **Error Handling**: Graceful handling of various error conditions

## What It Does

1. **Backup Creation**: Creates a `.backup` file for each database
2. **Column Addition**: Adds `width INTEGER` and `height INTEGER` columns to the `files` table
3. **Verification**: Confirms the columns were added successfully
4. **Reporting**: Provides detailed success/failure reporting

## Requirements

- Python 3.x
- SQLite3 (included with Python)
- Write access to database files and their directories

## Safety Features

- **Automatic Backups**: Each database is backed up before migration
- **Idempotent**: Can be run multiple times safely (won't duplicate columns)
- **Validation**: Checks for table existence before attempting migration
- **Error Recovery**: Provides backup file location if migration fails

## Example Output

```
==================================================
Processing database: backend/data/dev.db
==================================================
Database backup created: backend/data/dev.db.backup
Starting migration for database: backend/data/dev.db
Successfully added column 'width' to table 'files'
Successfully added column 'height' to table 'files'
Migration completed successfully
Verification successful: width and height columns are present
✓ Migration successful for backend/data/dev.db

==================================================
Migration Summary: 1/1 databases migrated successfully
==================================================
All migrations completed successfully!
```

## Troubleshooting

- **Permission Errors**: Ensure write access to database files and directories
- **Missing Database**: Check that the database file exists and path is correct
- **Backup Failures**: Ensure sufficient disk space for backup files
- **Column Already Exists**: This is normal - the script will skip existing columns

## Recovery

If migration fails, restore from the automatically created backup:
```bash
cp database.db.backup database.db
```