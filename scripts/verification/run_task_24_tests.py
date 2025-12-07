#!/usr/bin/env python3
"""Simple test runner for Task 24 integration tests."""

import sys
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT))

# Import and run tests
try:
    from test_ai_workflow_integration import run_all_integration_tests
    
    print("Starting Task 24 Integration Tests...")
    success = run_all_integration_tests()
    
    if success:
        print("\n✅ All Task 24 tests passed!")
        sys.exit(0)
    else:
        print("\n❌ Some Task 24 tests failed!")
        sys.exit(1)
        
except Exception as e:
    print(f"\n❌ Error running tests: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
