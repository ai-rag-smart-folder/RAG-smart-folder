# RAG Smart Folder - Troubleshooting and FAQs

## Common Issues

### Backend Issues
1. **Docker not starting**: 
   - Check if Docker Desktop is running
   - Run `docker info` to verify Docker is accessible
   - Try `make start` or `docker-compose up -d`

2. **Port 8003 in use**:
   - Check what's using the port: `lsof -i :8003`
   - Kill the process or change port in `backend/docker-compose.yml`

3. **Database errors**:
   - Delete `data/dev.db` and restart backend
   - Check database schema in `backend/sql/schema.sql`

4. **Permission denied for folders**:
   - Ensure the user has read access to scan folders
   - Check Docker volume mounts in docker-compose.yml

### Desktop App Issues
1. **App won't start**:
   - Run `npm install` in `desktop/`
   - Check Node.js version (requires Node 16+)
   - Try `npm start` directly

2. **Cannot connect to backend**:
   - Verify backend is running on `http://localhost:8003`
   - Check `make status` or `docker-compose ps`
   - Test API directly: `curl http://localhost:8003/health`

3. **Electron errors**:
   - Clear node_modules: `rm -rf node_modules package-lock.json`
   - Reinstall: `npm install`
   - Check Electron version compatibility

### Development Issues
1. **Make commands not working**:
   - Ensure you're in the root directory
   - Check if `make` is installed: `which make`
   - Use Docker Compose directly if needed

2. **File changes not reflected**:
   - Backend: Restart with `make stop && make start`
   - Desktop: Restart with `Ctrl+R` in the app or restart `npm start`

## FAQs

### General
**Q: How do I view logs?**
A: Use `make logs` or check `logs/app.log` file

**Q: How do I reset everything?**
A: Run `make clean` to remove all containers and data

**Q: Where is the API documentation?**
A: Visit `http://localhost:8003/docs` when backend is running

**Q: How do I test without making changes?**
A: Use the desktop app's preview mode or API endpoints directly

### Development
**Q: How do I add new features?**
A: See [Development_Workflow.markdown](Development_Workflow.markdown) for detailed steps

**Q: Can I run backend without Docker?**
A: Yes, but Docker is recommended. See individual repo READMEs for manual setup

**Q: How do I package the desktop app?**
A: Run `npm run build` in the desktop repo folder

### Deployment
**Q: How do I deploy to production?**
A: Use `docker-compose up -d` for backend, package desktop app as installer

**Q: Can I run multiple instances?**
A: Yes, change ports in docker-compose.yml for each instance

## Debug Commands

### Check Service Status
```bash
make status                    # Show all services
docker-compose ps             # Docker services only
curl http://localhost:8003/health  # Test backend API
```

### View Logs
```bash
make logs                     # Backend logs
docker-compose logs -f        # All container logs
tail -f logs/app.log         # Application logs
```

### Reset Everything
```bash
make clean                    # Remove containers and images
rm -rf data/dev.db           # Reset database
docker system prune -f       # Clean Docker system
```

### Development Debug
```bash
# Backend container access
docker-compose exec backend bash

# Check backend processes
docker-compose exec backend ps aux

# Desktop app debug
cd desktop
npm run dev                   # Development mode with debug
```

## Getting Help

### Resources
- Check individual README files in `repos/` folders
- Review [Project_Structure_and_Architecture.markdown](Project_Structure_and_Architecture.markdown)
- Use `make help` for available commands

### Support
- Create GitHub issues for bugs
- Check logs first before reporting issues
- Include system information (OS, Docker version, Node version)