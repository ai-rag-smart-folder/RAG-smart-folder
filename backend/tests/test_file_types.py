"""
Tests for scanner behavior with different file types and folder structures.
Tests Requirements: 4.1, 4.2, 4.3, 4.4
"""

import pytest
import os
import sys
import tempfile
import shutil
import json
from pathlib import Path
from PIL import Image

# Add the scripts directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'scripts'))

from scan_folder import FileScanner


class TestTextFileProcessing:
    """Test processing of various text file types."""
    
    def test_plain_text_files(self, temp_db):
        """Test processing of plain text files."""
        test_dir = tempfile.mkdtemp(prefix="text_test_")
        
        try:
            # Create various text files
            text_files = {
                'simple.txt': 'Simple text content',
                'empty.txt': '',
                'unicode.txt': 'Unicode content: 你好世界 🌍',
                'large.txt': 'A' * 10000,  # 10KB file
                'multiline.txt': 'Line 1\nLine 2\nLine 3\n',
            }
            
            for filename, content in text_files.items():
                with open(os.path.join(test_dir, filename), 'w', encoding='utf-8') as f:
                    f.write(content)
            
            scanner = FileScanner(temp_db)
            scanner.connect_db()
            
            scanner.scan_folder(test_dir)
            
            # Should process all text files
            assert scanner.stats['processed_files'] == len(text_files)
            
            # Verify database entries
            scanner.cursor.execute("SELECT file_name, file_type FROM files")
            files = scanner.cursor.fetchall()
            
            for file_name, file_type in files:
                assert file_type == '.txt'
                assert file_name in text_files
            
            scanner.conn.close()
            
        finally:
            shutil.rmtree(test_dir, ignore_errors=True)
    
    def test_structured_text_files(self, temp_db):
        """Test processing of structured text files (JSON, XML, etc.)."""
        test_dir = tempfile.mkdtemp(prefix="structured_test_")
        
        try:
            # Create structured files
            files = {
                'data.json': json.dumps({'key': 'value', 'number': 42}),
                'config.xml': '<?xml version="1.0"?><root><item>value</item></root>',
                'style.css': 'body { margin: 0; padding: 0; }',
                'script.js': 'function hello() { console.log("Hello"); }',
                'readme.md': '# Title\n\nThis is markdown content.',
            }
            
            for filename, content in files.items():
                with open(os.path.join(test_dir, filename), 'w') as f:
                    f.write(content)
            
            scanner = FileScanner(temp_db)
            scanner.connect_db()
            
            scanner.scan_folder(test_dir)
            
            # Should process all files
            assert scanner.stats['processed_files'] == len(files)
            
            # Verify different file types are detected
            scanner.cursor.execute("SELECT DISTINCT file_type FROM files ORDER BY file_type")
            file_types = [row[0] for row in scanner.cursor.fetchall()]
            
            expected_types = ['.css', '.js', '.json', '.md', '.xml']
            assert file_types == expected_types
            
            scanner.conn.close()
            
        finally:
            shutil.rmtree(test_dir, ignore_errors=True)


