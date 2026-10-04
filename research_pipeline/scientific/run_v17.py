#!/usr/bin/env python3
"""Public V17 entry point for interval operators and quantile preprocessing.

All study choices remain in ``pipeline_request.json``.  The shared runner is
used so interval aggregation, quantization, model search and reporting remain
available to future regions without a Japan-specific source fork.
"""
from __future__ import annotations

from run_v14 import main


if __name__ == "__main__":
    main()
