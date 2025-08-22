# RAG Smart Folder - Project Overview

## What is RAG Smart Folder?
RAG Smart Folder is a Retrieval-Augmented Generation (RAG)-based application designed for intelligent file management. It leverages AI to scan folders, detect duplicates, analyze content, and provide insights, similar to Google Photos functionality but extensible to any folder on your machine.

## Architecture
The project follows a clean, separated architecture with two main codebases:

### Backend (`backend/`)
- **FastAPI** REST API for file operations
- **SQLite** database for metadata storage
- **Docker** containerization for easy deployment
- **Python** scripts for file scanning and analysis

### Desktop App (`desktop/`)
- **Electron** cross-platform desktop application
- **Native** folder selection and file system access
- **Real-time** progress updates and results display
- **Secure** communication with backend API

## Key Features

### Current Features ✅
- **File Scanning**: Recursive directory scanning with metadata extraction
- **Duplicate Detection**: SHA256-based exact duplicate detection
- **Image Analysis**: Perceptual hashing for image similarity
- **Desktop Interface**: Native folder selection and results display
- **Real-time Updates**: Live progress tracking during scans
- **Docker Support**: Containerized backend for consistent deployment
- **Cross-platform**: Works on macOS, Windows, and Linux

### Planned Features 🚧
- **RAG Integration**: Content search and AI-powered insights
- **Advanced ML**: Enhanced image similarity and content analysis
- **Web Interface**: Browser-based access to complement desktop app
- **Cloud Storage**: Integration with cloud storage providers
- **Batch Operations**: Bulk file operations and management

## Goals
- **Efficiency**: Enhance file organization and storage efficiency
- **Scalability**: Provide solutions for personal and enterprise use
- **Extensibility**: Support future enhancements and integrations
- **Usability**: Intuitive interface for both technical and non-technical users

## Technology Stack

### Backend
- **Python 3.11+** - Core language
- **FastAPI** - Web framework
- **SQLite** - Database
- **Docker** - Containerization
- **Pillow** - Image processing
- **Imagehash** - Perceptual hashing

### Desktop App
- **Node.js 16+** - Runtime
- **Electron** - Desktop framework
- **HTML/CSS/JS** - Frontend technologies
- **Native APIs** - File system access

### DevOps
- **Docker Compose** - Service orchestration
- **Make** - Build automation
- **Git** - Version control

## Current Status
The project has a fully functional MVP with:
- ✅ Working desktop application with native folder selection
- ✅ FastAPI backend with comprehensive file scanning
- ✅ Docker containerization for easy deployment
- ✅ Real-time progress updates and duplicate detection
- ✅ Clean separated architecture for maintainability

## Getting Started
See the [Quick Start Guide](Quick_Start_Guide.markdown) for setup instructions, or use these simple commands:

```bash
make start    # Start backend
make desktop  # Start desktop app
```

## Development
Each codebase can be developed independently:
- Backend developers work in `backend/`
- Frontend developers work in `desktop/`
- See [Development Workflow](Development_Workflow.markdown) for detailed instructions