# 🐳 Docker Guide for RAG Smart Folder

## Quick Start with Docker

### Prerequisites
- Docker Desktop installed and running
- At least 2GB RAM available for Docker

### 1. Build and Run (Production Mode)
```bash
# Build the Docker image
./docker-setup.sh build

# Start the application
./docker-setup.sh start

# Access the app
open http://localhost:8000
```

### 2. Development Mode (with Live Reload)
```bash
# Start in development mode
./docker-setup.sh start-dev

# Your code changes will auto-restart the server
```

## 🚀 Docker Commands

### Using the Setup Script (Recommended)
```bash
./docker-setup.sh build      # Build Docker image
./docker-setup.sh start      # Start production mode
./docker-setup.sh start-dev  # Start development mode
./docker-setup.sh stop       # Stop the application
./docker-setup.sh logs       # View logs
./docker-setup.sh shell      # Open shell in container
./docker-setup.sh clean      # Remove containers and images
./docker-setup.sh help       # Show all commands
```

### Manual Docker Commands
```bash
# Build image
docker build -t rag-smart-folder .

# Run production
docker-compose up -d

# Run development
docker-compose -f docker-compose.dev.yml up -d

# View logs
docker-compose logs -f

# Stop
docker-compose down

# Remove everything
docker-compose down --rmi all --volumes
```

## 📁 Volume Mounts

The Docker setup mounts these directories:

- **`./data`** → `/app/data` (Database and persistent data)
- **`./logs`** → `/app/logs` (Application logs)
- **`./quarantine`** → `/app/quarantine` (Quarantined files)
- **`/Users/shankaraswal/Desktop`** → `/app/scan_target` (Folder to scan - **READ ONLY**)

### Customizing Scan Target
Edit `docker-compose.yml` and change this line:
```yaml
- /Users/shankaraswal/Desktop:/app/scan_target:ro
```
To your desired folder:
```yaml
- /path/to/your/folder:/app/scan_target:ro
```

## 🔧 Configuration

### Environment Variables
Set these in `docker-compose.yml`:

```yaml
environment:
  - DATABASE_URL=sqlite:///./data/dev.db
  - LOG_LEVEL=INFO  # DEBUG, INFO, WARNING, ERROR
  - DEBUG=false      # true for development
  - API_HOST=0.0.0.0
  - API_PORT=8000
```

### Production vs Development

| Feature | Production | Development |
|---------|------------|-------------|
| Live Reload | ❌ | ✅ |
| Debug Mode | ❌ | ✅ |
| Log Level | INFO | DEBUG |
| Source Mount | ❌ | ✅ |

## 🐛 Troubleshooting

### Common Issues

1. **Port Already in Use**
   ```bash
   # Check what's using port 8000
   lsof -i :8000
   
   # Kill the process or change port in docker-compose.yml
   ```

2. **Permission Denied**
   ```bash
   # Make sure Docker has access to mounted directories
   chmod 755 data logs quarantine
   ```

3. **Container Won't Start**
   ```bash
   # Check logs
   ./docker-setup.sh logs
   
   # Check container status
   docker ps -a
   ```

4. **Database Issues**
   ```bash
   # Remove old database and restart
   rm -f data/dev.db
   ./docker-setup.sh restart
   ```

### Debug Commands
```bash
# Check container status
docker ps -a

# View container logs
docker logs rag-smart-folder

# Execute commands in container
docker exec -it rag-smart-folder /bin/bash

# Check container resources
docker stats rag-smart-folder
```

## 🚀 Deployment

### Production Deployment
1. **Build optimized image:**
   ```bash
   docker build -t rag-smart-folder:latest .
   ```

2. **Run with proper volumes:**
   ```bash
   docker run -d \
     --name rag-smart-folder \
     -p 8000:8000 \
     -v /host/data:/app/data \
     -v /host/logs:/app/logs \
     -v /host/quarantine:/app/quarantine \
     -v /host/scan-folder:/app/scan_target:ro \
     rag-smart-folder:latest
   ```

3. **Use Docker Compose for production:**
   ```bash
   docker-compose -f docker-compose.prod.yml up -d
   ```

### Scaling
```bash
# Scale to multiple instances
docker-compose up -d --scale rag-smart-folder=3

# Use load balancer (nginx, haproxy)
# Configure reverse proxy to distribute requests
```

## 🔒 Security Considerations

- **Read-only mounts** for scan targets prevent accidental file modification
- **Non-root user** in container (if needed, add to Dockerfile)
- **Network isolation** with custom Docker networks
- **Secrets management** for production credentials

## 📊 Monitoring

### Health Checks
The container includes health checks:
```yaml
healthcheck:
  test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
  interval: 30s
  timeout: 10s
  retries: 3
  start_period: 40s
```

### Logging
```bash
# View real-time logs
./docker-setup.sh logs

# Export logs
docker logs rag-smart-folder > app.log

# Log rotation (configure in docker-compose.yml)
```

## 🎯 Next Steps

1. **Customize scan target** in docker-compose.yml
2. **Add environment variables** for your configuration
3. **Set up monitoring** and alerting
4. **Configure backup** for data volumes
5. **Add CI/CD pipeline** for automated deployments

---

Happy containerizing! 🐳✨