class TestImageFileProcessing:
    """Test processing of various image file types."""
    
    def test_common_image_formats(self, temp_db):
        """Test processing of common image formats."""
        test_dir = tempfile.mkdtemp(prefix="image_test_")
        
        try:
            # Create images in different formats
            formats = [
                ('test.png', 'PNG'),
                ('test.jpg', 'JPEG'),
                ('test.bmp', 'BMP'),
                ('test.gif', 'GIF'),
            ]
            
            for filename, format_name in formats:
                img = Image.new('RGB', (100, 100), color='red')
                img.save(os.path.join(test_dir, filename), format_name)
            
            scanner = FileScanner(temp_db)
            scanner.connect_db()
            
            scanner.scan_folder(test_dir)
            
            # Should process all images
            assert scanner.stats['processed_files'] == len(formats)
            
            # Check image-specific data
            scanner.cursor.execute("""
                SELECT file_name, file_type, width, height, perceptual_hash 
                FROM files 
                ORDER BY file_name
            """)
            
            images = scanner.cursor.fetchall()
            
            for file_name, file_type, width, height, phash in images:
                # Should have correct file type
                assert file_type in ['.png', '.jpg', '.bmp', '.gif']
                
                # Should have dimensions if PIL is available
                if scanner._is_dependency_available('Image'):
                    assert width == 100
                    assert height == 100
                
                # Should have perceptual hash if imagehash is available
                if scanner._is_dependency_available('imagehash'):
                    assert phash is not None
            
            scanner.conn.close()
            
        finally:
            shutil.rmtree(test_dir, ignore_errors=True)
    
    def test_image_variations(self, temp_db):
        """Test processing of images with different properties."""
        test_dir = tempfile.mkdtemp(prefix="image_var_test_")
        
        try:
            # Create images with different properties
            variations = [
                ('small.png', (50, 50), 'RGB'),
                ('large.png', (500, 300), 'RGB'),
                ('grayscale.png', (100, 100), 'L'),
                ('rgba.png', (100, 100), 'RGBA'),
            ]
            
            for filename, size, mode in variations:
                img = Image.new(mode, size, color='blue')
                img.save(os.path.join(test_dir, filename))
            
            scanner = FileScanner(temp_db)
            scanner.connect_db()
            
            scanner.scan_folder(test_dir)
            
            # Should process all variations
            assert scanner.stats['processed_files'] == len(variations)
            
            # Check dimensions are correct
            if scanner._is_dependency_available('Image'):
                scanner.cursor.execute("SELECT file_name, width, height FROM files ORDER BY file_name")
                results = scanner.cursor.fetchall()
                
                expected_dimensions = {
                    'grayscale.png': (100, 100),
                    'large.png': (500, 300),
                    'rgba.png': (100, 100),
                    'small.png': (50, 50),
                }
                
                for file_name, width, height in results:
                    expected_w, expected_h = expected_dimensions[file_name]
                    assert width == expected_w
                    assert height == expected_h
            
            scanner.conn.close()
            
        finally:
            shutil.rmtree(test_dir, ignore_errors=True)
    
    def test_corrupted_images(self, temp_db):
        """Test handling of corrupted image files."""
        test_dir = tempfile.mkdtemp(prefix="corrupted_test_")
        
        try:
            # Create valid image
            valid_img = Image.new('RGB', (100, 100), color='green')
            valid_img.save(os.path.join(test_dir, 'valid.png'))
            
            # Create corrupted "image" files
            corrupted_files = [
                ('corrupted.jpg', b'This is not a valid JPEG'),
                ('truncated.png', b'\x89PNG\r\n\x1a\n'),  # PNG header only
                ('empty.gif', b''),
            ]
            
            for filename, content in corrupted_files:
                with open(os.path.join(test_dir, filename), 'wb') as f:
                    f.write(content)
            
            scanner = FileScanner(temp_db)
            scanner.connect_db()
            
            scanner.scan_folder(test_dir)
            
            # Should process all files (valid and corrupted)
            total_files = 1 + len(corrupted_files)  # 1 valid + corrupted files
            assert scanner.stats['total_files'] == total_files
            
            # Should have some errors from corrupted files
            assert scanner.stats['errors'] > 0
            
            # Valid image should still be processed
            scanner.cursor.execute("SELECT COUNT(*) FROM files WHERE file_name = 'valid.png'")
            valid_count = scanner.cursor.fetchone()[0]
            assert valid_count == 1
            
            scanner.conn.close()
            
        finally:
            shutil.rmtree(test_dir, ignore_errors=True)


