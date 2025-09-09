from sqlalchemy import Column, Integer, String, DateTime, Text, Index
from sqlalchemy.sql import func
from ..db.database import Base


class File(Base):
    """File model for storing file metadata and hashes."""
    
    __tablename__ = "files"
    
    id = Column(Integer, primary_key=True, index=True)
    file_path = Column(String, nullable=False, index=True)
    file_name = Column(String, nullable=False)
    file_size = Column(Integer)
    sha256 = Column(String(64), index=True)  # SHA-256 hash
    perceptual_hash = Column(String, index=True)  # Perceptual hash for images
    file_type = Column(String(50))
    mime_type = Column(String(100))
    width = Column(Integer)  # Image width
    height = Column(Integer)  # Image height
    created_at = Column(DateTime)
    modified_at = Column(DateTime)
    metadata_json = Column(Text)  # JSON string for additional metadata
    added_at = Column(DateTime, default=func.now())
    
    # Indexes for performance
    __table_args__ = (
        Index('idx_files_sha256', 'sha256'),
        Index('idx_files_perceptual_hash', 'perceptual_hash'),
        Index('idx_files_path', 'file_path'),
        Index('idx_files_type', 'file_type'),
    )
    
    def __repr__(self):
        return f"<File(id={self.id}, name='{self.file_name}', path='{self.file_path}')>"
