# Data Directory

This directory contains all data files used by the CMS Home Health Data Explorer.

## Structure

```
data/
├── raw/                    # Raw data files (CSV, Excel, etc.)
│   ├── HHCAHPS_Provider_Apr2025.csv
│   ├── HHCAHPS_State_Apr2025.csv
│   ├── HH_National_Apr2025.csv
│   ├── HH_Provider_Apr2025.csv
│   ├── HH_Zip_Apr2025.csv
│   ├── State_County_Penetration_MA_2025_06.csv
│   ├── cbsa_delineation.xls
│   ├── hud_zip_county_crosswalk.xlsx
│   ├── uszips.csv
│   ├── uszips.xlsx
│   ├── zcta_county_rel_10.txt
│   ├── zip_cbsa_crosswalk.csv
│   ├── zip_county_crosswalk_raw.csv
│   └── county_coverage_report.csv
├── processed/              # Processed and cleaned data
│   └── cms_homehealth.db   # Main SQLite database
└── docs/                   # Data documentation
    └── HHS_Data_Dictionary.pdf
```

## Raw Data Files

### CMS Home Health Data (April 2025)
- **HH_Provider_Apr2025.csv** - Provider details, addresses, services offered
- **HH_Zip_Apr2025.csv** - Provider service area ZIP codes
- **HHCAHPS_Provider_Apr2025.csv** - Provider quality metrics and patient satisfaction
- **HHCAHPS_State_Apr2025.csv** - State-level quality benchmarks
- **HH_National_Apr2025.csv** - National quality statistics

### Geographic and Crosswalk Data
- **cbsa_delineation.xls** - Core Based Statistical Area definitions
- **hud_zip_county_crosswalk.xlsx** - HUD ZIP-to-county mapping
- **zip_cbsa_crosswalk.csv** - ZIP-to-CBSA mapping
- **zip_county_crosswalk_raw.csv** - Raw ZIP-to-county crosswalk
- **zcta_county_rel_10.txt** - ZCTA-to-county relationships (2010 Census)
- **uszips.csv/xlsx** - US ZIP code geographic data

### Market Analysis Data
- **State_County_Penetration_MA_2025_06.csv** - Medicare Advantage penetration by county
- **county_coverage_report.csv** - Provider coverage analysis by county

## Processed Data

### Database Schema (cms_homehealth.db)

The main SQLite database contains integrated and cleaned data:

**Tables:**
- `providers` - Master provider dataset with quality metrics
- `zip_county_crosswalk` - Geographic mapping data
- Additional tables created during processing

**Key Fields:**
- Provider identifiers (CCN, name, address)
- Quality metrics (composite scores, star ratings)
- Geographic data (coordinates, CBSA, rural/urban classification)
- Service offerings and patient volume estimates

## Data Processing Pipeline

1. **Raw Data Ingestion** - Load CSV/Excel files from `raw/`
2. **Data Cleaning** - Standardize formats, handle missing values
3. **Geographic Enhancement** - Add CBSA, rural/urban classifications
4. **Quality Scoring** - Calculate composite quality metrics
5. **Database Creation** - Save to SQLite in `processed/`

## Data Access

Access data through the analytics modules:

```python
from src.analytics import CMSAnalytics
from src.data import DATABASE_PATH, RAW_DATA_PATH

# Use analytics for processed data
analytics = CMSAnalytics()
providers = analytics.find_providers_by_location(state='CA')

# Direct database access if needed
import sqlite3
conn = sqlite3.connect(DATABASE_PATH)
```

## Data Updates

To update with new CMS data:

1. Download new files to `raw/`
2. Run data processing scripts
3. Update database in `processed/`
4. Verify data integrity

## Data Quality

- **Completeness**: Geographic data enhanced with multiple sources
- **Accuracy**: Quality metrics calculated from official CMS data
- **Timeliness**: Data from April 2025 CMS releases
- **Consistency**: Standardized formats and validation

## Privacy and Compliance

- All data is publicly available from CMS
- No patient-level information included
- Provider-level data only (aggregated metrics)
- Follows CMS data use guidelines
