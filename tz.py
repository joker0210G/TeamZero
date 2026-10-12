#!/usr/bin/env python3
"""TeamZero Unified CLI (`tz`) Entrypoint.

Forwards execution to `teamzero.cli.main`.
"""

import sys
from teamzero.cli import main

if __name__ == "__main__":
    main()
