// RAG Smart Folder - Minimal Desktop App

class RAGSmartFolder {
    constructor() {
        this.apiBase = 'http://127.0.0.1:8003';
        this.selectedFolderPath = '';
        this.scanStartTime = null;
        this.imageFiles = [];
        this.similarImages = [];
        
        this.initializeEventListeners();
        this.checkAPIConnection();
    }

    translateContainerPathToHost(containerPath) {
        // Translate Docker container path to host path for desktop app
        if (!containerPath) {
            return containerPath;
        }
        
        // Handle Docker container path translation
        if (containerPath.startsWith('/app/host_home/')) {
            // Get the user's home directory - this should match your local machine
            const userHome = '/Users/shankaraswal'; // Hardcoded for your system
            return containerPath.replace('/app/host_home/', userHome + '/');
        }
        
        // If it's already a host path, return as-is
        return containerPath;
    }

    translateHostPathToContainer(hostPath) {
        // Translate host path to Docker container path for API calls
        if (!hostPath) {
            return hostPath;
        }
        
        // Handle host path to container path translation
        if (hostPath.startsWith('/Users/shankaraswal/')) {
            return hostPath.replace('/Users/shankaraswal/', '/app/host_home/');
        }
        
        // If it's already a container path or doesn't match our pattern, return as-is
        return hostPath;
    }

