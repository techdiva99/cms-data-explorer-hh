# CMS Home Health Data Explorer

A comprehensive data analytics platform for CMS Home Health agency data that enables users to find high-quality providers, analyze market competition, and explore geographic coverage using advanced search and AI-powered assistance.

## 🚀 Features

### 📊 Core Analytics
- **Provider Search**: Find home health providers by location (ZIP, city, county, state)
- **Quality Analysis**: Filter by quality scores and service offerings
- **Market Analysis**: Analyze competitive landscapes and market share
- **Geographic Coverage**: Understand provider service areas and coverage
- **🏜️ Coverage Deserts**: NEW - Identify underserved areas and market opportunities

### 🤖 AI-Powered Capabilities
- **Vector Database**: ChromaDB integration for semantic search
- **RAG (Retrieval-Augmented Generation)**: Natural language queries on provider data
- **Intelligent Search**: Find similar providers and relevant context

### 📈 Key Metrics & Calculations
- **Patient Volume Estimation**: `survey_count / response_rate`
- **Market Share**: Provider patients / total county patients
- **Quality Scoring**: Composite scores from multiple CMS quality metrics
- **Competitive Positioning**: Rank providers within geographic areas

### 🏗️ Modular Architecture
The application has been refactored into a clean, modular structure:

- **Analytics Modules** (`src/analytics/`): Specialized analytics components
- **UI Pages** (`src/ui/pages/`): Individual page implementations  
- **Reusable Components** (`src/ui/components/`): Common UI widgets
- **Test Coverage** (`tests/`): Comprehensive testing framework

See [docs/MODULAR_ARCHITECTURE.md](docs/MODULAR_ARCHITECTURE.md) for detailed documentation.

## 🏃 Quick Start

### Running the Application

**New Modular Application (Recommended):**
```bash
streamlit run app.py
```

**Original Application (Deprecated):**
```bash
streamlit run legacy/streamlit_app_simple.py
```

### Using the Analytics API
```python
from src.analytics import CMSAnalytics

# Initialize analytics
analytics = CMSAnalytics()

# Find coverage deserts
deserts = analytics.identify_coverage_deserts(
    radius_miles=25,
    min_medicare_population=100,
    max_providers_in_radius=2
)

# Calculate market potential
market_potential = analytics.calculate_market_potential(['90210', '10001'])
```

## 📁 Project Structure

```
cms-data-explorer-hh/
├── 📁 src/                     # Source code (modular architecture)
│   ├── 📁 analytics/           # Analytics modules
│   │   ├── base.py            # Core analytics class
│   │   ├── geographic.py      # Location-based analysis
│   │   ├── market.py          # Market analysis
│   │   ├── quality.py         # Quality benchmarks
│   │   ├── rural_urban.py     # Rural/urban classification
│   │   └── coverage_deserts.py # Coverage desert analysis (NEW)
│   ├── 📁 ui/                  # User interface modules
│   │   ├── app.py             # Main application
│   │   ├── 📁 pages/          # Individual page modules
│   │   └── 📁 components/     # Reusable UI components
│   ├── 📁 data/               # Data processing modules
│   └── 📁 utils/              # Utility functions
├── 📁 data/                    # Data files
│   ├── 📁 raw/                # Raw CSV/Excel files
│   ├── 📁 processed/          # SQLite database
│   └── 📁 docs/               # Data documentation
├── 📁 scripts/                 # Utility scripts
├── 📁 tests/                   # Test modules
├── 📁 docs/                    # Documentation
├── 📁 legacy/                  # Deprecated files
├── app.py                      # Main entry point
├── requirements.txt            # Python dependencies
├── license.txt                 # License information
├── setup.sh                   # Setup script
└── README.md                   # This file
```

## 🗂️ Data Sources

The platform processes several CMS data files:

- **HHCAHPS_Provider_Apr2025.csv**: Provider quality metrics and patient satisfaction scores
- **HH_Provider_Apr2025.csv**: Provider details, addresses, services offered
- **HH_Zip_Apr2025.csv**: Provider service area ZIP codes
- **State_County_Penetration_MA_2025_06.csv**: Medicare Advantage penetration by county
- **HHCAHPS_State_Apr2025.csv**: State-level quality benchmarks
- **HH_National_Apr2025.csv**: National quality statistics

## 🏗️ Architecture

### Data Processing Pipeline (`src/utils/data_processing.py`)
```python
# Load and clean raw CSV data
dataframes = processor.load_raw_data()
dataframes = processor.clean_and_standardize_data(dataframes)

# Create master dataset with derived metrics
master_df = processor.create_master_provider_dataset(dataframes)
master_df = processor.calculate_derived_metrics(master_df)

# Save to SQLite database
processor.save_to_database(master_df, dataframes)
```

### Analytics Engine (`analytics.py`)
```python
# Find providers by location
providers = analytics.find_providers_by_location(
    zip_code="90210", 
    high_quality_only=True
)

# Market analysis
market_data = analytics.get_market_analysis("Los Angeles", "CA")

# Competitor analysis  
competitors = analytics.get_competitor_analysis("123456")
```

### Vector Database (`vector_database.py`)
```python
# Initialize and embed data
vector_db = CMSVectorDatabase()
vector_db.initialize_vector_database()

# Semantic search
results = vector_db.semantic_search("high quality providers in Texas")

# RAG query for chatbot
context = vector_db.rag_query("Find the best home health providers near me")
```

## 🛠️ Installation & Setup

### Prerequisites
- Python 3.8+
- pip package manager

