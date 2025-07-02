# Legacy Files

This folder contains the original monolithic files that have been refactored into the new modular structure.

## Files

- **analytics.py** - Original monolithic analytics module (replaced by `src/analytics/`)
- **streamlit_app_simple.py** - Original main Streamlit application (replaced by `src/ui/app.py` and page modules)
- **streamlit_app.py** - Earlier version of the Streamlit application

## Purpose

These files are preserved for:
- Reference during development
- Comparison with new modular implementation
- Fallback if needed during transition
- Historical record of the application evolution

## Status

These files are **deprecated** and should not be used for new development. All new features should be implemented using the modular structure in the `src/` directory.

## Migration

The functionality from these files has been distributed as follows:

### analytics.py → src/analytics/
- **Base functionality** → `src/analytics/base.py`
- **Geographic analysis** → `src/analytics/geographic.py`
- **Market analysis** → `src/analytics/market.py`
- **Quality metrics** → `src/analytics/quality.py`
- **Rural/urban analysis** → `src/analytics/rural_urban.py`
- **Coverage deserts** → `src/analytics/coverage_deserts.py` (new)

### streamlit_app_simple.py → src/ui/
- **Main app structure** → `src/ui/app.py`
- **Provider search** → `src/ui/pages/provider_search.py`
- **Coverage deserts** → `src/ui/pages/coverage_deserts.py`
- **Market analysis** → `src/ui/pages/market_analysis.py`
- **Quality benchmarks** → `src/ui/pages/quality_benchmarks.py`
- **Common components** → `src/ui/components/common.py`
- **Other pages** → Individual page modules (placeholder implementations)

## Running Legacy Applications

If needed, these can still be run from the project root:

```bash
# Original analytics (import only)
from legacy.analytics import CMSAnalytics

# Original Streamlit app
streamlit run legacy/streamlit_app_simple.py
```

However, it's recommended to use the new modular application:

```bash
streamlit run app.py
```
