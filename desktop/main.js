const { app, BrowserWindow, dialog, ipcMain, shell } = require('electron');
const path = require('path');

let mainWindow;

function createWindow() {
    mainWindow = new BrowserWindow({
        width: 1200,
        height: 900,
        minWidth: 800,
        minHeight: 600,
        webPreferences: {
            nodeIntegration: false,
            contextIsolation: true,
            preload: path.join(__dirname, 'preload.js')
        },
        titleBarStyle: 'default',
        show: false
    });

    // Load the app
    mainWindow.loadFile('renderer/index.html');

    // Show window when ready
    mainWindow.once('ready-to-show', () => {
        mainWindow.show();
    });

    // Open external links in browser
    mainWindow.webContents.setWindowOpenHandler(({ url }) => {
        shell.openExternal(url);
        return { action: 'deny' };
    });
}

// Handle folder selection
ipcMain.handle('select-folder', async () => {
    const result = await dialog.showOpenDialog(mainWindow, {
        properties: ['openDirectory'],
        title: 'Select Folder to Scan'
    });
    
    if (!result.canceled && result.filePaths.length > 0) {
        return result.filePaths[0];
    }
    return null;
});

// Handle image loading for previews
ipcMain.handle('get-image-data-url', async (event, filePath) => {
    try {
        const fs = require('fs');
        const path = require('path');
        
        console.log('Loading image:', filePath);
        
        // Check if file exists and is readable
        if (!fs.existsSync(filePath)) {
            console.error('File does not exist:', filePath);
            throw new Error('File does not exist');
        }
        
        // Check file stats
        const stats = fs.statSync(filePath);
        if (!stats.isFile()) {
            console.error('Path is not a file:', filePath);
            throw new Error('Path is not a file');
        }
        
        console.log('File size:', stats.size, 'bytes');
        
        // Limit file size to prevent memory issues (10MB max)
        if (stats.size > 10 * 1024 * 1024) {
            console.error('File too large:', stats.size);
            throw new Error('File too large (max 10MB)');
        }
        
        // Read file and convert to base64 data URL
        const imageBuffer = fs.readFileSync(filePath);
        const ext = path.extname(filePath).toLowerCase();
        
        console.log('File extension:', ext);
        
        // Determine MIME type
        let mimeType = 'image/jpeg'; // default
        switch (ext) {
            case '.png': mimeType = 'image/png'; break;
            case '.gif': mimeType = 'image/gif'; break;
            case '.bmp': mimeType = 'image/bmp'; break;
            case '.webp': mimeType = 'image/webp'; break;
            case '.tiff':
            case '.tif': mimeType = 'image/tiff'; break;
            case '.jpg':
            case '.jpeg': mimeType = 'image/jpeg'; break;
        }
        
        const base64 = imageBuffer.toString('base64');
        const dataUrl = `data:${mimeType};base64,${base64}`;
        
        console.log('Successfully created data URL, length:', dataUrl.length);
        return dataUrl;
        
    } catch (error) {
        console.error('Error loading image:', filePath, error);
        return null;
    }
});

// Handle image existence check
ipcMain.handle('check-image-exists', async (event, filePath) => {
    try {
        const fs = require('fs');
        return fs.existsSync(filePath);
    } catch (error) {
        return false;
    }
});

// Handle app events
app.whenReady().then(() => {
    createWindow();

    app.on('activate', () => {
        if (BrowserWindow.getAllWindows().length === 0) {
            createWindow();
        }
    });
});

app.on('window-all-closed', () => {
    if (process.platform !== 'darwin') {
        app.quit();
    }
});

// Security: Prevent new window creation
app.on('web-contents-created', (event, contents) => {
    contents.on('new-window', (event, navigationUrl) => {
        event.preventDefault();
        shell.openExternal(navigationUrl);
    });
});