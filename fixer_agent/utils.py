# fixer_agent/utils.py

import logging
from .config import LOG_LEVEL

def format_finding(finding: dict) -> str:
    """
    Human-readable string for a finding.
    """
    return f"[{finding['service'].upper()}] {finding['resource']}: {finding['issue']}"

def setup_logger():
    logging.basicConfig(
        level=getattr(logging, LOG_LEVEL.upper(), logging.INFO),
        format="%(asctime)s - %(levelname)s - %(message)s"
    )
    return logging.getLogger("fixer_agent")
