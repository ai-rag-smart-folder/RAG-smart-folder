# RAG Smart Folder - Desktop App

An Electron-based desktop application for intelligent file management with duplicate detection.

## Features

- 🖥️ **Native Desktop App**: Cross-platform Electron application
- 📁 **Folder Selection**: Native folder picker with full file system access
- 🔍 **Real-time Scanning**: Live progress updates during folder scanning
- 📊 **Results Dashboard**: Comprehensive view of scanned files and duplicates
- 🎯 **Duplicate Detection**: Visual duplicate file grouping and management
- ⚡ **Fast Performance**: Optimized UI with minimal resource usage

## Screenshots

The desktop app provides:
- Clean, modern interface
- Native folder selection dialog
- Real-time scan progress
- Detailed file listings
- Duplicate file grouping
- Status logging

## Prerequisites

- **Node.js** (v16 or higher)
- **Backend API** running on http://localhost:8003
  - See [backend](https://github.com/yourusername/backend)

## Quick Start

### Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/yourusername/desktop.git
   cd desktop
   ```

2. **Install dependencies**
   ```bash
   npm install
   ```

3. **Start the backend API**
   ```bash
   # Make sure the backend is running on http://localhost:8003
   # See backend repository for setup instructions
   ```

4. **Run the desktop app**
   ```bash
   npm start
   ```

### Building for Distribution

```bash
# Build for current platform
npm run build

# Build for all platforms
npm run build:all

# Build for specific platforms
npm run build:mac
npm run build:win
npm run build:linux
```

## Usage

1. **Launch the app** - The desktop application will start
2. **Check backend connection** - Ensure the status shows "Backend connected"
3. **Select folder** - Click "Select Folder" to choose a directory to scan
4. **Configure options**:
   - ✅ Recursive scanning (scan subdirectories)
   - ✅ Find duplicates (detect duplicate files)
   - ✅ Clear previous data (start fresh)
5. **Start scan** - Click "Scan" to begin the process
6. **View results** - Browse files and duplicates in the results tabs

## Configuration

### Backend API URL
The app connects to the backend API at `http://127.0.0.1:8003` by default. To change this:

1. Edit `renderer/script.js`
2. Update the `apiBase` property:
   ```javascript
   this.apiBase = 'http://your-backend-url:port';
   ```

### Window Settings
Customize the app window in `main.js`:
```javascript
const mainWindow = new BrowserWindow({
  width: 1200,
  height: 800,
  // ... other options
});
```

## Architecture

```
desktop-app/
├── main.js                 # Electron main process
├── preload.js             # Preload script for security
├── package.json           # Dependencies and build config
└── renderer/
    ├── index.html         # Main UI
    ├── script.js          # Frontend logic
    └── styles.css         # Styling
```

## Key Features

### Native Folder Access
Unlike web applications, the desktop app can:
- Access any folder on your system
- Read file paths directly
- No browser security restrictions
- Native file system integration

### Real-time Updates
- Live scan progress
- Instant result updates
- Status logging
- Error handling

### Cross-platform Support
- **macOS**: Native .app bundle
- **Windows**: .exe installer
- **Linux**: AppImage, deb, rpm packages

## API Integration

The desktop app communicates with the backend API:

```javascript
// Scan a folder
const response = await fetch(`${this.apiBase}/scan`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
        folder_path: this.selectedFolderPath,
        recursive: true,
        find_duplicates: true,
        clear_previous: true
    })
});
```

## Development

### Project Structure
- **Main Process** (`main.js`): Handles app lifecycle, window management
- **Preload Script** (`preload.js`): Secure bridge between main and renderer
- **Renderer Process** (`renderer/`): UI and user interaction logic

### Security
The app follows Electron security best practices:
- Context isolation enabled
- Node integration disabled in renderer
- Secure preload script for API exposure

### Debugging
```bash
# Run with developer tools
npm run dev

# Enable verbose logging
DEBUG=* npm start
```

## Building and Distribution

### Package Scripts
```json
{
  "start": "electron .",
  "dev": "electron . --enable-logging",
  "build": "electron-builder",
  "build:mac": "electron-builder --mac",
  "build:win": "electron-builder --win",
  "build:linux": "electron-builder --linux"
}
```

### Distribution Files
After building, you'll find:
- **macOS**: `.dmg` installer and `.app` bundle
- **Windows**: `.exe` installer and portable version
- **Linux**: `.AppImage`, `.deb`, `.rpm` packages

## Troubleshooting

### Backend Connection Issues
- Ensure backend is running on http://localhost:8003
- Check firewall settings
- Verify API health at http://localhost:8003/health

### Folder Access Issues
- On macOS: Grant Full Disk Access in System Preferences
- On Windows: Run as administrator if needed
- Check folder permissions

### Build Issues
- Clear node_modules: `rm -rf node_modules && npm install`
- Update Electron: `npm update electron`
- Check platform-specific build requirements

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test on multiple platforms
5. Submit a pull request

## License

MIT License - see LICENSE file for details.