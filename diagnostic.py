#!/usr/bin/env python3
"""
Diagnostic script to identify errors in the CMS data explorer
"""

import sys
import os

def test_imports():
    """Test all required imports"""
    print("🔍 Testing imports...")
    
    try:
        import pandas as pd
        print("✅ pandas imported successfully")
    except ImportError as e:
        print(f"❌ pandas import failed: {e}")
        return False
    
    try:
        import sqlite3
        print("✅ sqlite3 imported successfully")
    except ImportError as e:
        print(f"❌ sqlite3 import failed: {e}")
        return False
    
    try:
        import streamlit as st
        print("✅ streamlit imported successfully")
    except ImportError as e:
        print(f"❌ streamlit import failed: {e}")
        return False
    
    try:
        import plotly.express as px
        print("✅ plotly imported successfully")
    except ImportError as e:
        print(f"❌ plotly import failed: {e}")
        return False
    
    return True

def test_database():
    """Test database connection and data"""
    print("\n🗄️ Testing database...")
    
    if not os.path.exists('cms_homehealth.db'):
        print("❌ Database file 'cms_homehealth.db' not found")
        return False
    
    try:
        import sqlite3
        conn = sqlite3.connect('cms_homehealth.db')
        cursor = conn.cursor()
        
        # Test providers table
        cursor.execute("SELECT COUNT(*) FROM providers")
        provider_count = cursor.fetchone()[0]
        print(f"✅ Database connected - {provider_count:,} providers found")
        
        # Test a sample query
        cursor.execute("SELECT provider_name, state FROM providers LIMIT 3")
        samples = cursor.fetchall()
        print("✅ Sample providers:")
        for name, state in samples:
            print(f"   - {name} ({state})")
        
        conn.close()
        return True
        
    except Exception as e:
        print(f"❌ Database test failed: {e}")
        return False

def test_analytics():
    """Test analytics module"""
    print("\n📊 Testing analytics module...")
    
    try:
        from analytics import CMSAnalytics
        print("✅ Analytics module imported successfully")
        
        analytics = CMSAnalytics()
        print("✅ Analytics instance created successfully")
        
        # Test a simple query
        states = analytics.conn.execute("SELECT DISTINCT state FROM providers LIMIT 5").fetchall()
        print(f"✅ Sample states: {[s[0] for s in states]}")
        
        analytics.close()
        return True
        
    except Exception as e:
        print(f"❌ Analytics test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_streamlit_syntax():
    """Test streamlit app syntax"""
    print("\n🖥️ Testing Streamlit app syntax...")
    
    try:
        import ast
        
        # Test the simple streamlit app
        with open('streamlit_app_simple.py', 'r') as f:
            source_code = f.read()
        
        ast.parse(source_code)
        print("✅ streamlit_app_simple.py syntax is valid")
        
        # Test the main streamlit app
        with open('streamlit_app.py', 'r') as f:
            source_code = f.read()
        
        ast.parse(source_code)
        print("✅ streamlit_app.py syntax is valid")
        
        return True
        
    except SyntaxError as e:
        print(f"❌ Syntax error: {e}")
        return False
    except Exception as e:
        print(f"❌ Syntax test failed: {e}")
        return False

def main():
    print("🏥 CMS Home Health Data Explorer - Diagnostic Test")
    print("=" * 55)
    
    all_tests_passed = True
    
    # Run all tests
    if not test_imports():
        all_tests_passed = False
    
    if not test_database():
        all_tests_passed = False
    
    if not test_analytics():
        all_tests_passed = False
    
    if not test_streamlit_syntax():
        all_tests_passed = False
    
    print("\n" + "=" * 55)
    if all_tests_passed:
        print("🎉 All tests passed! The system should be working correctly.")
        print("\n📋 Next steps:")
        print("1. Run: streamlit run streamlit_app_simple.py")
        print("2. Open browser to: http://localhost:8501")
    else:
        print("❌ Some tests failed. Check the errors above.")
    
    return all_tests_passed

if __name__ == "__main__":
    main()
