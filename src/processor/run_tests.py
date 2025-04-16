#!/usr/bin/env python
"""
Test runner for AI-OCR processor tests.
This script sets up the necessary environment for testing and runs the test suite.
"""
import argparse
import os
import subprocess
import sys
from pathlib import Path

# Add the project root to the Python path
sys.path.append(str(Path(__file__).parent))

def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="Run AI-OCR processor tests")
    parser.add_argument("--test-path", type=str, default="app/tests",
                        help="Path to test directory")
    parser.add_argument("--model-api-key", type=str, 
                        help="OpenAI API key for tests")
    parser.add_argument("--skip-ai", action="store_true",
                        help="Skip tests that require AI model")
    parser.add_argument("-v", "--verbose", action="store_true",
                        help="Enable verbose output")
    parser.add_argument("-k", type=str, 
                        help="Only run tests that match the given substring expression")
    parser.add_argument("--no-capture", action="store_true",
                        help="Don't capture stdout/stderr")
    return parser.parse_args()

def create_test_data_dir():
    """Create a directory for test data if it doesn't exist."""
    test_data_dir = Path("test_data")
    test_data_dir.mkdir(exist_ok=True)
    return str(test_data_dir)

def run_tests(args):
    """Run the test suite."""
    # Set up environment variables
    env = os.environ.copy()
    
    # Use provided API key or try to get from environment
    if args.model_api_key:
        env["MODEL_API_KEY"] = args.model_api_key
    
    # Set test data directory
    env["TEST_DATA_DIR"] = create_test_data_dir()
    
    # Build the pytest command
    cmd = ["python", "-m", "pytest", args.test_path]
    
    # Add additional arguments
    if args.verbose:
        cmd.append("-v")
    
    if args.k:
        cmd.extend(["-k", args.k])
    
    if args.no_capture:
        cmd.append("-s")
    
    if args.skip_ai:
        cmd.append("-k not test_invoice_extraction and not test_report_extraction")
    
    # Run the tests
    print(f"Running tests: {' '.join(cmd)}")
    result = subprocess.run(cmd, env=env)
    
    return result.returncode

if __name__ == "__main__":
    args = parse_args()
    sys.exit(run_tests(args)) 