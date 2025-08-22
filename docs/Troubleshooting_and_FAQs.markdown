# RAG Smart Folder - Troubleshooting and FAQs

## Common Issues
1. **Permission Denied**: Ensure read access to the folder.
2. **Dependencies Missing**: Run `pip install -r requirements.txt`.
3. **Database Errors**: Delete `data/dev.db` and rerun setup.
4. **Port in Use**: Change port in `backend/app/core/config.py`.

## FAQs
- **How to view logs?**: Check `logs/app.log`.
- **Test without changes?**: Use `--dry-run` with scanner.
- **API docs?**: Visit `http://127.0.0.1:8000/docs`.

## Getting Help
- Contact team lead or check Confluence updates.