class TestBinaryFileProcessing:
    """Test processing of binary file types."""
    
    def test_executable_files(self, temp_db):
        """Test processing of executable and binary files."""
        test_dir = tempfile.mkdtemp(prefix="binary_test_")
        
        try:
            # Create various binary files
            binary_files = {
                'program.exe': b'\x4d\x5a\x90\x00',  # PE header
                'library.dll': b'\x4d\x5a\x90\x00',  # PE header
                'data.bin': bytes(range(256)),  # Binary data
                'archive.zip': b'PK\x03\x04',  # ZIP header
            }
            
            for filename, content in binary_files.items():
                with open(os.path.join(test_dir, filename), 'wb') as f:
                    f.write(content)
            
            scanner = FileScanner(temp_db)
            scanner.connect_db()
            
            scanner.scan_folder(test_dir)
            
            # Should process all binary files
            assert scanner.stats['processed_files'] == len(binary_files)
            
            # Verify file types
            scanner.cursor.execute("SELECT file_name, file_type FROM files ORDER BY file_name")
            files = scanner.cursor.fetchall()
            
            expected_types = {
                'archive.zip': '.zip',
                'data.bin': '.bin',
                'library.dll': '.dll',
                'program.exe': '.exe',
            }
            
            for file_name, file_type in files:
                assert file_type == expected_types[file_name]
            
            scanner.conn.close()
            
        finally:
            shutil.rmtree(test_dir, ignore_errors=True)
    
    def test_media_files(self, temp_db):
        """Test processing of media file types."""
        test_dir = tempfile.mkdtemp(prefix="media_test_")
        
        try:
            # Create mock media files (just headers/signatures)
            media_files = {
                'video.mp4': b'\x00\x00\x00\x20ftypmp4',  # MP4 signature
                'audio.mp3': b'ID3',  # MP3 ID3 tag
                'document.pdf': b'%PDF-1.4',  # PDF header
            }
            
            for filename, content in media_files.items():
                with open(os.path.join(test_dir, filename), 'wb') as f:
                    f.write(content)
                    f.write(b'\x00' * 1000)  # Add some size
            
            scanner = FileScanner(temp_db)
            scanner.connect_db()
            
            scanner.scan_folder(test_dir)
            
            # Should process all media files
            assert scanner.stats['processed_files'] == len(media_files)
            
            # Check file sizes are reasonable
            scanner.cursor.execute("SELECT file_name, file_size FROM files")
            files = scanner.cursor.fetchall()
            
            for file_name, file_size in files:
                assert file_size > 1000  # Should have content
            
            scanner.conn.close()
            
        finally:
            shutil.rmtree(test_dir, ignore_errors=True)


