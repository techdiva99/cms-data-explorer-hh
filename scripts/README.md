# Scripts Directory

This directory contains utility scripts for data processing, integration, and system operations.

## Scripts

### Data Download Scripts
- **download_cbsa.py** - Downloads CBSA (Core Based Statistical Area) data
- **download_crosswalk.py** - Downloads ZIP-to-county crosswalk data

### Data Integration Scripts
- **integrate_cbsa.py** - Integrates CBSA data with provider data
- **integrate_crosswalk.py** - Integrates crosswalk data for geographic analysis
- **enhance_cbsa_rural.py** - Enhances data with rural/urban classifications

### Testing and Diagnostics
- **demo.py** - Demonstration script for analytics functionality
- **live_test.py** - Live testing of application components
- **diagnostic.py** - System diagnostic and health checks
- **syntax_check.py** - Python syntax validation

### Setup and Configuration
- **setup.sh** - Initial setup and configuration script

## Usage

Run scripts from the project root directory:

```bash
# Data processing
python scripts/download_cbsa.py
python scripts/integrate_cbsa.py

# Testing
python scripts/demo.py
python scripts/diagnostic.py
```

## Migration to Modular Structure

Many of these scripts contain functionality that should be moved to the modular structure:

- **Data processing logic** → `src/utils/data_processing.py`
- **Download utilities** → `src/utils/downloads.py`
- **Integration workflows** → `src/utils/integrations.py`

## Best Practices

- Keep scripts focused on specific tasks
- Use the `src/utils/` modules for reusable functionality
- Add proper error handling and logging
- Include documentation and usage examples
