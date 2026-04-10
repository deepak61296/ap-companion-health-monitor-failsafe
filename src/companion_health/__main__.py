"""
Entry point for python -m companion_health.

AP_FLAKE8_CLEAN
"""

import sys

from .cli import main

if __name__ == '__main__':
    sys.exit(main())
