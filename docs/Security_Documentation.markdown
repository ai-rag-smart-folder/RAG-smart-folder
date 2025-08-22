# RAG Smart Folder - Security Documentation

## Security Overview
RAG Smart Folder is designed with security in mind, ensuring your data remains private and secure. As of August 22, 2025, 12:11 PM BST, the application operates entirely on your local machine and does not upload any files or data to external servers.

## Key Security Features
- **Local Processing**: All file scanning, metadata extraction, duplicate detection, and similarity analysis occur locally at the user-specified folder or drive.
- **No Data Upload**: No files, metadata, or content are transmitted to the cloud or third-party services, minimizing data breach risks.
- **Secure Storage**: Data (e.g., SQLite database in `data/dev.db`) and logs (`logs/`) are stored locally with restricted access.
- **Quarantine System**: Removed duplicates are moved to a `quarantine/` folder, allowing recovery without external dependency.
- **Encrypted Communication**: Internal API (FastAPI) uses HTTPS locally if configured, ensuring secure inter-component communication.

## Security Measures
- **Access Control**: Requires user permission to scan folders, adhering to OS-level security protocols.
- **Code Integrity**: Open-source libraries (e.g., LangChain, FAISS) are vetted, with regular updates to patch vulnerabilities.
- **Error Handling**: Logs sensitive operations locally without exposing details, reducing leak risks.
- **Backup Recommendation**: Users are encouraged to backup data before running duplicate removal.

## Potential Risks and Mitigations
- **Risk**: Unauthorized access to local files if device is compromised.
  - **Mitigation**: Use strong device passwords and restrict folder permissions.
- **Risk**: Misconfiguration leading to data loss.
  - **Mitigation**: Implement dry-run mode and user confirmation for deletions.
- **Risk**: Future cloud integration (if added) could introduce upload risks.
  - **Mitigation**: Plan secure APIs and user consent for any future cloud features.

## Best Practices
- Run the app in a secure, isolated environment (e.g., virtual machine).
- Regularly review logs in `logs/` for unusual activity.
- Update dependencies (via `requirements.txt`) to address security patches.

## Contact
For security concerns, contact the project lead via Confluence or internal channels.