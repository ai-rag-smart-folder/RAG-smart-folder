from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from ..core.config import settings
from ..core.logging import logger
from .migrations import init_migrations

# Create database engine
engine = create_engine(
    settings.database_url,
    connect_args={"check_same_thread": False} if "sqlite" in settings.database_url else {}
)

# Create session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Create base class for models
Base = declarative_base()


def get_db():
    """Dependency to get database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """Initialize database tables and run migrations."""
    try:
        # Create basic tables first
        Base.metadata.create_all(bind=engine)
        logger.info("Database tables created successfully")
        
        # Extract database path from URL for migrations
        db_path = settings.database_url.replace("sqlite:///", "")
        
        # Run migrations to enhance schema
        migration_manager = init_migrations(db_path)
        logger.info("Database migrations applied successfully")
        
        # Validate final schema
        validation = migration_manager.validate_database_schema()
        if not validation['valid']:
            logger.warning(f"Database schema validation issues: {validation['issues']}")
        else:
            logger.info("Database schema validation passed")
            
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        raise
