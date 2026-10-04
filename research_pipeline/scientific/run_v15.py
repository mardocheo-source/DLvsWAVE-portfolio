#!/usr/bin/env python3
"""Public V15 entry point for the contextual deep-history pipeline.

The implementation lives in the backward-compatible generic runner so V14 and
V15 do not diverge into two copies of the master, model, location, and reporting
workflow.  V15 behaviour is selected entirely by ``pipeline_request.json``.
"""
from __future__ import annotations

from run_v14 import main


if __name__ == "__main__":
    main()
