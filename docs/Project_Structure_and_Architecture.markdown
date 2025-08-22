# RAG Smart Folder - Project Structure and Architecture

## Project Structure

```
RAG-smart-folder/
├── repos/                           # Clean separated codebases
│   ├── backend/   # Python FastAPI Backend
│   │   ├── app/                    # FastAPI application
│   │   ├── data/                   # Backend-specific data
│   │   ├── scripts/                # Utility scripts
│   │   ├── sql/                    # Database schemas
│   │   ├── docker-compose.yml      # Backend services
│   │   ├── Dockerfile              # Backend container
│   │   └── requirements.txt        # Python dependencies
│   └── desktop/   # Electron Desktop Application
│       ├── renderer/               # Frontend UI files
│       ├── main.js                 # Electron main process
│       ├── preload.js              # Preload script
│       └── package.json            # Node.js dependencies
├── data/                           # Shared application data
├── logs/                           # Application logs
├── quarantine/                     # Quarantined duplicate files
├── docs/                           # Documentation
├── docker-compose.yml              # Root orchestration
├── Makefile                        # Development commands
├── .gitignore                      # Git ignore rules
└── README.md                       # Main documentation
```

## High-Level Architecture

### Backend (backend/)
- **FastAPI Application**: RESTful API for file operations
- **File Scanner**: Recursive directory scanning with metadata extraction
- **Duplicate Detection**: SHA256 hashing and perceptual hashing for images
- **Database**: SQLite for file metadata and duplicate tracking
- **Docker Support**: Containerized for consistent deployment

### Desktop App (desktop/)
- **Electron Framework**: Cross-platform desktop application
- **Native Integration**: OS-level folder selection dialogs
- **Real-time Updates**: Live progress tracking during scans
- **Secure Communication**: IPC between main and renderer processes

### Data Flow
1. **User Selection**: Desktop app provides folder selection interface
2. **API Communication**: Desktop app sends scan requests to backend API
3. **File Processing**: Backend scans files, extracts metadata, detects duplicates
4. **Results Display**: Real-time updates shown in desktop interface
5. **Action Handling**: User can quarantine, delete, or manage duplicates

## Benefits of New Structure

### Separation of Concerns
- **Independent Development**: Each team can work on their codebase
- **Technology Isolation**: Backend (Python) and Frontend (Node.js) dependencies separated
- **Version Control**: Each repo can have its own git history if needed

### Scalability
- **Microservices Ready**: Easy to split into separate repositories
- **Container Orchestration**: Docker Compose manages service dependencies
- **Deployment Flexibility**: Backend can be deployed independently

### Maintainability
- **Clear Boundaries**: No mixing of backend and frontend code
- **Simplified Dependencies**: Each codebase has only what it needs
- **Easy Onboarding**: New developers can focus on specific components

## Development Workflow

### Quick Start
```bash
make start    # Start backend
make desktop  # Start desktop app
```

### Individual Development
```bash
# Backend development
cd backend
docker-compose up -d

# Desktop development
cd desktop
npm start
```

### Production Deployment
```bash
docker-compose up -d  # Start backend services
# Desktop app can be packaged as native installer
```