### Quick Setup
```bash
# Clone the repository
git clone <repository-url>
cd cms-data-explorer-hh

# Install dependencies
pip install -r requirements.txt

# Run setup script (if needed)
bash setup.sh

# Start the application
streamlit run app.py
```

### Dependencies
Key packages used:
- **Streamlit**: Web application framework
- **Pandas**: Data manipulation and analysis
- **Plotly**: Interactive visualizations
- **SQLite3**: Database operations
- **ChromaDB**: Vector database for semantic search

## 📱 User Interface

### 🔍 Provider Search
- **Location Filters**: State, city, ZIP code
- **Quality Filters**: Minimum quality score, high-quality only
- **Service Filters**: Nursing, PT, OT, speech therapy, etc.
- **Results**: Sortable table with provider details

### 📊 Market Analysis
- **Geographic Selection**: Choose state and city/county
- **Key Metrics**: Total providers, quality distribution, market concentration
- **Visualizations**: Quality histograms, ownership pie charts
- **Top Providers**: Ranked by patient volume and market share

### 🎯 Quality Benchmarks
- **National vs State**: Compare quality distributions
- **Percentile Analysis**: See where providers rank nationally
- **Star Rating Distribution**: 1-5 star breakdown

### 🤖 AI Assistant
- **Natural Language Queries**: Ask questions in plain English
- **Semantic Search**: Find relevant providers and data
- **Context Retrieval**: Get comprehensive information for LLM integration

## 📊 Database Schema

### Providers Table
```sql
CREATE TABLE providers (
    ccn TEXT PRIMARY KEY,
    provider_name TEXT,
    address TEXT, city TEXT, state TEXT, zip_code TEXT,
    quality_care_star_rating REAL,
    hhcahps_star_rating REAL,
    composite_quality_score REAL,
    is_high_quality BOOLEAN,
    estimated_total_patients REAL,
    estimated_market_share REAL,
    -- ... additional columns
);
```

### Service Areas Table
```sql
CREATE TABLE service_areas (
    ccn TEXT,
    zip_code TEXT,
    FOREIGN KEY (ccn) REFERENCES providers (ccn)
);
```

### County Statistics Table
```sql
CREATE TABLE county_stats (
    state_name TEXT,
    county_name TEXT,
    eligible_population INTEGER,
    enrolled_population INTEGER,
    penetration_rate REAL
);
```

## 🧮 Key Calculations

### Patient Volume Estimation
```python
estimated_patients = completed_surveys / (response_rate / 100)
```

### Quality Score Composite
```python
composite_score = mean([
    quality_care_star_rating,
    hhcahps_star_rating
])
```

### Market Share Calculation
```python
market_share = provider_patients / total_county_patients
```

### High Quality Classification
```python
is_high_quality = (composite_score >= 4.0) | (composite_score >= 75th_percentile)
```

## 🤖 RAG Implementation

### Document Types in Vector Database

1. **Provider Documents**: Comprehensive summaries including:
   - Quality metrics and ratings
   - Service offerings and capabilities
   - Patient volume and market position
   - Geographic coverage

2. **County Documents**: Market intelligence including:
   - Medicare eligible/enrolled population
   - Penetration rates
   - Market opportunity analysis

3. **Benchmark Documents**: Comparative data including:
   - National quality distributions
   - State-specific benchmarks
   - Performance percentiles

### Sample RAG Queries
```python
# Natural language questions the system can answer:
queries = [
    "Find high quality home health providers in Los Angeles County",
    "What are the quality benchmarks for home health agencies?", 
    "Show me providers that offer physical therapy in Texas",
    "Compare market share of top providers in Cook County",
    "Which counties have the highest Medicare penetration?"
]
```

## 🚀 Extending the Platform

### Adding New Data Sources
1. Update `data_processor.py` to handle new CSV files
2. Modify database schema if needed
3. Update analytics functions for new metrics
4. Re-embed data in vector database

### Integrating with LLMs
```python
# Example OpenAI integration
import openai

def generate_rag_response(query: str, context: str) -> str:
    response = openai.ChatCompletion.create(
        model="gpt-4",
        messages=[
            {"role": "system", "content": "You are a CMS data expert..."},
            {"role": "user", "content": f"Question: {query}\n\nContext: {context}"}
        ]
    )
    return response.choices[0].message.content
```

### Adding Geospatial Features
- Integrate with mapping APIs (Google Maps, MapBox)
- Add distance-based searches
- Visualize provider coverage areas
- Calculate drive-time accessibility

## 📈 Use Cases

### For Patients/Families
- Find high-quality providers in their area
- Compare services offered by different agencies
- Understand quality ratings and patient satisfaction

### For Healthcare Professionals
- Analyze market competition
- Identify partnership opportunities
- Benchmark quality performance

### For Researchers/Analysts
- Study market concentration and competition
- Analyze quality trends and patterns
- Understand geographic access patterns

### For Business Development
- Identify underserved markets
- Analyze competitor strengths/weaknesses
- Plan service expansion strategies

## 🔒 Data Privacy & Compliance

- Uses only publicly available CMS data
- No patient-level information included
- Aggregated metrics protect individual privacy
- Compliant with CMS data use agreements

## 🛠️ Technical Stack

- **Backend**: Python, SQLite, ChromaDB
- **Analytics**: Pandas, NumPy, SciPy
- **Embeddings**: Sentence Transformers
- **Frontend**: Streamlit
- **Visualization**: Plotly, Folium
- **Database**: SQLite (structured), ChromaDB (vector)

## 📞 Support

For questions about implementation, data sources, or extending the platform, please refer to the inline documentation and code comments throughout the modules.