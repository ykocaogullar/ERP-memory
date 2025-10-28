#!/bin/bash
# Start the ERP Memory System API

echo "🚀 Starting ERP Memory System API..."
echo "================================"

# Activate virtual environment
source .venv/bin/activate

# Check if database is running
echo "📊 Checking database connection..."
python -c "from api.utils.database import db; db.execute_query('SELECT 1')" && echo "✅ Database connected" || { echo "❌ Database not connected!"; exit 1; }

# Start the API server
echo ""
echo "🌐 Starting FastAPI server..."
echo "📝 API will be available at: http://localhost:8080"
echo "📖 API documentation: http://localhost:8080/docs"
echo ""
echo "Press Ctrl+C to stop the server"
echo ""

uvicorn api.main:app --reload --host 0.0.0.0 --port 8080

