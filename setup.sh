#!/bin/bash

echo "🚀 Setting up StudyAI Django API..."

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
echo "Activating virtual environment..."
source venv/bin/activate

# Install dependencies
echo "Installing dependencies..."
pip install -r requirements.txt

# Check if .env file exists
if [ ! -f ".env" ]; then
    echo "Creating .env file from local example..."
    cp env.local.example .env
    echo ""
    echo "🔑 IMPORTANT: Edit .env file and add your OpenAI API key!"
    echo "   Get your API key from: https://platform.openai.com/api-keys"
    echo "   Replace 'sk-your_openai_api_key_here' with your actual key"
    echo ""
else
    echo "✅ .env file already exists"
fi

# Check if OpenAI API key is set
if grep -q "sk-your_openai_api_key_here" .env 2>/dev/null; then
    echo ""
    echo "⚠️  WARNING: Please update your OpenAI API key in .env file!"
    echo "   Current: sk-your_openai_api_key_here"
    echo "   Replace with your actual key from: https://platform.openai.com/api-keys"
    echo ""
fi

# Create logs directory
echo "Creating logs directory..."
mkdir -p logs

# Run migrations
echo "Running database migrations..."
python manage.py migrate

# Create superuser if it doesn't exist
echo "Creating superuser (skip if already exists)..."
python manage.py createsuperuser --noinput --username admin --email admin@example.com || echo "Superuser already exists or skipped"

# Collect static files
echo "Collecting static files..."
python manage.py collectstatic --noinput

echo ""
echo "✅ Setup complete!"
echo ""
echo "🔧 Next steps:"
echo "1. Edit .env file and add your OpenAI API key"
echo "2. Run: source venv/bin/activate"
echo "3. Run: python manage.py runserver"
echo ""
echo "🌐 Your API will be available at: http://localhost:8000/"
echo "🔧 Admin panel: http://localhost:8000/admin/"
echo "📚 API docs: http://localhost:8000/swagger/"
echo ""
echo "🔑 OpenAI API Key Setup:"
echo "   - Get key from: https://platform.openai.com/api-keys"
echo "   - Add to .env: OPENAI_API_KEY=sk-your-actual-key"
echo "   - AI question generation requires this key!" 