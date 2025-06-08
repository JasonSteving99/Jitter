"""
PLJam - Live programming system for Python

PLJam implements a "live programming" system that allows developers to write code
with `NotImplementedError` placeholders and implement functions on-the-fly at runtime
using LLM assistance.
"""

from jitter.core.handler import not_implemented_handler

__version__ = "0.1.0"
__all__ = ["not_implemented_handler"]
