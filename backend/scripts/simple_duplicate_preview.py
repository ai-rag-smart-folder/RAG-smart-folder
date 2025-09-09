#!/usr/bin/env python3
"""
Simple Local Duplicate Image Preview Tool
Displays duplicate images locally without any external dependencies.
"""

import os
import sys
import sqlite3
import webbrowser
import tempfile
from pathlib import Path
from typing import List, Dict, Any, Optional
import argparse
from datetime import datetime


class SimpleDuplicatePreviewTool:
    """Simple tool for previewing duplicate images locally."""
    
    def __init__(self, db_path: str = "data/dev.db"):
        self.db_path = db_path
        self.temp_dir = None
        
    def translate_container_path_to_host(self, container_path: str) -> str:
        """Translate Docker container path to host path."""
        if not container_path:
            return container_path
        
        # Handle Docker container path translation
        if container_path.startswith('/app/host_home/'):
            # Get the user's home directory
            import os
            user_home = os.environ.get('HOME', '/Users/shankaraswal')
            if not user_home.endswith('/'):
                user_home += '/'
            return container_path.replace('/app/host_home/', user_home)
        
        # If it's already a host path, return as-is
        return container_path
        
    def get_duplicates_from_db(self, mode: str = "exact") -> Dict[str, Any]:
        """Get duplicate detection results directly from database."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Get duplicate groups
            if mode == "exact":
                # Find files with same SHA256
                cursor.execute("""
                    SELECT sha256, COUNT(*) as count, GROUP_CONCAT(id) as file_ids
                    FROM files 
                    WHERE sha256 IS NOT NULL 
                    GROUP BY sha256 
                    HAVING COUNT(*) > 1
                    ORDER BY count DESC
                """)
            else:
                # Find files with similar perceptual hashes
                cursor.execute("""
                    SELECT perceptual_hash, COUNT(*) as count, GROUP_CONCAT(id) as file_ids
                    FROM files 
                    WHERE perceptual_hash IS NOT NULL 
                    GROUP BY perceptual_hash 
                    HAVING COUNT(*) > 1
                    ORDER BY count DESC
                """)
            
            groups = []
            for row in cursor.fetchall():
                hash_value, count, file_ids_str = row
                file_ids = [int(fid) for fid in file_ids_str.split(',')]
                
                # Get file details
                placeholders = ','.join(['?' for _ in file_ids])
                cursor.execute(f"""
                    SELECT id, file_path, file_name, file_size, file_type, width, height
                    FROM files 
                    WHERE id IN ({placeholders})
                    ORDER BY file_size ASC
                """, file_ids)
                
                files = []
                min_size = None
                for file_row in cursor.fetchall():
                    file_id, file_path, file_name, file_size, file_type, width, height = file_row
                    if min_size is None or file_size < min_size:
                        min_size = file_size
                    # Translate container path to host path
                    translated_path = self.translate_container_path_to_host(file_path)
                    files.append({
                        "id": file_id,
                        "path": translated_path,
                        "name": file_name,
                        "size": file_size,
                        "type": file_type,
                        "width": width if width else None,
                        "height": height if height else None,
                        "is_original": False  # Will be set below
                    })
                
                # Mark the smallest file as original
                for file in files:
                    if file["size"] == min_size:
                        file["is_original"] = True
                
                groups.append({
                    "id": hash_value,
                    "detection_method": "sha256" if mode == "exact" else "perceptual",
                    "confidence_score": 100.0 if mode == "exact" else 85.0,
                    "similarity_percentage": 100.0 if mode == "exact" else 85.0,
                    "file_count": count,
                    "files": files
                })
            
            conn.close()
            
            return {
                "session_id": f"local_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                "detection_mode": mode,
                "summary": {
                    "total_groups_found": len(groups),
                    "total_duplicates_found": sum(len(g["files"]) for g in groups)
                },
                "duplicate_groups": groups
            }
            
        except sqlite3.Error as e:
            print(f"Database error: {e}")
            return None
    
    def filter_image_duplicates(self, duplicates_data: Dict[str, Any]) -> Dict[str, Any]:
        """Filter to only show image duplicates."""
        if not duplicates_data or "duplicate_groups" not in duplicates_data:
            return duplicates_data
        
        image_extensions = {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff', '.webp'}
        
        filtered_groups = []
        for group in duplicates_data["duplicate_groups"]:
            image_files = []
            for file in group["files"]:
                file_ext = Path(file["name"]).suffix.lower()
                if file_ext in image_extensions:
                    image_files.append(file)
            
            if len(image_files) > 1:  # Only include groups with multiple images
                filtered_groups.append({
                    **group,
                    "files": image_files,
                    "file_count": len(image_files)
                })
        
        return {
            **duplicates_data,
            "duplicate_groups": filtered_groups,
            "summary": {
                **duplicates_data.get("summary", {}),
                "total_groups_found": len(filtered_groups),
                "total_duplicates_found": sum(len(g["files"]) for g in filtered_groups)
            }
        }
    
    def create_html_preview(self, duplicates_data: Dict[str, Any], output_path: Optional[str] = None) -> str:
        """Create an HTML file to preview duplicate images locally."""
        if not duplicates_data or "duplicate_groups" not in duplicates_data:
            print("No duplicate data available.")
            return ""
        
        # Create temporary directory for HTML file
        if not self.temp_dir:
            self.temp_dir = tempfile.mkdtemp(prefix="duplicate_preview_")
        
        if not output_path:
            output_path = os.path.join(self.temp_dir, "duplicate_preview.html")
        
        html_content = self._generate_html_content(duplicates_data)
        
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        return output_path
    
    def _generate_html_content(self, duplicates_data: Dict[str, Any]) -> str:
        """Generate HTML content for the preview."""
        groups = duplicates_data.get("duplicate_groups", [])
        summary = duplicates_data.get("summary", {})
        
        html = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Duplicate Images Preview - {summary.get('total_groups_found', 0)} Groups Found</title>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: #f5f5f5;
            color: #333;
            line-height: 1.6;
        }}
        
        .header {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 2rem;
            text-align: center;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }}
        
        .header h1 {{
            font-size: 2.5rem;
            margin-bottom: 0.5rem;
        }}
        
        .header .stats {{
            font-size: 1.1rem;
            opacity: 0.9;
        }}
        
        .container {{
            max-width: 1400px;
            margin: 0 auto;
            padding: 2rem;
        }}
        
        .group {{
            background: white;
            border-radius: 12px;
            margin-bottom: 2rem;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
            overflow: hidden;
        }}
        
        .group-header {{
            background: #f8f9fa;
            padding: 1rem 1.5rem;
            border-bottom: 1px solid #e9ecef;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }}
        
        .group-info {{
            display: flex;
            gap: 1rem;
            align-items: center;
        }}
        
        .group-id {{
            font-weight: bold;
            color: #495057;
        }}
        
        .group-meta {{
            display: flex;
            gap: 1rem;
            font-size: 0.9rem;
            color: #6c757d;
        }}
        
        .confidence-badge {{
            background: #28a745;
            color: white;
            padding: 0.25rem 0.75rem;
            border-radius: 20px;
            font-size: 0.8rem;
            font-weight: bold;
        }}
        
        .images-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 1rem;
            padding: 1.5rem;
        }}
        
        .image-card {{
            background: #f8f9fa;
            border-radius: 8px;
            overflow: hidden;
            border: 2px solid transparent;
            transition: all 0.3s ease;
        }}
        
        .image-card:hover {{
            transform: translateY(-2px);
            box-shadow: 0 8px 25px rgba(0,0,0,0.15);
        }}
        
        .image-card.original {{
            border-color: #28a745;
        }}
        
        .image-container {{
            position: relative;
            width: 100%;
            height: 200px;
            overflow: hidden;
            background: #e9ecef;
        }}
        
        .image-container img {{
            width: 100%;
            height: 100%;
            object-fit: cover;
            transition: transform 0.3s ease;
        }}
        
        .image-container:hover img {{
            transform: scale(1.05);
        }}
        
        .image-info {{
            padding: 1rem;
        }}
        
        .image-name {{
            font-weight: bold;
            margin-bottom: 0.5rem;
            word-break: break-all;
        }}
        
        .image-details {{
            font-size: 0.85rem;
            color: #6c757d;
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 0.5rem;
        }}
        
        .original-badge {{
            background: #28a745;
            color: white;
            padding: 0.2rem 0.5rem;
            border-radius: 4px;
            font-size: 0.75rem;
            font-weight: bold;
            display: inline-block;
            margin-top: 0.5rem;
        }}
        
        .no-images {{
            text-align: center;
            padding: 3rem;
            color: #6c757d;
            font-style: italic;
        }}
        
        .error-message {{
            background: #f8d7da;
            color: #721c24;
            padding: 1rem;
            border-radius: 8px;
            margin: 1rem 0;
            border: 1px solid #f5c6cb;
        }}
        
        .loading {{
            text-align: center;
            padding: 2rem;
            color: #6c757d;
        }}
        
        @media (max-width: 768px) {{
            .images-grid {{
                grid-template-columns: 1fr;
            }}
            
            .header h1 {{
                font-size: 2rem;
            }}
            
            .container {{
                padding: 1rem;
            }}
        }}
    </style>
</head>
<body>
    <div class="header">
        <h1>🔍 Duplicate Images Preview</h1>
        <div class="stats">
            Found {summary.get('total_groups_found', 0)} groups with {summary.get('total_duplicates_found', 0)} duplicate images
        </div>
    </div>
    
    <div class="container">
"""
        
        if not groups:
            html += """
        <div class="no-images">
            <h2>No duplicate images found</h2>
            <p>Try adjusting the detection mode or confidence threshold.</p>
        </div>
"""
        else:
            for i, group in enumerate(groups):
                html += f"""
        <div class="group">
            <div class="group-header">
                <div class="group-info">
                    <span class="group-id">Group {i + 1}</span>
                    <div class="group-meta">
                        <span>📁 {group.get('file_count', 0)} files</span>
                        <span>🎯 {group.get('detection_method', 'unknown')}</span>
                        <span>📊 {group.get('similarity_percentage', 0):.1f}% similar</span>
                    </div>
                </div>
                <div class="confidence-badge">
                    {group.get('confidence_score', 0):.0f}% confidence
                </div>
            </div>
            
            <div class="images-grid">
"""
                
                for file in group.get('files', []):
                    is_original = file.get('is_original', False)
                    file_path = file.get('path', '')
                    file_name = file.get('name', '')
                    file_size = file.get('size', 0)
                    width = file.get('width')
                    height = file.get('height')
                    
                    # Format file size
                    if file_size:
                        if file_size < 1024:
                            size_str = f"{file_size} B"
                        elif file_size < 1024 * 1024:
                            size_str = f"{file_size / 1024:.1f} KB"
                        else:
                            size_str = f"{file_size / (1024 * 1024):.1f} MB"
                    else:
                        size_str = "Unknown"
                    
                    # Create file:// URL for local file
                    file_url = f"file://{file_path}"
                    
                    html += f"""
                <div class="image-card{' original' if is_original else ''}">
                    <div class="image-container">
                        <img src="{file_url}" alt="{file_name}" 
                             onerror="this.style.display='none'; this.parentElement.innerHTML='<div style=\\'padding: 20px; text-align: center; color: #6c757d;\\'>Image not accessible<br><small>{file_name}</small></div>';">
                    </div>
                    <div class="image-info">
                        <div class="image-name">{file_name}</div>
                        <div class="image-details">
                            <span>Size: {size_str}</span>
                            <span>Type: {file.get('type', 'Unknown')}</span>
                            {f'<span>Dimensions: {width}×{height}</span>' if width and height else ''}
                            <span>Path: {file_path}</span>
                        </div>
                        {f'<div class="original-badge">Original (smallest)</div>' if is_original else ''}
                    </div>
                </div>
"""
                
                html += """
            </div>
        </div>
"""
        
        html += """
    </div>
    
    <script>
        // Add click handlers for image expansion
        document.querySelectorAll('.image-container img').forEach(img => {
            img.addEventListener('click', function() {
                if (this.style.transform === 'scale(1.5)') {
                    this.style.transform = 'scale(1.05)';
                    this.style.cursor = 'zoom-in';
                } else {
                    this.style.transform = 'scale(1.5)';
                    this.style.cursor = 'zoom-out';
                }
            });
            
            img.style.cursor = 'zoom-in';
        });
        
        // Add keyboard shortcuts
        document.addEventListener('keydown', function(e) {
            if (e.key === 'Escape') {
                document.querySelectorAll('.image-container img').forEach(img => {
                    img.style.transform = 'scale(1.05)';
                    img.style.cursor = 'zoom-in';
                });
            }
        });
    </script>
</body>
</html>
"""
        
        return html
    
    def open_preview(self, html_path: str):
        """Open the HTML preview in the default browser."""
        try:
            webbrowser.open(f"file://{html_path}")
            print(f"✅ Preview opened in browser: {html_path}")
        except Exception as e:
            print(f"❌ Could not open browser automatically: {e}")
            print(f"Please open this file manually: {html_path}")
    
    def cleanup(self):
        """Clean up temporary files."""
        if self.temp_dir and os.path.exists(self.temp_dir):
            try:
                import shutil
                shutil.rmtree(self.temp_dir)
                print("🧹 Temporary files cleaned up")
            except Exception as e:
                print(f"Warning: Could not clean up temporary files: {e}")


