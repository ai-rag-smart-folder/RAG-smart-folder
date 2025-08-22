# DevOps & Infrastructure

This folder contains all deployment, containerization, and infrastructure setup files.

## 📁 Contents

- `docker-compose.yml` - Docker orchestration for the full stack
- `Dockerfile` - Container definition for the backend
- `.dockerignore` - Files to exclude from Docker build
- `setup.sh` - Development environment setup script
- `env.example` - Environment variables template
- `DOCKER.md` - Detailed Docker documentation

## 🚀 Quick Commands

### Docker Deployment
```bash
# Start the application
docker-compose up -d

# View logs
docker-compose logs -f

# Stop the application
docker-compose down

# Rebuild and restart
docker-compose up -d --build
```

### Development Setup
```bash
# Setup Python environment for backend development
./setup.sh
```

## 🔧 Configuration

1. Copy `env.example` to `.env` and customize settings
2. Update `docker-compose.yml` paths if needed
3. Modify `Dockerfile` for custom backend requirements

## 📋 Environment Variables

See `env.example` for all available configuration options.