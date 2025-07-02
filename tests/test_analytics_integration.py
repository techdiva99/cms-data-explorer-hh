"""
Tests for the analytics modules integration.
"""

import unittest
import sys
import os

# Add the src directory to the path for testing
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from src.analytics import CMSAnalytics
from src.analytics.coverage_deserts import CoverageDesertAnalytics


class TestAnalyticsIntegration(unittest.TestCase):
    """Test cases for analytics module integration."""
    
    def test_cms_analytics_import(self):
        """Test that CMSAnalytics can be imported and instantiated."""
        try:
            analytics = CMSAnalytics()
            self.assertIsNotNone(analytics)
            self.assertTrue(hasattr(analytics, 'find_providers_by_location'))
            self.assertTrue(hasattr(analytics, 'identify_coverage_deserts'))
        except Exception as e:
            self.fail(f"Failed to import/instantiate CMSAnalytics: {e}")
    
    def test_coverage_desert_analytics_methods(self):
        """Test that coverage desert analytics methods exist."""
        try:
            analytics = CoverageDesertAnalytics()
            self.assertTrue(hasattr(analytics, 'identify_coverage_deserts'))
            self.assertTrue(hasattr(analytics, 'calculate_market_potential'))
            self.assertTrue(hasattr(analytics, 'analyze_provider_expansion_opportunity'))
        except Exception as e:
            self.fail(f"Failed to test CoverageDesertAnalytics: {e}")
    
    def test_analytics_module_structure(self):
        """Test that the analytics module has the expected structure."""
        import src.analytics as analytics_module
        
        # Check that main classes are available
        self.assertTrue(hasattr(analytics_module, 'CMSAnalytics'))
        
        # Check submodules exist
        expected_modules = [
            'base', 'geographic', 'market', 'quality', 
            'rural_urban', 'coverage_deserts'
        ]
        
        for module_name in expected_modules:
            try:
                module = getattr(analytics_module, module_name, None)
                if module is None:
                    # Try importing directly
                    exec(f"from src.analytics import {module_name}")
                    self.assertTrue(True, f"Module {module_name} imported successfully")
            except ImportError as e:
                self.fail(f"Failed to import analytics.{module_name}: {e}")


if __name__ == '__main__':
    unittest.main()
