// RAG Smart Folder - Minimal Desktop App

class RAGSmartFolder {
    constructor() {
        this.apiBase = 'http://127.0.0.1:8003';
        this.selectedFolderPath = '';
        this.scanStartTime = null;
        
        this.initializeEventListeners();
        this.checkAPIConnection();
    }

    initializeEventListeners() {
        document.getElementById('selectFolderBtn').addEventListener('click', () => this.selectFolder());
        document.getElementById('scanButton').addEventListener('click', () => this.startScan());
        document.getElementById('clearButton').addEventListener('click', () => this.clearDatabase());
        
        document.querySelectorAll('.tab-btn').forEach(btn => {
            btn.addEventListener('click', (e) => this.switchTab(e.target.dataset.tab));
        });
    }

    async selectFolder() {
        try {
            const folderPath = await window.electronAPI.selectFolder();
            
            if (folderPath) {
                this.selectedFolderPath = folderPath;
                document.getElementById('selectedPath').textContent = folderPath;
                document.getElementById('scanButton').disabled = false;
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

    async startScan() {
        if (!this.selectedFolderPath) {
            this.log('Please select a folder first', 'error');
            return;
        }

        const btn = document.getElementById('scanButton');
        const btnText = btn.querySelector('.btn-text');
        const btnLoader = btn.querySelector('.btn-loader');
        
        btn.disabled = true;
        btnText.style.display = 'none';
        btnLoader.style.display = 'inline-block';
        
        this.scanStartTime = Date.now();
        this.log('Starting scan...', 'info');

        try {
            const response = await fetch(`${this.apiBase}/scan`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    folder_path: this.selectedFolderPath,
                    recursive: document.getElementById('recursiveCheck').checked,
                    find_duplicates: document.getElementById('findDuplicates').checked,
                    clear_previous: document.getElementById('clearPrevious').checked
                })
            });

            if (!response.ok) {
                const error = await response.json();
                throw new Error(error.detail || 'Scan failed');
            }

            const result = await response.json();
            this.log(result.message, 'success');
            
            await this.loadResults();
            
            const scanTime = ((Date.now() - this.scanStartTime) / 1000).toFixed(1);
            this.log(`Completed in ${scanTime}s`, 'success');
            
        } catch (error) {
            this.log(`Scan failed: ${error.message}`, 'error');
        } finally {
            btn.disabled = false;
            btnText.style.display = 'inline-block';
            btnLoader.style.display = 'none';
        }
    }

    async loadResults() {
        try {
            const [filesResponse, duplicatesResponse] = await Promise.all([
                fetch(`${this.apiBase}/files`),
                fetch(`${this.apiBase}/duplicates`)
            ]);
            
            const filesData = await filesResponse.json();
            const duplicatesData = await duplicatesResponse.json();
            
            this.displayResults(filesData, duplicatesData);
            
        } catch (error) {
            this.log(`Failed to load results: ${error.message}`, 'error');
        }
    }

    displayResults(filesData, duplicatesData) {
        const totalSize = filesData.files?.reduce((sum, file) => sum + (file.size || 0), 0) || 0;
        const scanTime = this.scanStartTime ? ((Date.now() - this.scanStartTime) / 1000).toFixed(1) : '0';
        
        document.getElementById('totalFiles').textContent = filesData.total_files || 0;
        document.getElementById('duplicateGroups').textContent = duplicatesData.total_duplicate_groups || 0;
        document.getElementById('totalSize').textContent = this.formatFileSize(totalSize);
        document.getElementById('scanTime').textContent = `${scanTime}s`;
        
        this.displayFilesList(filesData.files || []);
        this.displayDuplicatesList(duplicatesData.duplicates || []);
        
        document.getElementById('resultsSection').style.display = 'block';
    }

    displayFilesList(files) {
        const list = document.getElementById('filesList');
        list.innerHTML = files.length === 0 ? '<div class="file-item">No files found</div>' : '';
        
        files.forEach(file => {
            const item = document.createElement('div');
            item.className = 'file-item';
            item.innerHTML = `
                <div class="file-info">
                    <div class="file-name">${file.name}</div>
                    <div class="file-path">${file.path}</div>
                </div>
                <div class="file-size">${this.formatFileSize(file.size)}</div>
            `;
            list.appendChild(item);
        });
    }

    displayDuplicatesList(duplicates) {
        const list = document.getElementById('duplicatesList');
        list.innerHTML = duplicates.length === 0 ? '<div class="file-item">No duplicates found</div>' : '';
        
        duplicates.forEach((group, index) => {
            const groupDiv = document.createElement('div');
            groupDiv.className = 'duplicate-group';
            
            const header = document.createElement('div');
            header.className = 'duplicate-header';
            header.textContent = `Group ${index + 1} (${group.count} files)`;
            
            const filesDiv = document.createElement('div');
            filesDiv.className = 'duplicate-files';
            
            group.files.forEach(filePath => {
                const item = document.createElement('div');
                item.className = 'file-item';
                item.innerHTML = `
                    <div class="file-info">
                        <div class="file-name">${filePath.split('/').pop()}</div>
                        <div class="file-path">${filePath}</div>
                    </div>
                `;
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

document.addEventListener('DOMContentLoaded', () => new RAGSmartFolder());