def main():
    parser = argparse.ArgumentParser(description="Simple Local Duplicate Image Preview Tool")
    parser.add_argument("--db", default="data/dev.db", help="Database path")
    parser.add_argument("--mode", choices=["exact", "similar"], default="exact", 
                       help="Detection mode")
    parser.add_argument("--images-only", action="store_true", help="Show only image duplicates")
    parser.add_argument("--no-browser", action="store_true", help="Don't open browser automatically")
    parser.add_argument("--output", help="Output HTML file path")
    parser.add_argument("--cleanup", action="store_true", help="Clean up temporary files on exit")
    
    args = parser.parse_args()
    
    tool = SimpleDuplicatePreviewTool(db_path=args.db)
    
    try:
        print("🔍 Fetching duplicate detection results from database...")
        
        # Get duplicates directly from database
        duplicates_data = tool.get_duplicates_from_db(args.mode)
        
        if not duplicates_data:
            print("❌ No duplicate data found. Make sure you've scanned some files first.")
            return
        
        if args.images_only:
            duplicates_data = tool.filter_image_duplicates(duplicates_data)
        
        if not duplicates_data.get("duplicate_groups"):
            print("❌ No duplicate images found.")
            return
        
        print(f"✅ Found {len(duplicates_data['duplicate_groups'])} duplicate groups")
        
        # Create HTML preview
        html_path = tool.create_html_preview(duplicates_data, args.output)
        
        if html_path:
            print(f"📄 HTML preview created: {html_path}")
            
            if not args.no_browser:
                tool.open_preview(html_path)
            else:
                print(f"Open this file in your browser: {html_path}")
        
    except KeyboardInterrupt:
        print("\n⏹️  Operation cancelled by user")
    except Exception as e:
        print(f"❌ Error: {e}")
    finally:
        if args.cleanup:
            tool.cleanup()


if __name__ == "__main__":
    main()
