#!/usr/bin/env python3
"""
Load test runner for batch API
Wrapper script to run locust with locustfile.py
"""
import sys
import os
from pathlib import Path

# Ensure locustfile.py is in the same directory
LOCUST_DIR = Path(__file__).parent
LOCUSTFILE = LOCUST_DIR / "locustfile.py"


def main():
    """Run locust with the batch API locustfile"""
    from locust.main import main as locust_main

    # Set the locustfile path
    if '--locustfile' not in sys.argv and '-f' not in sys.argv:
        sys.argv.insert(1, '-f')
        sys.argv.insert(2, str(LOCUSTFILE))

    # Run locust
    sys.exit(locust_main())


if __name__ == "__main__":
    main()
