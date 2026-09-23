"""
Laya Fast-Path Execution Engine (<300ms deterministic execution)
"""

from .executor import FastPathExecutor, get_fast_path_executor

__all__ = ["FastPathExecutor", "get_fast_path_executor"]
