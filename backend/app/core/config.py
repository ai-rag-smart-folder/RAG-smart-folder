from pydantic_settings import BaseSettings
from typing import Optional
import os


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # Database
    database_url: str = "sqlite:///./data/dev.db"
    
    # File processing
    max_file_size: int = 100 * 1024 * 1024  # 100MB
    supported_image_types: list = ["jpg", "jpeg", "png", "gif", "bmp", "tiff", "webp"]
    supported_document_types: list = ["pdf", "doc", "docx", "txt", "md"]
    
    # Duplicate detection
    hash_chunk_size: int = 8192  # 8KB chunks for hashing
    perceptual_hash_size: int = 8  # 8x8 for perceptual hashing
    
    # Quarantine
    quarantine_dir: str = "./quarantine"
    
    # Logging
    log_level: str = "INFO"
    log_file: str = "./logs/app.log"
    
    # API
    api_host: str = "127.0.0.1"
    api_port: int = 8003
    debug: bool = False
    
    class Config:
        env_file = ".env"
        case_sensitive = False


# Global settings instance
settings = Settings()
