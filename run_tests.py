#!/usr/bin/env python3
"""
Test runner script for fernlabs-api using pytest

This script provides an easy way to run tests from the project root directory.
"""

import sys
import os
import subprocess
import argparse


def run_pytest_tests(test_path="tests", args=None):
    """Run pytest with the given arguments"""
    cmd = [sys.executable, "-m", "pytest", test_path]

    if args:
        cmd.extend(args)

    try:
        result = subprocess.run(cmd, capture_output=False, text=True, cwd=os.getcwd())
        return result.returncode == 0
    except Exception as e:
        print(f"Error running pytest: {e}")
        return False


def run_basic_tests():
    """Run the basic functionality tests"""
    print("Running basic tests...")
    return run_pytest_tests("tests", ["-k", "test_generator_simple", "-v"])


def run_comprehensive_tests():
    """Run the comprehensive test suite"""
    print("Running comprehensive tests...")
    return run_pytest_tests("tests", ["-k", "test_generator", "-v"])


def run_all_tests():
    """Run all tests"""
    print("Running all tests...")
    return run_pytest_tests("tests", ["-v"])


def run_specific_test(test_name):
    """Run a specific test by name"""
    print(f"Running test: {test_name}")
    return run_pytest_tests("tests", ["-k", test_name, "-v"])


def run_tests_with_coverage():
    """Run tests with coverage reporting"""
    print("Running tests with coverage...")
    return run_pytest_tests(
        "tests",
        ["--cov=fernlabs_api", "--cov-report=term-missing", "--cov-report=html", "-v"],
    )


def main():
    """Main function"""
    parser = argparse.ArgumentParser(description="Run fernlabs-api tests with pytest")
    parser.add_argument("--basic", action="store_true", help="Run only basic tests")
    parser.add_argument(
        "--comprehensive", action="store_true", help="Run only comprehensive tests"
    )
    parser.add_argument("--all", action="store_true", help="Run all tests (default)")
    parser.add_argument(
        "--coverage", action="store_true", help="Run tests with coverage reporting"
    )
    parser.add_argument("--test", type=str, help="Run a specific test by name")
    parser.add_argument(
        "--verbose", "-v", action="store_true", help="Enable verbose output"
    )
    parser.add_argument("--pytest-args", type=str, help="Additional pytest arguments")

    args = parser.parse_args()

    # If no specific test type is specified, run all
    if not any([args.basic, args.comprehensive, args.test]):
        args.all = True

    success = True

    if args.basic:
        print("=" * 60)
        print("RUNNING BASIC TESTS")
        print("=" * 60)
        if not run_basic_tests():
            success = False
        print()

    if args.comprehensive:
        print("=" * 60)
        print("RUNNING COMPREHENSIVE TESTS")
        print("=" * 60)
        if not run_comprehensive_tests():
            success = False
        print()

    if args.all:
        print("=" * 60)
        print("RUNNING ALL TESTS")
        print("=" * 60)
        if not run_all_tests():
            success = False
        print()

    if args.test:
        print("=" * 60)
        print(f"RUNNING SPECIFIC TEST: {args.test}")
        print("=" * 60)
        if not run_specific_test(args.test):
            success = False
        print()

    if args.coverage:
        print("=" * 60)
        print("RUNNING TESTS WITH COVERAGE")
        print("=" * 60)
        if not run_tests_with_coverage():
            success = False
        print()

    # Final summary
    print("=" * 60)
    print("TEST RUN SUMMARY")
    print("=" * 60)

    if success:
        print("🎉 All tests completed successfully!")
        print("\n✅ Your WorkflowAgent is working correctly!")
        print("\n💡 Additional pytest options:")
        print("  - Run specific test: python -m pytest tests/ -k 'test_name'")
        print("  - Run with coverage: python -m pytest tests/ --cov=fernlabs_api")
        print("  - Run in parallel: python -m pytest tests/ -n auto")
        print("  - Run with markers: python -m pytest tests/ -m unit")
    else:
        print("❌ Some tests failed. Check the output above for details.")
        print("\n💡 Tips:")
        print("  - Run with --verbose for more details")
        print("  - Check the tests/README_TESTING.md for troubleshooting")
        print("  - Ensure all dependencies are installed")
        print(
            "  - Try running individual test files: python -m pytest tests/test_generator_simple.py"
        )

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
