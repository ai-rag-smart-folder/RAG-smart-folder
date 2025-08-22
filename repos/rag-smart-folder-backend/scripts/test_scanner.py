#!/usr/bin/env python3
"""
Test script for the file scanner.
Creates a small test folder and runs the scanner on it.
"""

import os
import tempfile
import shutil
from pathlib import Path


def create_test_files():
    """Create a temporary test folder with some files."""
    test_dir = tempfile.mkdtemp(prefix="rag_test_")
    print(f"Created test directory: {test_dir}")
    
    # Create some test files
    test_files = [
        ("test1.txt", "This is test file 1"),
        ("test2.txt", "This is test file 2"),
        ("duplicate1.txt", "This is duplicate content"),
        ("duplicate2.txt", "This is duplicate content"),  # Same content as duplicate1
        ("unique.txt", "This is unique content"),
    ]
    
    for filename, content in test_files:
        file_path = os.path.join(test_dir, filename)
        with open(file_path, 'w') as f:
            f.write(content)
        print(f"Created: {filename}")
    
    # Create a subdirectory with more files
    subdir = os.path.join(test_dir, "subfolder")
    os.makedirs(subdir, exist_ok=True)
    
    sub_files = [
        ("sub1.txt", "Subfolder file 1"),
        ("sub2.txt", "Subfolder file 2"),
    ]
    
    for filename, content in sub_files:
        file_path = os.path.join(subdir, filename)
        with open(file_path, 'w') as f:
            f.write(content)
        print(f"Created: {os.path.join('subfolder', filename)}")
    
    return test_dir


def main():
    """Main test function."""
    print("🧪 Testing RAG Smart Folder Scanner")
    print("=" * 40)
    
    # Create test files
    test_dir = create_test_files()
    
    print(f"\n📁 Test directory created: {test_dir}")
    print("\nTo test the scanner, run:")
    print(f"python scripts/scan_folder.py --path '{test_dir}' --db 'data/dev.db' --duplicates")
    
    print(f"\nTo clean up test files, run:")
    print(f"rm -rf '{test_dir}'")
    
    print(f"\nTo start the FastAPI server, run:")
    print("cd backend && python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000")
    
    print(f"\nThen visit: http://127.0.0.1:8000")
    print(f"API docs: http://127.0.0.1:8000/docs")


if __name__ == "__main__":
    main()
