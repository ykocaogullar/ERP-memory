#!/bin/bash

# Docker Compose startup script for ERP Memory System
# This script replaces the manual start_api.sh approach

set -e

echo "🐳 Starting ERP Memory System with Docker Compose"
echo "=================================================="

# Check if .env file exists
if [ ! -f .env ]; then
    echo "⚠️  Warning: .env file not found"
    echo "   Please create .env file with your configuration"
    echo "   You can copy from .env.example if available"
    echo ""
fi

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo "❌ Docker is not running. Please start Docker first."
    exit 1
fi

# Check if Docker Compose is available
if ! command -v docker-compose > /dev/null 2>&1; then
    echo "❌ Docker Compose not found. Please install Docker Compose."
    exit 1
fi

echo "🔧 Building and starting services..."
echo ""

# Build and start services
docker-compose up --build -d

echo ""
echo "⏳ Waiting for services to be ready..."

# Wait for database to be ready
echo "   - Waiting for database..."
timeout=60
while ! docker-compose exec -T db pg_isready -U erp_user -d erp_db > /dev/null 2>&1; do
    sleep 2
    timeout=$((timeout - 2))
    if [ $timeout -le 0 ]; then
        echo "❌ Database failed to start within 60 seconds"
        docker-compose logs db
        exit 1
    fi
done

# Wait for API to be ready
echo "   - Waiting for API..."
timeout=60
while ! curl -f http://localhost:8080/health > /dev/null 2>&1; do
    sleep 2
    timeout=$((timeout - 2))
    if [ $timeout -le 0 ]; then
        echo "❌ API failed to start within 60 seconds"
        docker-compose logs api
        exit 1
    fi
done

echo ""
echo "✅ All services are ready!"
echo ""
echo "🌐 API is available at: http://localhost:8080"
echo "📊 Health check: http://localhost:8080/health"
echo "📖 API docs: http://localhost:8080/docs"
echo ""
echo "🗄️  Database is available at: localhost:5432"
echo "   - Database: erp_db"
echo "   - User: erp_user"
echo "   - Password: erp_password"
echo ""
echo "📋 Useful commands:"
echo "   - View logs: docker-compose logs -f"
echo "   - Stop services: docker-compose down"
echo "   - Restart API: docker-compose restart api"
echo "   - Access API container: docker-compose exec api bash"
echo ""
echo "🎉 ERP Memory System is running!"

