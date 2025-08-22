# RAG Smart Folder - Project Structure and Architecture

## Project Structure

```
RAG-smart-folder/
├── backend/         # Python FastAPI Backend (app, scripts, sql, tests)
├── desktop-app/     # Electron Desktop Application (main.js, renderer, etc.)
├── devops/          # DevOps & Infrastructure (Docker files)
├── data/            # Application Data (dev.db)
├── logs/            # Application Logs
├── quarantine/      # Quarantined Files
├── .gitignore
├── README.md
├── QUICKSTART.md
└── PROJECT-STRUCTURE.md
```

## High-Level Architecture

- **Backend**: Handles file scanning, duplicate detection, and API services (FastAPI with Docker).
- **Desktop App**: Provides a UI for folder selection and results (Electron-based).
- **DevOps**: Manages deployment and infrastructure (Docker Compose).
- **Data Flow**: User query → Retriever → Vector Store → Embedding Model → LLM → Response → UI.

## Benefits

- Separation of concerns for maintainability.
- Independent development across teams.
- Scalable for future components (e.g., web/mobile apps).