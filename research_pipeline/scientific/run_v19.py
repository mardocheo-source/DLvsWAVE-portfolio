#!/usr/bin/env python3
"""Public V19 entry point for exact start search and budget-matched timing.

All scientific choices live in the project ``pipeline_request.json``.  The
shared runner keeps the start-date search, compact-master search, modelling,
controls, localization and report generation reusable for other regions.
"""
from __future__ import annotations

from run_v14 import main


if __name__ == "__main__":
    main()
