"""
Data module for the CMS Home Health Data Explorer.

This module handles:
- Raw data loading from CSV/Excel files
- Data processing and cleaning
- Database operations
- Data integration workflows

Structure:
- raw/: Raw data files (CSV, Excel, etc.)
- processed/: Processed data (SQLite database, cleaned datasets)
- integrations/: Data integration utilities and workflows
"""

from . import integrations

__all__ = ['integrations']

# Data file paths
import os
DATA_DIR = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))  # Go up to project root
RAW_DATA_PATH = os.path.join(DATA_DIR, 'data', 'raw')
PROCESSED_DATA_PATH = os.path.join(DATA_DIR, 'data', 'processed')
DATABASE_PATH = os.path.join(PROCESSED_DATA_PATH, 'cms_homehealth.db')
