#!/usr/bin/env python3
"""
Test runner for the scanner test suite.
Provides comprehensive testing with coverage reporting.
"""

import sys
import os
import subprocess
import argparse
from pathlib import Path


def run_tests(test_type='all', verbose=False, coverage=False, specific_test=None):
    """
    Run the test suite with specified options.
    
    Args:
        test_type: Type of tests to run ('unit', 'integration', 'all')
        verbose: Enable verbose output
        coverage: Enable coverage reporting
        specific_test: Run specific test file or test function
    """
    
    # Ensure we're in the right directory
    test_dir = Path(__file__).parent
    os.chdir(test_dir)
    
    # Build pytest command
    cmd = ['python', '-m', 'pytest']
    
    # Add coverage if requested
    if coverage:
        cmd.extend(['--cov=../scripts', '--cov-report=html', '--cov-report=term'])
    
    # Add verbosity
    if verbose:
        cmd.append('-v')
    else:
        cmd.append('-q')
    
    # Select test files based on type
    if specific_test:
        cmd.append(specific_test)
    elif test_type == 'unit':
        cmd.extend([
            'test_database_operations.py',
            'test_file_processing.py',
            'test_error_handling.py',
            'test_file_types.py'
        ])
    elif test_type == 'integration':
        cmd.append('test_integration.py')
    elif test_type == 'all':
        cmd.append('.')
    else:
        print(f"Unknown test type: {test_type}")
        return False
    
    # Add additional pytest options
    cmd.extend([
        '--tb=short',  # Shorter traceback format
        '--strict-markers',  # Strict marker checking
        '-x',  # Stop on first failure (remove for full run)
    ])
    
    print(f"Running command: {' '.join(cmd)}")
    print("=" * 60)
    
    try:
        result = subprocess.run(cmd, check=False)
        return result.returncode == 0
    except KeyboardInterrupt:
        print("\nTests interrupted by user")
        return False
    except Exception as e:
        print(f"Error running tests: {e}")
        return False


def check_dependencies():
    """Check if required test dependencies are installed."""
    required_packages = [
        'pytest',
        'PIL',  # Pillow
        'sqlite3',  # Built-in
    ]
    
    optional_packages = [
        'imagehash',
        'magic',
        'exifread',
        'numpy',
        'sklearn',
    ]
    
    missing_required = []
    missing_optional = []
    
    for package in required_packages:
        try:
            __import__(package)
        except ImportError:
            missing_required.append(package)
    
    for package in optional_packages:
        try:
            __import__(package)
        except ImportError:
            missing_optional.append(package)
    
    if missing_required:
        print("❌ Missing required packages:")
        for package in missing_required:
            print(f"  - {package}")
        print("\nInstall with: pip install -r requirements.txt")
        return False
    
    if missing_optional:
        print("⚠️  Missing optional packages (some tests may be skipped):")
        for package in missing_optional:
            print(f"  - {package}")
        print()
    
    print("✅ All required dependencies available")
    return True


def main():
    """Main test runner function."""
    parser = argparse.ArgumentParser(description='Run scanner test suite')
    parser.add_argument(
        '--type', 
        choices=['unit', 'integration', 'all'], 
        default='all',
        help='Type of tests to run'
    )
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Enable verbose output'
    )
    parser.add_argument(
        '--coverage', '-c',
        action='store_true',
        help='Enable coverage reporting'
    )
    parser.add_argument(
        '--test', '-t',
        help='Run specific test file or test function'
    )
    parser.add_argument(
        '--check-deps',
        action='store_true',
        help='Check dependencies and exit'
    )
    
    args = parser.parse_args()
    
    print("🧪 Scanner Test Suite")
    print("=" * 60)
    
    # Check dependencies
    if not check_dependencies():
        if not args.check_deps:
            print("\nCannot run tests due to missing dependencies")
        sys.exit(1)
    
    if args.check_deps:
        print("Dependencies check complete")
        sys.exit(0)
    
    # Run tests
    success = run_tests(
        test_type=args.type,
        verbose=args.verbose,
        coverage=args.coverage,
        specific_test=args.test
    )
    
    print("=" * 60)
    if success:
        print("✅ All tests passed!")
        sys.exit(0)
    else:
        print("❌ Some tests failed")
        sys.exit(1)


if __name__ == '__main__':
    main()