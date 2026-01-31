# Duplicate Image Preview Tool

This tool allows you to preview duplicate images locally without uploading any files to a server. It creates an HTML viewer that displays your duplicate images directly from your local file system.

## Features

- 🔍 **Local Preview**: View duplicate images without uploading to any server
- 🖼️ **Image Groups**: See duplicate images grouped by similarity
- 📊 **Metadata Display**: View file size, dimensions, and paths
- 🎯 **Multiple Detection Modes**: Exact duplicates, similar images, comprehensive analysis
- 🔄 **API Fallback**: Works with API or direct database access
- 📱 **Responsive Design**: Works on desktop and mobile browsers

## Prerequisites

1. **Install requests library** (if not already installed):
   ```bash
   pip install requests
   ```

2. **Make sure you have scanned files** using the scanner:
   ```bash
   python backend/scripts/scan_folder.py --path "/path/to/your/folder"
   ```

## Usage

### Basic Usage (Exact Duplicates)

```bash
python backend/scripts/duplicate_preview.py
```

This will:
- Connect to the API at `http://127.0.0.1:8003`
- Fetch exact duplicate detection results
- Create an HTML preview file
- Open it in your default browser

### Advanced Usage

```bash
# Show only image duplicates with similar detection
python backend/scripts/duplicate_preview.py --mode similar --images-only

# Use different confidence threshold
python backend/scripts/duplicate_preview.py --mode comprehensive --confidence 90.0

# Don't open browser automatically
python backend/scripts/duplicate_preview.py --no-browser

# Save to specific output file
python backend/scripts/duplicate_preview.py --output ~/Desktop/duplicates.html

# Use different database
python backend/scripts/duplicate_preview.py --db data/test.db

# Clean up temporary files on exit
python backend/scripts/duplicate_preview.py --cleanup
```

## Command Line Options

| Option | Description | Default |
|--------|-------------|---------|
| `--db` | Database path | `data/dev.db` |
| `--api-url` | API URL | `http://127.0.0.1:8003` |
| `--mode` | Detection mode (exact/similar/comprehensive) | `exact` |
| `--confidence` | Confidence threshold (0-100) | `80.0` |
| `--images-only` | Show only image duplicates | `False` |
| `--no-browser` | Don't open browser automatically | `False` |
| `--output` | Output HTML file path | Auto-generated |
| `--cleanup` | Clean up temporary files on exit | `False` |

## Detection Modes

### 1. Exact Mode (`--mode exact`)
- Finds files with identical SHA256 hashes
- 100% confidence (exact duplicates)
- Fastest detection method

### 2. Similar Mode (`--mode similar`)
- Finds files with similar perceptual hashes
- Good for finding visually similar images
- Adjustable confidence threshold

### 3. Comprehensive Mode (`--mode comprehensive`)
- Uses multiple detection algorithms
- Most thorough but slower
- Best for finding all types of duplicates

## How It Works

1. **Data Fetching**: The tool first tries to connect to your local API. If the API is not running, it falls back to direct database access.

2. **Image Filtering**: If `--images-only` is used, it filters to show only image files (jpg, png, gif, etc.).

3. **HTML Generation**: Creates a self-contained HTML file with embedded CSS and JavaScript.

4. **Local Display**: Uses `file://` URLs to display images directly from your local file system.

5. **Browser Opening**: Automatically opens the HTML file in your default browser.

## Security & Privacy

- ✅ **No Upload**: Images are never uploaded to any server
- ✅ **Local Only**: All processing happens on your local machine
- ✅ **File URLs**: Uses `file://` protocol to display local files
- ✅ **Temporary Files**: Creates temporary HTML files that can be cleaned up

## Troubleshooting

### "Could not connect to API"
- Make sure your backend server is running:
  ```bash
  uvicorn app.main:app --host 127.0.0.1 --port 8003
  ```
- The tool will automatically fall back to direct database access

### "No duplicate images found"
- Make sure you've scanned some files first:
  ```bash
  python backend/scripts/scan_folder.py --path "/path/to/your/folder"
  ```
- Try different detection modes or lower confidence thresholds

### "Image not accessible"
- Some browsers block `file://` URLs for security reasons
- Try opening the HTML file directly in your browser
- Make sure the image files still exist at the recorded paths

### "requests library not found"
- Install the requests library:
  ```bash
  pip install requests
  ```

## Examples

### Find exact duplicate images
```bash
python backend/scripts/duplicate_preview.py --mode exact --images-only
```

### Find similar images with 90% confidence
```bash
python backend/scripts/duplicate_preview.py --mode similar --confidence 90.0 --images-only
```

### Comprehensive analysis and save to desktop
```bash
python backend/scripts/duplicate_preview.py --mode comprehensive --output ~/Desktop/my_duplicates.html
```

### Quick preview without opening browser
```bash
python backend/scripts/duplicate_preview.py --no-browser
echo "HTML file created at: $(find /tmp -name 'duplicate_preview_*' -type d | head -1)/duplicate_preview.html"
```

## Browser Compatibility

The HTML preview works best with modern browsers:
- ✅ Chrome/Chromium
- ✅ Firefox
- ✅ Safari
- ✅ Edge

Note: Some browsers may block `file://` URLs for security reasons. If images don't load, try opening the HTML file directly in your browser.
