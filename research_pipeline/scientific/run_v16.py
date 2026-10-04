#!/usr/bin/env python3
"""Public V16 entry point for shifted-grid conditional-magnitude studies.

The implementation remains in the shared parameter-driven runner.  V16 adds
no event-specific code path: direct Horizons retrieval, target thresholds,
world hard negatives, focus dates, magnitude calibration and report selection
are all selected by ``pipeline_request.json``.
"""
from __future__ import annotations

from run_v14 import main


if __name__ == "__main__":
    main()
