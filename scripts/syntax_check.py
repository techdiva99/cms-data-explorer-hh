#!/usr/bin/env python3
"""
Simple test to verify the Streamlit app syntax is correct
"""

import sys
import ast

def check_syntax(filename):
    """Check if Python file has valid syntax"""
    try:
        with open(filename, 'r') as f:
            source_code = f.read()
        
        # Parse the code
        ast.parse(source_code)
        print(f"✅ {filename}: Syntax is valid")
        return True
        
    except SyntaxError as e:
        print(f"❌ {filename}: Syntax error on line {e.lineno}: {e.msg}")
        return False
    except Exception as e:
        print(f"❌ {filename}: Error reading file: {e}")
        return False

if __name__ == "__main__":
    files_to_check = [
        'streamlit_app.py',
        'data_processor.py', 
        'analytics.py',
        'vector_database.py'
    ]
    
    all_good = True
    for filename in files_to_check:
        if not check_syntax(filename):
            all_good = False
    
    if all_good:
        print("\n🎉 All Python files have valid syntax!")
    else:
        print("\n❌ Some files have syntax errors that need to be fixed.")
        sys.exit(1)
