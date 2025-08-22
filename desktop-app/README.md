# RAG Smart Folder - Desktop App

A clean, native desktop application for intelligent file management with duplicate detection.

## ✨ Features

- **Native Folder Selection**: No more manual path copying - use native OS folder picker
- **Real-time Scanning**: Scan files directly from their original locations
- **Duplicate Detection**: Find exact duplicates using SHA256 hashing and similar images using perceptual hashing
- **Clean Interface**: Simplified desktop UI without browser limitations
- **Cross-platform**: Works on macOS, Windows, and Linux

## 🚀 Quick Start

### Prerequisites
- Node.js (v16 or higher)
- npm
- Backend server running in Docker on `http://127.0.0.1:8003`

### Installation

1. **Run the setup script:**
   ```bash
   ./setup.sh
   ```

2. **Or install manually:**
   ```bash
   npm install
   ```

### Running the App

1. **Make sure your Docker backend is running:**
   ```bash
   # If not already running:
   docker-compose up -d
   
   # Check if it's running:
   docker ps
   ```

2. **Start the desktop app:**
   ```bash
   npm start
   ```

## 🔧 Development

### Available Scripts

- `npm start` - Run the app in development mode
- `npm run dev` - Run with development flags
- `npm run build` - Build for current platform
- `npm run build-mac` - Build for macOS (.dmg)
- `npm run build-win` - Build for Windows (.exe)
- `npm run build-linux` - Build for Linux (AppImage)

### Project Structure

```
desktop-app/
├── main.js           # Electron main process
├── preload.js        # Secure bridge between main and renderer
├── renderer/         # Frontend files
│   ├── index.html    # Clean HTML without browser workarounds
│   ├── script.js     # Simplified JavaScript
│   └── styles.css    # Desktop-optimized styles
├── package.json      # Dependencies and build config
└── README.md         # This file
```

## 🎯 Key Improvements Over Web Version

### Removed Browser Limitations
- ❌ No more manual path input
- ❌ No more browser security workarounds
- ❌ No more path helper modals
- ❌ No more platform detection code
- ❌ No more file input hacks

### Added Desktop Features
- ✅ Native folder picker dialog
- ✅ Direct file system access
- ✅ Better performance
- ✅ Native OS integration
- ✅ Cleaner, simpler code

## 📦 Building for Distribution

### macOS
```bash
npm run build-mac
```
Creates: `dist/RAG Smart Folder-1.0.0.dmg`

### Windows
```bash
npm run build-win
```
Creates: `dist/RAG Smart Folder Setup 1.0.0.exe`

### Linux
```bash
npm run build-linux
```
Creates: `dist/RAG Smart Folder-1.0.0.AppImage`

## 🔒 Security

The app uses Electron's security best practices:
- Context isolation enabled
- Node integration disabled in renderer
- Secure preload script for API access
- External links open in default browser

## 🐛 Troubleshooting

### Backend Connection Issues
- Ensure Docker container is running: `docker ps`
- Check backend logs: `docker-compose logs rag-smart-folder`
- Verify backend is accessible: `curl http://127.0.0.1:8000/health`
- Restart if needed: `docker-compose restart rag-smart-folder`

### Build Issues
- Update Node.js to latest LTS version
- Clear npm cache: `npm cache clean --force`
- Delete `node_modules` and run `npm install` again

### App Won't Start
- Check console for errors: `npm start` shows detailed logs
- Verify all dependencies are installed
- Try running in development mode: `npm run dev`

## 📝 Changelog

### v1.0.0
- Initial desktop app release
- Native folder selection
- Removed all browser workarounds
- Clean, simplified codebase
- Cross-platform builds