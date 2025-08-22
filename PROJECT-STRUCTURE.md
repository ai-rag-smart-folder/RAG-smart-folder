# RAG Smart Folder - Project Structure

Clean 3-folder organization for better maintainability and separation of concerns.

## 📁 Project Structure

```
RAG-smart-folder/
├── backend/                 # Python FastAPI Backend
│   ├── app/                # FastAPI application
│   ├── scripts/            # Processing scripts
│   ├── sql/                # Database schemas
│   ├── requirements.txt    # Python dependencies
│   └── tests/              # Backend tests
│
├── desktop-app/            # Electron Desktop Application
│   ├── main.js             # Electron main process
│   ├── preload.js          # Secure bridge
│   ├── package.json        # Node.js dependencies
│   ├── setup.sh            # Desktop app setup
│   └── renderer/           # Frontend UI
│       ├── index.html      # Main UI
│       ├── script.js       # Application logic
│       └── styles.css      # Styling
│
├── devops/                 # DevOps & Infrastructure
│   ├── docker-compose.yml  # Docker orchestration
│   ├── Dockerfile          # Container definition
│   ├── .dockerignore       # Docker ignore rules
│   ├── setup.sh            # Development setup
│   ├── env.example         # Environment template
│   └── DOCKER.md           # Docker documentation
│
├── data/                   # Application Data
│   └── dev.db              # SQLite database
│
├── logs/                   # Application Logs
│
├── quarantine/             # Quarantined Files
│
├── .gitignore              # Git ignore rules
├── README.md               # Main documentation
├── QUICKSTART.md           # Quick start guide
└── PROJECT-STRUCTURE.md    # This file
```

## 🚀 Quick Start Commands

### Backend Development
```bash
cd devops && ./setup.sh          # Setup Python environment
cd backend && python -m uvicorn app.main:app --reload
```

### Desktop App
```bash
cd desktop-app && ./setup.sh     # Setup Electron app
npm start                         # Run desktop app
```

### Docker Deployment
```bash
cd devops
docker-compose up -d              # Start with Docker
docker-compose logs -f            # View logs
```

## 🎯 Benefits of This Structure

- **Separation of Concerns**: Each folder has a clear purpose
- **Easy Navigation**: Developers know exactly where to find things
- **Independent Development**: Teams can work on different parts independently
- **Clean Deployment**: DevOps files are separate from application code
- **Scalable**: Easy to add new components (mobile app, web app, etc.)

## 📋 Development Workflow

1. **Backend Changes**: Work in `backend/` folder
2. **Desktop App Changes**: Work in `desktop-app/` folder  
3. **Infrastructure Changes**: Work in `devops/` folder
4. **Data**: Stored in `data/`, `logs/`, `quarantine/` folders

This structure follows industry best practices for multi-component applications.