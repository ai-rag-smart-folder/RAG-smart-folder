#!/bin/bash

echo "🚀 Setting up RAG Smart Folder Development Environment"
echo "=================================================="

# Check if Python 3 is available
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is not installed. Please install Python 3.8+ first."
    exit 1
fi

echo "✅ Python 3 found: $(python3 --version)"

# Create virtual environment
echo "📦 Creating virtual environment..."
python3 -m venv .venv

if [ $? -eq 0 ]; then
    echo "✅ Virtual environment created successfully"
else
    echo "❌ Failed to create virtual environment"
    exit 1
fi

# Activate virtual environment
echo "🔧 Activating virtual environment..."
source .venv/bin/activate

if [ $? -eq 0 ]; then
    echo "✅ Virtual environment activated"
else
    echo "❌ Failed to activate virtual environment"
    exit 1
fi

# Upgrade pip
echo "⬆️  Upgrading pip..."
pip install --upgrade pip

# Install dependencies
echo "📚 Installing dependencies..."
pip install -r requirements.txt

if [ $? -eq 0 ]; then
    echo "✅ Dependencies installed successfully"
else
    echo "❌ Failed to install dependencies"
    echo "💡 Try installing manually: pip install -r requirements.txt"
    exit 1
fi

# Create necessary directories
echo "📁 Creating project directories..."
mkdir -p data logs quarantine

# Initialize database
echo "🗄️  Initializing database..."
sqlite3 data/dev.db < backend/sql/schema.sql

if [ $? -eq 0 ]; then
    echo "✅ Database initialized successfully"
else
    echo "⚠️  Database initialization failed (this is okay for first run)"
fi

echo ""
echo "🎉 Setup completed successfully!"
echo ""
echo "Next steps:"
echo "1. Activate virtual environment: source .venv/bin/activate"
echo "2. Test scanner: python scripts/test_scanner.py"
echo "3. Start API server: cd backend && python -m uvicorn app.main:app --reload"
echo "4. Visit: http://127.0.0.1:8000"
echo ""
echo "Happy coding! 🚀"
