# RAG Smart Folder - Development Workflow

## Clean Architecture Workflow

### Repository Structure
Each codebase is independent and can be developed separately:
- **Backend**: `backend/`
- **Desktop**: `desktop/`

### Development Steps

#### 1. Backend Development
```bash
cd backend

# Start development environment
docker-compose up -d

# View logs
docker-compose logs -f

# Run tests (when available)
docker-compose exec backend python -m pytest

# Format code
docker-compose exec backend black app/ scripts/

# Lint code
docker-compose exec backend flake8 app/ scripts/
```

#### 2. Desktop App Development
```bash
cd desktop

# Install dependencies
npm install

# Start development mode
npm run dev

# Build for production
npm run build

# Build platform-specific
npm run build-mac    # macOS
npm run build-win    # Windows
npm run build-linux  # Linux
```

#### 3. Full Stack Development
```bash
# Terminal 1: Start backend
make start

# Terminal 2: Start desktop app
make desktop

# View backend logs
make logs
```

## Make Commands (Recommended)
```bash
make help     # Show all commands
make start    # Start backend
make desktop  # Start desktop app
make logs     # View logs
make stop     # Stop everything
make build    # Build services
make clean    # Clean containers
make status   # Show status
```

## Docker Commands
```bash
# Root level orchestration
docker-compose up -d        # Start all services
docker-compose down         # Stop all services
docker-compose logs -f      # View logs

# Backend specific
cd backend
docker-compose up -d        # Start backend only
docker-compose exec backend bash  # Access container
```

## Development Best Practices

### Code Organization
- Keep backend and frontend code completely separated
- Use the shared `data/`, `logs/`, `quarantine/` folders for persistence
- Update documentation when changing structure

### Testing
- Backend tests run in Docker container
- Desktop app tests run with npm
- Integration tests can use both services

### Version Control
- Each repo can be independently versioned
- Root level changes affect orchestration
- Document breaking changes in README

### Deployment
- Backend deploys as Docker container
- Desktop app packages as native installer
- Use docker-compose for production backend deployment

## Common Tasks

### Adding New API Endpoint
1. Edit `backend/app/api/`
2. Update database schema if needed
3. Test with `make start` and API calls
4. Update desktop app to use new endpoint

### Adding Desktop Features
1. Edit `desktop/renderer/`
2. Update main process if needed
3. Test with `make desktop`
4. Ensure backend API supports new features

### Database Changes
1. Update `backend/sql/schema.sql`
2. Create migration scripts if needed
3. Test with fresh database
4. Update both backend and desktop app accordingly