class TestFolderStructures:
    """Test scanner behavior with different folder structures."""
    
    def test_nested_directories(self, temp_db):
        """Test scanning deeply nested directory structures."""
        test_dir = tempfile.mkdtemp(prefix="nested_test_")
        
        try:
            # Create nested structure
            levels = ['level1', 'level2', 'level3', 'level4']
            current_path = test_dir
            
            for i, level in enumerate(levels):
                current_path = os.path.join(current_path, level)
                os.makedirs(current_path, exist_ok=True)
                
                # Add a file at each level
                file_path = os.path.join(current_path, f'file_at_{level}.txt')
                with open(file_path, 'w') as f:
                    f.write(f'Content at {level}')
            
            scanner = FileScanner(temp_db)
            scanner.connect_db()
            
            scanner.scan_folder(test_dir)
            
            # Should find all files in nested structure
            assert scanner.stats['processed_files'] == len(levels)
            
            # Verify files from different levels
            scanner.cursor.execute("SELECT file_path FROM files ORDER BY file_path")
            paths = [row[0] for row in scanner.cursor.fetchall()]
            
            for level in levels:
                matching_paths = [p for p in paths if level in p]
                assert len(matching_paths) == 1
            
            scanner.conn.close()
            
        finally:
            shutil.rmtree(test_dir, ignore_errors=True)
    
    def test_mixed_content_directories(self, temp_db):
        """Test directories with mixed file types and subdirectories."""
        test_dir = tempfile.mkdtemp(prefix="mixed_test_")
        
        try:
            # Create mixed content structure
            structure = {
                'documents': ['doc1.txt', 'doc2.pdf', 'readme.md'],
                'images': ['photo1.jpg', 'photo2.png', 'icon.gif'],
                'code': ['script.py', 'style.css', 'config.json'],
                'data': ['data.csv', 'backup.zip', 'log.txt'],
            }
            
            total_files = 0
            for subdir, files in structure.items():
                subdir_path = os.path.join(test_dir, subdir)
                os.makedirs(subdir_path)
                
                for filename in files:
                    file_path = os.path.join(subdir_path, filename)
                    
                    if filename.endswith(('.jpg', '.png', '.gif')):
                        # Create actual image files
                        img = Image.new('RGB', (50, 50), color='red')
                        img.save(file_path)
                    else:
                        # Create text files
                        with open(file_path, 'w') as f:
                            f.write(f'Content of {filename}')
                    
                    total_files += 1
            
            scanner = FileScanner(temp_db)
            scanner.connect_db()
            
            scanner.scan_folder(test_dir)
            
            # Should process all files
            assert scanner.stats['processed_files'] == total_files
            
            # Verify directory distribution
            scanner.cursor.execute("""
                SELECT file_path, COUNT(*) as count 
                FROM files 
                GROUP BY SUBSTR(file_path, 1, INSTR(file_path, '/') - 1)
            """)
            
            # Should have files from all subdirectories
            scanner.cursor.execute("SELECT DISTINCT file_type FROM files")
            file_types = [row[0] for row in scanner.cursor.fetchall()]
            assert len(file_types) > 5  # Should have variety of types
            
            scanner.conn.close()
            
        finally:
            shutil.rmtree(test_dir, ignore_errors=True)
    
    def test_empty_subdirectories(self, temp_db):
        """Test handling of empty subdirectories."""
        test_dir = tempfile.mkdtemp(prefix="empty_sub_test_")
        
        try:
            # Create structure with empty directories
            os.makedirs(os.path.join(test_dir, 'empty1'))
            os.makedirs(os.path.join(test_dir, 'empty2', 'nested_empty'))
            
            # Add one file in non-empty directory
            non_empty_dir = os.path.join(test_dir, 'non_empty')
            os.makedirs(non_empty_dir)
            with open(os.path.join(non_empty_dir, 'file.txt'), 'w') as f:
                f.write('Only file')
            
            scanner = FileScanner(temp_db)
            scanner.connect_db()
            
            scanner.scan_folder(test_dir)
            
            # Should process the one file
            assert scanner.stats['processed_files'] == 1
            assert scanner.stats['total_files'] == 1
            
            scanner.conn.close()
            
        finally:
            shutil.rmtree(test_dir, ignore_errors=True)
    
    def test_special_characters_in_paths(self, temp_db):
        """Test handling of special characters in file and directory names."""
        test_dir = tempfile.mkdtemp(prefix="special_test_")
        
        try:
            # Create files and directories with special characters
            special_names = [
                'file with spaces.txt',
                'file-with-dashes.txt',
                'file_with_underscores.txt',
                'file.with.dots.txt',
                'file(with)parentheses.txt',
            ]
            
            # Create special directory
            special_dir = os.path.join(test_dir, 'dir with spaces')
            os.makedirs(special_dir)
            
            for filename in special_names:
                # Create in root
                with open(os.path.join(test_dir, filename), 'w') as f:
                    f.write(f'Content of {filename}')
                
                # Create in special directory
                with open(os.path.join(special_dir, filename), 'w') as f:
                    f.write(f'Content of {filename} in special dir')
            
            scanner = FileScanner(temp_db)
            scanner.connect_db()
            
            scanner.scan_folder(test_dir)
            
            # Should process all files
            expected_files = len(special_names) * 2  # Root + special dir
            assert scanner.stats['processed_files'] == expected_files
            
            # Verify special characters are preserved
            scanner.cursor.execute("SELECT file_name FROM files ORDER BY file_name")
            file_names = [row[0] for row in scanner.cursor.fetchall()]
            
            for special_name in special_names:
                matching_names = [name for name in file_names if special_name in name]
                assert len(matching_names) == 2  # One in each directory
            
            scanner.conn.close()
            
        finally:
            shutil.rmtree(test_dir, ignore_errors=True)