    initializeEventListeners() {
        document.getElementById('selectFolderBtn').addEventListener('click', () => this.selectFolder());
        document.getElementById('scanDuplicatesBtn').addEventListener('click', () => this.startDuplicateScan());
        document.getElementById('scanSimilarityBtn').addEventListener('click', () => this.startSimilarityScan());
        document.getElementById('clearButton').addEventListener('click', () => this.clearDatabase());
        document.getElementById('testImageBtn').addEventListener('click', () => this.testImageLoading());
        
        document.querySelectorAll('.tab-btn').forEach(btn => {
            btn.addEventListener('click', (e) => this.switchTab(e.target.dataset.tab));
        });
        
        // Image modal listeners
        document.getElementById('modalClose').addEventListener('click', () => this.closeImageModal());
        document.getElementById('imageModal').addEventListener('click', (e) => {
            if (e.target.id === 'imageModal') this.closeImageModal();
        });
        
        // Keyboard navigation
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape') this.closeImageModal();
        });
        
        // Similarity controls
        const similaritySlider = document.getElementById('similaritySlider');
        const similarityValue = document.getElementById('similarityValue');
        
        similaritySlider.addEventListener('input', (e) => {
            similarityValue.textContent = `${e.target.value}%`;
        });
        
        document.getElementById('refreshSimilarity').addEventListener('click', async () => {
            await this.loadSimilarImages();
        });
        
        // Scan mode selection
        document.querySelectorAll('input[name="scanMode"]').forEach(radio => {
            radio.addEventListener('change', () => this.handleScanModeChange());
        });
        
        // Similarity threshold slider
        const scanSimilaritySlider = document.getElementById('scanSimilaritySlider');
        const scanSimilarityValue = document.getElementById('scanSimilarityValue');
        
        scanSimilaritySlider.addEventListener('input', (e) => {
            scanSimilarityValue.textContent = `${e.target.value}%`;
        });
    }

    async selectFolder() {
        try {
            const folderPath = await window.electronAPI.selectFolder();
            
            if (folderPath) {
                this.selectedFolderPath = folderPath;
                document.getElementById('selectedPath').textContent = folderPath;
                document.getElementById('scanDuplicatesBtn').disabled = false;
                document.getElementById('scanSimilarityBtn').disabled = false;
                this.handleScanModeChange(); // Update button visibility
                this.log(`Selected: ${folderPath}`, 'success');
            }
        } catch (error) {
            this.log(`Failed to select folder: ${error.message}`, 'error');
        }
    }

    async checkAPIConnection() {
        try {
            const response = await fetch(`${this.apiBase}/health`);
            if (response.ok) {
                this.log('Backend connected', 'success');
                
                // Test scanner connection
                const scannerTest = await fetch(`${this.apiBase}/scan/test-connection`);
                const scannerResult = await scannerTest.json();
                
                if (scannerResult.scanner_available) {
                    this.log('Scanner ready', 'success');
                } else {
                    this.log('Scanner not available - check dependencies', 'error');
                }
            } else {
                throw new Error('API not responding');
            }
        } catch (error) {
            this.log('Backend not available - make sure Docker is running', 'error');
        }
    }

    async clearDatabase() {
        if (!confirm('Clear all scan data?')) return;

        const btn = document.getElementById('clearButton');
        const originalText = btn.textContent;
        
        try {
            btn.disabled = true;
            btn.textContent = 'Clearing...';
            
            const response = await fetch(`${this.apiBase}/clear`, { method: 'DELETE' });
            const result = await response.json();
            
            this.log(`Cleared ${result.files_removed} files`, 'success');
            document.getElementById('resultsSection').style.display = 'none';
            this.resetStats();
            
        } catch (error) {
            this.log(`Clear failed: ${error.message}`, 'error');
        } finally {
            btn.disabled = false;
            btn.textContent = originalText;
        }
    }

    handleScanModeChange() {
        const selectedMode = document.querySelector('input[name="scanMode"]:checked').value;
        const similaritySettings = document.getElementById('similaritySettings');
        const duplicatesBtn = document.getElementById('scanDuplicatesBtn');
        const similarityBtn = document.getElementById('scanSimilarityBtn');
        
        if (selectedMode === 'similarity') {
            similaritySettings.style.display = 'block';
            duplicatesBtn.style.display = 'none';
            similarityBtn.style.display = 'inline-block';
        } else {
            similaritySettings.style.display = 'none';
            duplicatesBtn.style.display = 'inline-block';
            similarityBtn.style.display = 'none';
        }
    }

    async startDuplicateScan() {
        if (!this.selectedFolderPath) {
            this.log('Please select a folder first', 'error');
            return;
        }

        const btn = document.getElementById('scanDuplicatesBtn');
        const btnText = btn.querySelector('.btn-text');
        const btnLoader = btn.querySelector('.btn-loader');

        btn.disabled = true;
        btnText.style.display = 'none';
        btnLoader.style.display = 'inline-block';

        this.scanStartTime = Date.now();
        this.log('Starting duplicate scan...', 'info');

        try {
            // Translate host path to container path for API
            const containerPath = this.translateHostPathToContainer(this.selectedFolderPath);
            console.log('Sending scan request with path:', containerPath);

            const response = await fetch(`${this.apiBase}/scan`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    folder_path: containerPath,
                    recursive: document.getElementById('recursiveCheck').checked,
                    find_duplicates: true,
                    clear_previous: document.getElementById('clearPrevious').checked,
                    scan_mode: 'duplicates'
                })
            });

            if (!response.ok) {
                const error = await response.json();
                throw new Error(error.detail || 'Duplicate scan failed');
            }

            const result = await response.json();

            if (result.status === 'success') {
                this.log(result.message, 'success');

                // Display enhanced statistics if available
                if (result.statistics) {
                    const stats = result.statistics;
                    this.log(`Processed: ${stats.processed_files}/${stats.total_files} files (${stats.success_rate.toFixed(1)}% success rate)`, 'info');
                    if (stats.errors > 0) {
                        this.log(`Encountered ${stats.errors} errors during scan`, 'warning');
                    }
                    if (stats.skipped_files > 0) {
                        this.log(`Skipped ${stats.skipped_files} files`, 'info');
                    }
                }

                // Force reload results after scan
                setTimeout(async () => {
                    await this.loadResults();
                    await this.loadSimilarImages();
                }, 500); // Small delay to ensure backend processing is complete

                const scanTime = ((Date.now() - this.scanStartTime) / 1000).toFixed(1);
                this.log(`Duplicate scan completed in ${scanTime}s`, 'success');
            } else {
                // Handle scan with errors
                this.log(result.message || 'Scan completed with errors', 'warning');
                if (result.statistics) {
                    const stats = result.statistics;
                    this.log(`Partial results: ${stats.processed_files}/${stats.total_files} files processed`, 'info');
                }
                if (result.error_details) {
                    this.log('Check console for detailed error information', 'error');
                    console.error('Scan errors:', result.error_details);
                }
            }

        } catch (error) {
            this.log(`Duplicate scan failed: ${error.message}`, 'error');
        } finally {
            btn.disabled = false;
            btnText.style.display = 'inline-block';
            btnLoader.style.display = 'none';
        }
    }

    async startSimilarityScan() {
        if (!this.selectedFolderPath) {
            this.log('Please select a folder first', 'error');
            return;
        }

        const btn = document.getElementById('scanSimilarityBtn');
        const btnText = btn.querySelector('.btn-text');
        const btnLoader = btn.querySelector('.btn-loader');
        const threshold = document.getElementById('scanSimilaritySlider').value;

        btn.disabled = true;
        btnText.style.display = 'none';
        btnLoader.style.display = 'inline-block';

        this.scanStartTime = Date.now();
        this.log(`Starting similarity scan with ${threshold}% threshold...`, 'info');

        try {
            // Translate host path to container path for API
            const containerPath = this.translateHostPathToContainer(this.selectedFolderPath);
            console.log('Sending similarity scan request with path:', containerPath);

            const response = await fetch(`${this.apiBase}/scan`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    folder_path: containerPath,
                    recursive: document.getElementById('recursiveCheck').checked,
                    find_duplicates: false,
                    clear_previous: document.getElementById('clearPrevious').checked,
                    scan_mode: 'similarity',
                    similarity_threshold: parseFloat(threshold)
                })
            });

            if (!response.ok) {
                const error = await response.json();
                throw new Error(error.detail || 'Similarity scan failed');
            }

            const result = await response.json();

            if (result.status === 'success') {
                this.log(result.message, 'success');

                // Display enhanced statistics if available
                if (result.statistics) {
                    const stats = result.statistics;
                    this.log(`Processed: ${stats.processed_files}/${stats.total_files} files (${stats.success_rate.toFixed(1)}% success rate)`, 'info');
                    if (stats.errors > 0) {
                        this.log(`Encountered ${stats.errors} errors during scan`, 'warning');
                    }
                    if (stats.skipped_files > 0) {
                        this.log(`Skipped ${stats.skipped_files} files`, 'info');
                    }
                }

                // Force reload all results after similarity scan
                setTimeout(async () => {
                    await this.loadResults();
                    await this.loadSimilarImages();
                }, 500); // Small delay to ensure backend processing is complete

                const scanTime = ((Date.now() - this.scanStartTime) / 1000).toFixed(1);
                this.log(`Similarity scan completed in ${scanTime}s`, 'success');

                // Switch to similar images tab
                this.switchTab('similar');
            } else {
                // Handle scan with errors
                this.log(result.message || 'Similarity scan completed with errors', 'warning');
                if (result.statistics) {
                    const stats = result.statistics;
                    this.log(`Partial results: ${stats.processed_files}/${stats.total_files} files processed`, 'info');
                }
                if (result.error_details) {
                    this.log('Check console for detailed error information', 'error');
                    console.error('Scan errors:', result.error_details);
                }
            }

        } catch (error) {
            this.log(`Similarity scan failed: ${error.message}`, 'error');
        } finally {
            btn.disabled = false;
            btnText.style.display = 'inline-block';
            btnLoader.style.display = 'none';
        }
    }

    async loadResults() {
        try {
            this.log('Loading results from API...', 'info');

            const [filesResponse, duplicatesResponse, imagesResponse, statsResponse] = await Promise.all([
                fetch(`${this.apiBase}/files`),
                fetch(`${this.apiBase}/duplicates`),
                fetch(`${this.apiBase}/images?similarity_threshold=80`),
                fetch(`${this.apiBase}/scan/statistics`)
            ]);

            const filesData = await filesResponse.json();
            this.log(`Files API: ${filesData.total_files || 0} files`, 'info');

            const duplicatesData = await duplicatesResponse.json();
            this.log(`Duplicates API: ${duplicatesData.duplicate_groups?.length || 0} groups`, 'info');

            const imagesData = imagesResponse.ok ? await imagesResponse.json() : { images: [], similar_images: [] };
            this.log(`Images API: ${imagesData.total_images || 0} images, ${imagesData.similar_groups || 0} similar groups`, 'info');

            const statsData = statsResponse.ok ? await statsResponse.json() : null;
            this.log(`Stats API: ${statsData ? 'Available' : 'Not available'}`, 'info');

            console.log('Files data:', filesData);
            console.log('Duplicates data:', duplicatesData);
            console.log('Images data:', imagesData);

            await this.displayResults(filesData, duplicatesData, imagesData, statsData);

            this.log('Results loaded successfully', 'success');

        } catch (error) {
            this.log(`Failed to load results: ${error.message}`, 'error');
            console.error('Load results error:', error);
        }
    }
    
    async loadSimilarImages() {
        try {
            const threshold = document.getElementById('similaritySlider').value;
            this.log(`Loading similar images with ${threshold}% threshold...`, 'info');

            const response = await fetch(`${this.apiBase}/images?similarity_threshold=${threshold}`);
            const imagesData = await response.json();

            console.log('Similar images data:', imagesData);

            this.displaySimilarImages(imagesData.similar_images || []);
            this.log(`Found ${imagesData.similar_groups || 0} similar groups`, 'success');

        } catch (error) {
            this.log(`Failed to load similar images: ${error.message}`, 'error');
            console.error('Load similar images error:', error);
        }
    }

    async displayResults(filesData, duplicatesData, imagesData = {}, statsData = null) {
        const totalSize = filesData.files?.reduce((sum, file) => sum + (file.size || 0), 0) || 0;
        const scanTime = this.scanStartTime ? ((Date.now() - this.scanStartTime) / 1000).toFixed(1) : '0';
        
        // Use enhanced statistics if available
        if (statsData && statsData.database_statistics) {
            const dbStats = statsData.database_statistics;
            const sizeStats = statsData.size_statistics;

            document.getElementById('totalFiles').textContent = dbStats.total_files || 0;
            document.getElementById('duplicateGroups').textContent = dbStats.total_duplicates || 0;
            document.getElementById('totalSize').textContent = this.formatFileSize(sizeStats.total_size || totalSize);
            document.getElementById('scanTime').textContent = `${scanTime}s`;

            // Log enhanced statistics
            if (dbStats.total_images > 0) {
                this.log(`Found ${dbStats.total_images} images (${dbStats.images_with_perceptual_hash} with perceptual hashes)`, 'info');
            }
            if (dbStats.duplicate_files > 0) {
                this.log(`${dbStats.duplicate_files} duplicate files in ${dbStats.total_duplicates} groups`, 'info');
            }
        } else {
            // Fallback to basic statistics
            document.getElementById('totalFiles').textContent = filesData.total_files || 0;
            document.getElementById('duplicateGroups').textContent = duplicatesData.total_duplicate_groups || 0;
            document.getElementById('totalSize').textContent = this.formatFileSize(totalSize);
            document.getElementById('scanTime').textContent = `${scanTime}s`;
        }
        
        this.displayFilesList(filesData.files || []);
        // this.displayDuplicatesList(duplicatesData.duplicates || []);
        // await this.displayImagesList(imagesData.images || [], imagesData.similar_images || []);
        // this.displaySimilarImages(imagesData.similar_images || []);
        
        document.getElementById('resultsSection').style.display = 'block';
    }

    displayFilesList(files) {
        const list = document.getElementById('filesList');
        list.innerHTML = files.length === 0 ? '<div class="file-item">No files found</div>' : '';

        files.forEach(file => {
            const item = document.createElement('div');
            item.className = 'file-item';

            // Check if this is an image file
            const isImage = this.isImageFile(file.name);

            if (isImage) {
                // Create image preview for image files
                item.innerHTML = `
                    <div class="image-loading">Loading preview...</div>
                    <div class="file-info" style="display:none">
                        <div class="file-name">${file.name}</div>
                        <div class="file-path">${file.path}</div>
                        <div class="file-size">${this.formatFileSize(file.size)}</div>
                    </div>
                `;

                // Load image preview asynchronously
                this.loadImagePreview(item, file.path, file.name);
            } else {
                // Regular file display
                item.innerHTML = `
                    <div class="file-info style="display:none"">
                        <div class="file-name">${file.name}</div>
                        <div class="file-path">${file.path}</div>
                        <div class="file-size" style="width:100px; height:50px">${this.formatFileSize(file.size)}</div>
                    </div>
                `;
            }

            list.appendChild(item);
        });
    }

    displayDuplicatesList(duplicates) {
        const list = document.getElementById('duplicatesList');
        list.innerHTML = duplicates.length === 0 ? '<div class="file-item">No duplicates found</div>' : '';

        // Add export button at the top
        if (duplicates.length > 0) {
            const exportBtn = document.createElement('button');
            exportBtn.className = 'export-btn';
            exportBtn.textContent = '📋 Export Duplicate Paths to Clipboard';
            exportBtn.onclick = () => this.exportDuplicatePaths(duplicates);
            list.insertBefore(exportBtn, list.firstChild);
        }

        duplicates.forEach((group, index) => {
            const groupDiv = document.createElement('div');
            groupDiv.className = 'duplicate-group';

            const header = document.createElement('div');
            header.className = 'duplicate-header';
            header.textContent = `Group ${index + 1} (${group.count} files) - ${this.formatFileSize(group.total_size)} total`;

            const filesDiv = document.createElement('div');
            filesDiv.className = 'duplicate-files';

            group.files.forEach(file => {
                const item = document.createElement('div');
                item.className = 'file-item';
                // Use the file object structure from the API response
                const translatedPath = this.translateContainerPathToHost(file.path);
                const fileName = file.name || translatedPath.split('/').pop();

                item.innerHTML = `
                    <div class="file-info">
                        <div class="file-name">${fileName}</div>
                        <div class="file-path">${translatedPath}</div>
                        <div class="file-size">${this.formatFileSize(file.size)}</div>
                        ${file.is_original ? '<div class="original-badge">ORIGINAL</div>' : ''}
                    </div>
                `;

                // Add click handler for image preview if it's an image
                if (this.isImageFile(fileName)) {
                    item.style.cursor = 'pointer';
                    item.addEventListener('click', () => this.openDuplicateImageModal(file, translatedPath));
                }

                filesDiv.appendChild(item);
            });

            groupDiv.appendChild(header);
            groupDiv.appendChild(filesDiv);
            list.appendChild(groupDiv);
        });
    }

    switchTab(tabName) {
        document.querySelectorAll('.tab-btn').forEach(btn => btn.classList.remove('active'));
        document.querySelector(`[data-tab="${tabName}"]`).classList.add('active');
        
        document.querySelectorAll('.tab-content').forEach(content => content.classList.remove('active'));
        document.getElementById(`${tabName}Tab`).classList.add('active');
    }

    resetStats() {
        document.getElementById('totalFiles').textContent = '0';
        document.getElementById('duplicateGroups').textContent = '0';
        document.getElementById('totalSize').textContent = '0 MB';
        document.getElementById('scanTime').textContent = '0s';
    }

    formatFileSize(bytes) {
        if (bytes === 0) return '0 B';
        const k = 1024;
        const sizes = ['B', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i];
    }

    async displayImagesList(images, similarImages) {
        this.imageFiles = images;
        this.similarImages = similarImages;
        
        console.log('Displaying images list:', images.length, 'images');
        if (images.length > 0) {
            console.log('First image path:', images[0].path);
            console.log('Sample image paths:', images.slice(0, 3).map(img => img.path));
        }
        
        const grid = document.getElementById('imagesGrid');
        grid.innerHTML = images.length === 0 ? '<div class="file-item">No images found</div>' : '';
        
        for (const [index, image] of images.entries()) {
            const item = document.createElement('div');
            item.className = 'image-item';
            
            // Check if this image has similar matches
            const similarGroup = similarImages.find(group => 
                group.images.some(img => img.path === image.path)
            );
            
            const similarIndicator = similarGroup ? 
                `<div class="similar-indicator ${similarGroup.type}">${similarGroup.images.length}</div>` : '';
            
            // Create placeholder first
            item.innerHTML = `
                ${similarIndicator}
                <div class="image-loading">Loading...</div>
                <div class="image-info">
                    <div class="image-name">${image.name}</div>
                    <div class="image-details">
                        <span style="width:50px;height:50px; ">${this.formatFileSize(image.size)}</span>
                        <span>${image.dimensions || 'Unknown'}</span>
                    </div>
                </div>
            `;
            
            item.addEventListener('click', () => this.openImageModal(image, index));
            grid.appendChild(item);
            
            // Load image asynchronously
            this.loadImagePreview(item, image.path, image.name);
        }
    }

    async loadImagePreview(container, imagePath, imageName) {
        try {
            // Translate container path to host path
            const translatedPath = this.translateContainerPathToHost(imagePath);
            console.log('Loading image preview for:', imagePath);
            console.log('Translated path:', translatedPath);
            
            // Check if image exists first
            const exists = await window.electronAPI.checkImageExists(translatedPath);
            console.log('Image exists:', exists);
            
            if (!exists) {
                this.setImageError(container, 'File not found');
                return;
            }
            
            // Get image data URL
            console.log('Getting image data URL...');
            const dataUrl = await window.electronAPI.getImageDataUrl(translatedPath);
            console.log('Data URL received:', dataUrl ? 'Yes' : 'No');
            
            if (dataUrl) {
                const loadingDiv = container.querySelector('.image-loading');
                if (loadingDiv) {
                    const img = document.createElement('img');
                    img.className = 'image-preview';
                    img.src = dataUrl;
                    img.alt = imageName;
                    img.onerror = () => {
                        console.error('Image failed to load in DOM:', translatedPath);
                        this.setImageError(container, 'Failed to load');
                    };
                    img.onload = () => {
                        console.log('Image loaded successfully:', translatedPath);
                    };
                    
                    loadingDiv.replaceWith(img);
                }
            } else {
                console.error('No data URL returned for:', translatedPath);
                this.setImageError(container, 'Cannot load image');
            }
        } catch (error) {
            console.error('Error loading image preview:', imagePath, error);
            this.setImageError(container, 'Load error');
        }
    }

    setImageError(container, errorMessage) {
        const loadingDiv = container.querySelector('.image-loading');
        if (loadingDiv) {
            const errorDiv = document.createElement('div');
            errorDiv.className = 'image-error';
            errorDiv.textContent = errorMessage;
            loadingDiv.replaceWith(errorDiv);
        }
    }

    async loadSimilarImagePreview(container, imagePath, imageName) {
        try {
            // Translate container path to host path
            const translatedPath = this.translateContainerPathToHost(imagePath);
            
            // Check if image exists first
            const exists = await window.electronAPI.checkImageExists(translatedPath);
            if (!exists) {
                this.setSimilarImageError(container, 'File not found');
                return;
            }
            
            // Get image data URL
            const dataUrl = await window.electronAPI.getImageDataUrl(translatedPath);
            if (dataUrl) {
                const loadingDiv = container.querySelector('.image-loading');
                if (loadingDiv) {
                    const img = document.createElement('img');
                    img.className = 'similar-image-preview';
                    img.src = dataUrl;
                    img.alt = imageName;
                    img.onerror = () => this.setSimilarImageError(container, 'Failed to load');
                    
                    loadingDiv.replaceWith(img);
                }
            } else {
                this.setSimilarImageError(container, 'Cannot load image');
            }
        } catch (error) {
            console.error('Error loading similar image preview:', error);
            this.setSimilarImageError(container, 'Load error');
        }
    }

    setSimilarImageError(container, errorMessage) {
        const loadingDiv = container.querySelector('.image-loading');
        if (loadingDiv) {
            const errorDiv = document.createElement('div');
            errorDiv.className = 'image-error';
            errorDiv.textContent = errorMessage;
            loadingDiv.replaceWith(errorDiv);
        }
    }

    async openImageModal(image, index) {
        const modal = document.getElementById('imageModal');
        const modalImage = document.getElementById('modalImage');
        const modalInfo = document.getElementById('modalInfo');

        // Show modal with loading state
        modalImage.src = '';
        modalImage.alt = 'Loading...';

        // Translate container path to host path
        const translatedPath = this.translateContainerPathToHost(image.path);

        modalInfo.innerHTML = `
            <strong>${image.name}</strong><br>
            ${translatedPath}<br>
            ${this.formatFileSize(image.size)} • ${image.dimensions || 'Unknown dimensions'}<br>
            <button class="open-in-viewer-btn" onclick="app.openImageInDefaultViewer('${translatedPath.replace(/'/g, "\\'")}')">🖼️ Open in Default Viewer</button><br>
            <em>Loading image...</em>
        `;

        modal.classList.add('active');
        this.currentImageIndex = index;

        // Load full-size image
        try {
            const dataUrl = await window.electronAPI.getImageDataUrl(translatedPath);
            if (dataUrl) {
                modalImage.src = dataUrl;
                modalImage.alt = image.name;
                modalInfo.innerHTML = `
                    <strong>${image.name}</strong><br>
                    ${translatedPath}<br>
                    ${this.formatFileSize(image.size)} • ${image.dimensions || 'Unknown dimensions'}<br>
                    <button class="open-in-viewer-btn" onclick="app.openImageInDefaultViewer('${translatedPath.replace(/'/g, "\\'")}')">🖼️ Open in Default Viewer</button>
                `;
            } else {
                modalImage.alt = 'Failed to load image';
                modalInfo.innerHTML = `
                    <strong>${image.name}</strong><br>
                    ${translatedPath}<br>
                    ${this.formatFileSize(image.size)} • ${image.dimensions || 'Unknown dimensions'}<br>
                    <button class="open-in-viewer-btn" onclick="app.openImageInDefaultViewer('${translatedPath.replace(/'/g, "\\'")}')">🖼️ Open in Default Viewer</button><br>
                    <em style="color: red;">Failed to load image preview</em>
                `;
            }
        } catch (error) {
            console.error('Error loading modal image:', error);
            modalImage.alt = 'Error loading image';
            modalInfo.innerHTML = `
                <strong>${image.name}</strong><br>
                ${translatedPath}<br>
                ${this.formatFileSize(image.size)} • ${image.dimensions || 'Unknown dimensions'}<br>
                <button class="open-in-viewer-btn" onclick="app.openImageInDefaultViewer('${translatedPath.replace(/'/g, "\\'")}')">🖼️ Open in Default Viewer</button><br>
                <em style="color: red;">Error loading image preview</em>
            `;
        }
    }

    async openDuplicateImageModal(file, translatedPath) {
        const modal = document.getElementById('imageModal');
        const modalImage = document.getElementById('modalImage');
        const modalInfo = document.getElementById('modalInfo');

        // Show modal with loading state
        modalImage.src = '';
        modalImage.alt = 'Loading...';

        modalInfo.innerHTML = `
            <strong>${file.name}</strong><br>
            ${translatedPath}<br>
            ${this.formatFileSize(file.size)}<br>
            <button class="open-in-viewer-btn" onclick="app.openImageInDefaultViewer('${translatedPath.replace(/'/g, "\\'")}')">🖼️ Open in Default Viewer</button><br>
            <em>Loading image...</em>
        `;

        modal.classList.add('active');

        // Load full-size image
        try {
            const dataUrl = await window.electronAPI.getImageDataUrl(translatedPath);
            if (dataUrl) {
                modalImage.src = dataUrl;
                modalImage.alt = file.name;
                modalInfo.innerHTML = `
                    <strong>${file.name}</strong><br>
                    ${translatedPath}<br>
                    ${this.formatFileSize(file.size)}<br>
                    <button class="open-in-viewer-btn" onclick="app.openImageInDefaultViewer('${translatedPath.replace(/'/g, "\\'")}')">🖼️ Open in Default Viewer</button><br>
                    ${file.is_original ? '<span style="color: green; font-weight: bold;">ORIGINAL FILE</span>' : '<span style="color: orange;">Duplicate</span>'}
                `;
            } else {
                modalImage.alt = 'Failed to load image';
                modalInfo.innerHTML = `
                    <strong>${file.name}</strong><br>
                    ${translatedPath}<br>
                    ${this.formatFileSize(file.size)}<br>
                    <button class="open-in-viewer-btn" onclick="app.openImageInDefaultViewer('${translatedPath.replace(/'/g, "\\'")}')">🖼️ Open in Default Viewer</button><br>
                    <em style="color: red;">Failed to load image preview</em>
                `;
            }
        } catch (error) {
            console.error('Error loading duplicate image:', error);
            modalImage.alt = 'Error loading image';
            modalInfo.innerHTML = `
                <strong>${file.name}</strong><br>
                ${translatedPath}<br>
                ${this.formatFileSize(file.size)}<br>
                <button class="open-in-viewer-btn" onclick="app.openImageInDefaultViewer('${translatedPath.replace(/'/g, "\\'")}')">🖼️ Open in Default Viewer</button><br>
                <em style="color: red;">Error loading image preview</em>
            `;
        }
    }

    async openSimilarImageModal(image, groupIndex, imageIndex) {
        const modal = document.getElementById('imageModal');
        const modalImage = document.getElementById('modalImage');
        const modalInfo = document.getElementById('modalInfo');

        // Show modal with loading state
        modalImage.src = '';
        modalImage.alt = 'Loading...';

        // Translate container path to host path
        const translatedPath = this.translateContainerPathToHost(image.path);

        modalInfo.innerHTML = `
            <strong>${image.name}</strong><br>
            ${translatedPath}<br>
            ${this.formatFileSize(image.size)} • ${image.dimensions || 'Unknown dimensions'}<br>
            Similarity: ${image.similarity}%<br>
            <button class="open-in-viewer-btn" onclick="app.openImageInDefaultViewer('${translatedPath.replace(/'/g, "\\'")}')">🖼️ Open in Default Viewer</button><br>
            <em>Loading image...</em>
        `;

        modal.classList.add('active');

        // Load full-size image
        try {
            const dataUrl = await window.electronAPI.getImageDataUrl(translatedPath);
            if (dataUrl) {
                modalImage.src = dataUrl;
                modalImage.alt = image.name;
                modalInfo.innerHTML = `
                    <strong>${image.name}</strong><br>
                    ${translatedPath}<br>
                    ${this.formatFileSize(image.size)} • ${image.dimensions || 'Unknown dimensions'}<br>
                    <strong>Similarity: ${image.similarity}%</strong><br>
                    <button class="open-in-viewer-btn" onclick="app.openImageInDefaultViewer('${translatedPath.replace(/'/g, "\\'")}')">🖼️ Open in Default Viewer</button><br>
                    ${image.is_original ? '<span style="color: green; font-weight: bold;">SUGGESTED ORIGINAL</span>' : '<span style="color: blue;">Similar Image</span>'}
                `;
            } else {
                modalImage.alt = 'Failed to load image';
                modalInfo.innerHTML = `
                    <strong>${image.name}</strong><br>
                    ${translatedPath}<br>
                    ${this.formatFileSize(image.size)} • ${image.dimensions || 'Unknown dimensions'}<br>
                    Similarity: ${image.similarity}%<br>
                    <button class="open-in-viewer-btn" onclick="app.openImageInDefaultViewer('${translatedPath.replace(/'/g, "\\'")}')">🖼️ Open in Default Viewer</button><br>
                    <em style="color: red;">Failed to load image preview</em>
                `;
            }
        } catch (error) {
            console.error('Error loading similar image:', error);
            modalImage.alt = 'Error loading image';
            modalInfo.innerHTML = `
                <strong>${image.name}</strong><br>
                ${translatedPath}<br>
                ${this.formatFileSize(image.size)} • ${image.dimensions || 'Unknown dimensions'}<br>
                Similarity: ${image.similarity}%<br>
                <button class="open-in-viewer-btn" onclick="app.openImageInDefaultViewer('${translatedPath.replace(/'/g, "\\'")}')">🖼️ Open in Default Viewer</button><br>
                <em style="color: red;">Error loading image preview</em>
            `;
        }
    }

    exportDuplicatePaths(duplicates) {
        try {
            let exportText = 'DUPLICATE FILES LIST\n';
            exportText += '=' .repeat(50) + '\n\n';

            duplicates.forEach((group, index) => {
                exportText += `DUPLICATE GROUP ${index + 1}\n`;
                exportText += `Files: ${group.count} | Total Size: ${this.formatFileSize(group.total_size)}\n`;
                exportText += '-'.repeat(40) + '\n';

                group.files.forEach((file, fileIndex) => {
                    const translatedPath = this.translateContainerPathToHost(file.path);
                    const marker = file.is_original ? '[ORIGINAL]' : '[DUPLICATE]';
                    exportText += `${fileIndex + 1}. ${marker} ${translatedPath}\n`;
                });

                exportText += '\n';
            });

            // Copy to clipboard
            navigator.clipboard.writeText(exportText).then(() => {
                this.log('✅ Duplicate file paths copied to clipboard!', 'success');
            }).catch(err => {
                console.error('Failed to copy to clipboard:', err);
                // Fallback: show in console
                console.log('Duplicate file paths:');
                console.log(exportText);
                this.log('❌ Clipboard copy failed - check console for paths', 'error');
            });

        } catch (error) {
            console.error('Export error:', error);
            this.log('❌ Failed to export duplicate paths', 'error');
        }
    }

    async openImageInDefaultViewer(imagePath) {
        try {
            this.log(`Opening image in default viewer: ${imagePath}`, 'info');
            const result = await window.electronAPI.openImageInViewer(imagePath);
            if (result) {
                this.log('✅ Image opened in default viewer', 'success');
            } else {
                this.log('❌ Failed to open image in viewer', 'error');
            }
        } catch (error) {
            console.error('Error opening image in viewer:', error);
            this.log('❌ Error opening image in viewer', 'error');
        }
    }

    closeImageModal() {
        document.getElementById('imageModal').classList.remove('active');
    }

    displaySimilarImages(similarGroups) {
        const container = document.getElementById('similarGroups');
        container.innerHTML = similarGroups.length === 0 ?
            '<div class="file-item">No similar images found above the threshold</div>' : '';

        similarGroups.forEach((group, groupIndex) => {
            const groupDiv = document.createElement('div');
            groupDiv.className = 'similar-group';

            const header = document.createElement('div');
            header.className = 'similar-group-header';
            header.innerHTML = `
                <span>Similar Group ${groupIndex + 1} (${group.count} images)</span>
                <div class="similarity-stats">
                    Avg: ${group.avg_similarity}% | Range: ${group.min_similarity}%-${group.max_similarity}%
                </div>
            `;

            const imagesGrid = document.createElement('div');
            imagesGrid.className = 'similar-images-grid';

            group.images.forEach((image, imageIndex) => {
                const item = document.createElement('div');
                item.className = 'similar-image-item';

                const similarityClass = image.similarity === 100 ? 'exact' :
                                      image.similarity >= 95 ? 'high' : '';

                item.innerHTML = `
                    <div class="similarity-percentage ${similarityClass}">${image.similarity}%</div>
                    <div class="image-loading">Loading...</div>
                    <div class="similar-image-info">
                        <div class="similar-image-name">${image.name}</div>
                        <div class="image-details">
                            <span>${this.formatFileSize(image.size)}</span>
                            <span>${image.dimensions || 'Unknown'}</span>
                        </div>
                        ${image.is_original ? '<div class="original-badge-small">ORIGINAL</div>' : ''}
                    </div>
                `;

                item.addEventListener('click', () => this.openSimilarImageModal(image, groupIndex, imageIndex));
                imagesGrid.appendChild(item);

                // Load image asynchronously
                this.loadSimilarImagePreview(item, image.path, image.name);
            });

            groupDiv.appendChild(header);
            groupDiv.appendChild(imagesGrid);
            container.appendChild(groupDiv);
        });
    }

    isImageFile(filename) {
        const imageExtensions = ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff', '.webp'];
        const ext = filename.toLowerCase().substring(filename.lastIndexOf('.'));
        return imageExtensions.includes(ext);
    }

    async testImageLoading() {
        this.log('Testing image loading functionality...', 'info');
        
        // Test with a common image path (you can modify this)
        const testPath = '/Users/shankaraswal/Desktop/test.jpg';
        
        try {
            // Test if electronAPI is available
            if (!window.electronAPI) {
                this.log('ElectronAPI not available', 'error');
                return;
            }
            
            this.log(`Testing path: ${testPath}`, 'info');
            
            // Test file existence check
            const exists = await window.electronAPI.checkImageExists(testPath);
            this.log(`File exists: ${exists}`, exists ? 'success' : 'warning');
            
            if (exists) {
                // Test image loading
                const dataUrl = await window.electronAPI.getImageDataUrl(testPath);
                this.log(`Data URL received: ${dataUrl ? 'Yes' : 'No'}`, dataUrl ? 'success' : 'error');
                
                if (dataUrl) {
                    this.log(`Data URL length: ${dataUrl.length} characters`, 'info');
                }
            }
            
        } catch (error) {
            this.log(`Test failed: ${error.message}`, 'error');
            console.error('Image loading test error:', error);
        }
    }

    log(message, type = 'info') {
        const log = document.getElementById('statusLog');
        const entry = document.createElement('div');
        entry.className = `log-entry ${type}`;
        entry.textContent = `${new Date().toLocaleTimeString()} - ${message}`;
        
        log.appendChild(entry);
        log.scrollTop = log.scrollHeight;
        
        // Keep only last 20 entries
        while (log.children.length > 20) {
            log.removeChild(log.firstChild);
        }
    }
}

document.addEventListener('DOMContentLoaded', () => {
    const app = new RAGSmartFolder();
    app.handleScanModeChange(); // Initialize button visibility
});