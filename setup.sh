#!/bin/bash

echo "🏥 CMS Home Health Data Explorer Setup"
echo "======================================"

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is required but not installed."
    exit 1
fi

echo "✅ Python 3 found"

# Install dependencies
echo "📦 Installing Python dependencies..."
pip install -r requirements.txt

if [ $? -eq 0 ]; then
    echo "✅ Dependencies installed successfully"
else
    echo "❌ Failed to install dependencies"
    exit 1
fi

# Check if data files exist
echo "📂 Checking for data files..."
required_files=(
    "data/HHCAHPS_Provider_Apr2025.csv"
    "data/HH_Provider_Apr2025.csv"
    "data/HH_Zip_Apr2025.csv"
    "data/State_County_Penetration_MA_2025_06.csv"
)

missing_files=0
for file in "${required_files[@]}"; do
    if [ -f "$file" ]; then
        echo "✅ Found: $file"
    else
        echo "❌ Missing: $file"
        ((missing_files++))
    fi
done

if [ $missing_files -gt 0 ]; then
    echo "⚠️  Warning: Some data files are missing. The pipeline will skip missing files."
fi

# Process the data
echo "🔄 Processing CMS data..."
python data_processor.py

if [ $? -eq 0 ]; then
    echo "✅ Data processing completed"
else
    echo "❌ Data processing failed"
    exit 1
fi

# Initialize vector database
echo "🤖 Initializing vector database..."
python vector_database.py

if [ $? -eq 0 ]; then
    echo "✅ Vector database initialized"
else
    echo "❌ Vector database initialization failed"
    exit 1
fi

echo ""
echo "🎉 Setup completed successfully!"
echo ""
echo "Next steps:"
echo "1. Launch the web application: streamlit run streamlit_app.py"
echo "2. Open your browser to http://localhost:8501"
echo "3. Explore the provider search, market analysis, and AI assistant features"
echo ""
echo "For help, see README.md or check the documentation in each Python file."