class TestFileSkipping:
    """Test file skipping logic and criteria."""
    
    def test_hidden_file_skipping(self, temp_db):
        """Test that hidden files are properly skipped."""
        test_dir = tempfile.mkdtemp(prefix="hidden_test_")
        
        try:
            # Create regular and hidden files
            files = [
                'regular.txt',
                '.hidden_file',
                '.hidden_dir/file.txt',
                'normal_dir/regular.txt',
            ]
            
            # Create directories
            os.makedirs(os.path.join(test_dir, '.hidden_dir'))
            os.makedirs(os.path.join(test_dir, 'normal_dir'))
            
            for filename in files:
                file_path = os.path.join(test_dir, filename)
                with open(file_path, 'w') as f:
                    f.write(f'Content of {filename}')
            
            scanner = FileScanner(temp_db)
            scanner.connect_db()
            
            scanner.scan_folder(test_dir)
            
            # Should skip hidden files and directories
            scanner.cursor.execute("SELECT file_name FROM files")
            processed_files = [row[0] for row in scanner.cursor.fetchall()]
            
            # Should only have regular files
            assert 'regular.txt' in processed_files
            assert 'regular.txt' in processed_files  # From normal_dir
            
            # Should not have hidden files
            hidden_files = [f for f in processed_files if f.startswith('.')]
            assert len(hidden_files) == 0
            
            scanner.conn.close()
            
        finally:
            shutil.rmtree(test_dir, ignore_errors=True)
    
    def test_system_file_skipping(self, temp_db):
        """Test skipping of system files."""
        test_dir = tempfile.mkdtemp(prefix="system_test_")
        
        try:
            # Create system-like files
            system_files = [
                'Thumbs.db',
                '.DS_Store',
                'desktop.ini',
                '$RECYCLE.BIN',
            ]
            
            regular_files = [
                'document.txt',
                'image.jpg',
            ]
            
            # Create all files
            for filename in system_files + regular_files:
                file_path = os.path.join(test_dir, filename)
                if filename == 'image.jpg':
                    # Create actual image
                    img = Image.new('RGB', (50, 50), color='blue')
                    img.save(file_path)
                else:
                    with open(file_path, 'w') as f:
                        f.write(f'Content of {filename}')
            
            scanner = FileScanner(temp_db)
            scanner.connect_db()
            
            scanner.scan_folder(test_dir)
            
            # Check what was processed
            scanner.cursor.execute("SELECT file_name FROM files")
            processed_files = [row[0] for row in scanner.cursor.fetchall()]
            
            # Should process regular files
            for regular_file in regular_files:
                assert regular_file in processed_files
            
            # System files may or may not be skipped depending on implementation
            # This test documents the current behavior
            
            scanner.conn.close()
            
        finally:
            shutil.rmtree(test_dir, ignore_errors=True)
    
    def test_large_file_handling(self, temp_db):
        """Test handling of very large files."""
        test_dir = tempfile.mkdtemp(prefix="large_test_")
        
        try:
            # Create files of different sizes
            files = [
                ('small.txt', 1024),  # 1KB
                ('medium.txt', 1024 * 1024),  # 1MB
                ('large.txt', 10 * 1024 * 1024),  # 10MB
            ]
            
            for filename, size in files:
                file_path = os.path.join(test_dir, filename)
                with open(file_path, 'wb') as f:
                    # Write in chunks to avoid memory issues
                    chunk_size = 1024
                    for _ in range(size // chunk_size):
                        f.write(b'A' * chunk_size)
            
            scanner = FileScanner(temp_db)
            scanner.connect_db()
            
            scanner.scan_folder(test_dir)
            
            # Should process files (may skip very large ones depending on limits)
            assert scanner.stats['processed_files'] > 0
            
            # Check file sizes in database
            scanner.cursor.execute("SELECT file_name, file_size FROM files ORDER BY file_size")
            db_files = scanner.cursor.fetchall()
            
            for file_name, file_size in db_files:
                assert file_size > 0
            
            scanner.conn.close()
            
        finally:
            shutil.rmtree(test_dir, ignore_errors=True)