"""Source code manipulation module for PLJam."""

from jitter.source_manipulation.hot_reload import hot_reload
from jitter.source_manipulation.inspection import get_function_lines
from jitter.source_manipulation.replacement import replace_function_implementation

__all__ = ["get_function_lines", "replace_function_implementation", "hot_reload"]
