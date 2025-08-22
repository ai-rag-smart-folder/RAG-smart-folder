# RAG Smart Folder - Development Workflow

## Workflow Steps
1. **Backend Changes**: Edit in `backend/` folder.
2. **Desktop App Changes**: Work in `desktop-app/` folder.
3. **Infrastructure Changes**: Update in `devops/` folder.
4. **Data Management**: Use `data/`, `logs/`, `quarantine/` folders.

## Development Commands
```bash
# Activate environment
source .venv/bin/activate

# Run tests
python -m pytest tests/

# Format code
black backend/ scripts/

# Lint code
flake8 backend/ scripts/

# Start server
cd backend && python -m uvicorn app.main:app --reload
```

## Docker Commands
```bash
cd devops
docker-compose up -d    # Start
docker-compose down     # Stop
```