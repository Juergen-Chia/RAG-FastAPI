#!/bin/bash

# Agentic RAG Application Startup Script

set -e

echo "🚀 Starting Agentic RAG Application..."

# Check if .env exists
if [ ! -f .env ]; then
    echo "❌ Error: .env file not found"
    echo "📝 Please copy .env.example to .env and configure it"
    echo "   cp .env.example .env"
    exit 1
fi

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv venv
    echo "✅ Virtual environment created"
fi

# Activate virtual environment
echo "🔧 Activating virtual environment..."
source venv/bin/activate

# Install requirements if needed
if [ ! -f "venv/.requirements_installed" ]; then
    echo "📦 Installing dependencies..."
    pip install -r requirements.txt
    touch venv/.requirements_installed
    echo "✅ Dependencies installed"
fi

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo "❌ Error: Docker is not running"
    echo "   Please start Docker Desktop and try again"
    exit 1
fi

# Start Docker services
echo "🐳 Starting Docker services (PostgreSQL & Redis)..."
docker-compose up -d

# Wait for services to be healthy
echo "⏳ Waiting for services to be ready..."
sleep 5

# Check PostgreSQL
until docker-compose exec -T postgres pg_isready -U postgres > /dev/null 2>&1; do
    echo "   Waiting for PostgreSQL..."
    sleep 2
done
echo "✅ PostgreSQL is ready"

# Check Redis
until docker-compose exec -T redis redis-cli ping > /dev/null 2>&1; do
    echo "   Waiting for Redis..."
    sleep 2
done
echo "✅ Redis is ready"

echo ""
echo "=========================================="
echo "🎉 All services are ready!"
echo "=========================================="
echo ""
echo "Starting application servers..."
echo ""
echo "📊 FastAPI will be available at: http://localhost:8000"
echo "📄 API Documentation at: http://localhost:8000/docs"
echo "🎨 Streamlit UI will be available at: http://localhost:8501"
echo ""
echo "Press Ctrl+C to stop all services"
echo ""

# Function to cleanup on exit
cleanup() {
    echo ""
    echo "🛑 Shutting down..."
    kill $FASTAPI_PID $STREAMLIT_PID 2>/dev/null
    echo "✅ Application stopped"
    echo "💡 Docker services are still running. To stop them:"
    echo "   docker-compose down"
}

trap cleanup EXIT INT TERM

# Start FastAPI in background
echo "🚀 Starting FastAPI backend..."
python -m app.main > logs/fastapi.log 2>&1 &
FASTAPI_PID=$!

# Wait a bit for FastAPI to start
sleep 3

# Start Streamlit in background
echo "🚀 Starting Streamlit frontend..."
streamlit run streamlit_app.py > logs/streamlit.log 2>&1 &
STREAMLIT_PID=$!

# Wait a bit for Streamlit to start
sleep 3

echo ""
echo "✅ Application is running!"
echo ""
echo "📝 Logs are being written to logs/ directory"
echo "   - logs/fastapi.log"
echo "   - logs/streamlit.log"
echo ""

# Keep script running
wait
