import functools
import inspect
import ast
import importlib
import sys
from pathlib import Path
from typing import NamedTuple, get_origin, get_args, Any, Union


class CustomTypeInfo(NamedTuple):
    """Information about a custom type found in function arguments."""
    
    name: str
    filename: str | None     # Filename if available
    source_code: str | None  # Source code if available
    start_line: int | None   # Start line if available
    end_line: int | None     # End line if available


class ArgumentInfo(NamedTuple):
    """Information about a function argument."""
    
    name: str
    type_annotation: str | None  # Raw annotation as string
    custom_types: list[CustomTypeInfo]  # Extracted custom types


def _is_builtin_type(type_obj) -> bool:
    """Check if a type is a built-in or primitive type."""
    if type_obj is None:
        return True
    
    # Handle actual type objects
    builtin_types = (int, float, str, bool, bytes, list, dict, tuple, set, frozenset, type(None))
    
    # Check if it's a built-in type
    if type_obj in builtin_types:
        return True
        
    # Check if it's defined in builtins
    if hasattr(type_obj, '__module__') and type_obj.__module__ == 'builtins':
        return True
    
    # Check if it's from typing module (Union, Optional, etc.)
    if hasattr(type_obj, '__module__') and type_obj.__module__ == 'typing':
        return True
        
    return False


def _extract_custom_types_from_annotation(annotation) -> list[CustomTypeInfo]:
    """Extract custom type information from a type annotation."""
    custom_types = []
    
    if annotation is None:
        return custom_types
    
    # Handle Union types and other generic types
    origin = get_origin(annotation)
    if origin is not None:
        # For Union, Optional, List[CustomType], etc. - check the args
        args = get_args(annotation)
        for arg in args:
            custom_types.extend(_extract_custom_types_from_annotation(arg))
        return custom_types
    
    # Skip built-in types
    if _is_builtin_type(annotation):
        return custom_types
    
    # This should be a custom type
    type_name = getattr(annotation, '__name__', str(annotation))
    
    # Try to get source information
    try:
        filename = inspect.getfile(annotation)
        source_lines, start_line = inspect.getsourcelines(annotation)
        source_code = ''.join(source_lines)
        end_line = start_line + len(source_lines) - 1
        
        custom_types.append(CustomTypeInfo(
            name=type_name,
            filename=filename,
            source_code=source_code,
            start_line=start_line,
            end_line=end_line
        ))
    except (TypeError, OSError):
        # Can't get source (built-in, dynamically created, etc.)
        custom_types.append(CustomTypeInfo(
            name=type_name,
            filename=None,
            source_code=None,
            start_line=None,
            end_line=None
        ))
    
    return custom_types


def _extract_function_arguments(func) -> list[ArgumentInfo]:
    """Extract argument information from a function."""
    arguments = []
    
    try:
        signature = inspect.signature(func)
        
        for param_name, param in signature.parameters.items():
            # Skip *args and **kwargs style parameters for now
            if param.kind in (param.VAR_POSITIONAL, param.VAR_KEYWORD):
                continue
                
            annotation = param.annotation
            annotation_str = None
            custom_types = []
            
            if annotation != param.empty:
                annotation_str = str(annotation)
                custom_types = _extract_custom_types_from_annotation(annotation)
            
            arguments.append(ArgumentInfo(
                name=param_name,
                type_annotation=annotation_str,
                custom_types=custom_types
            ))
    
    except (ValueError, TypeError):
        # Can't get signature information
        pass
    
    return arguments


class FunctionLocation(NamedTuple):
    """Container for function location information."""

    filename: str
    start_line: int
    end_line: int
    source_lines: list[str]
    arguments: list[ArgumentInfo]

    def source_code(self) -> str:
        """Get the complete source code as a single string."""
        return "".join(self.source_lines)

    def line_range(self) -> tuple[int, int]:
        """Get the line range as a tuple (start, end)."""
        return (self.start_line, self.end_line)

    def line_count(self) -> int:
        """Get the number of lines in the function."""
        return len(self.source_lines)

    def __str__(self) -> str:
        return f"{Path(self.filename).name}:{self.start_line}-{self.end_line}"


def get_function_lines(func) -> FunctionLocation:
    """
    Get the exact line numbers and source code of a function definition.

    Args:
        func: A function object to inspect

    Returns:
        FunctionLocation with filename, start_line, end_line, and source_lines

    Raises:
        TypeError: If the object is not a function or method
        OSError: If the source code cannot be retrieved (e.g., built-in functions,
                 functions defined in REPL, etc.)
    """
    # Try to unwrap decorated functions
    try:
        func = inspect.unwrap(func)
    except ValueError:
        # inspect.unwrap failed, continue with original function
        pass

    if not (inspect.isfunction(func) or inspect.ismethod(func)):
        raise TypeError(f"Expected function or method, got {type(func).__name__}")

    try:
        # Get source lines and starting line number
        source_lines, start_line = inspect.getsourcelines(func)
    except OSError as e:
        raise OSError(f"Cannot retrieve source for {func.__name__}: {e}")

    try:
        # Get the filename
        filename = inspect.getfile(func)
    except TypeError as e:
        raise OSError(f"Cannot retrieve file for {func.__name__}: {e}")

    # Calculate end line
    end_line = start_line + len(source_lines) - 1

    # Extract argument information
    arguments = _extract_function_arguments(func)

    return FunctionLocation(
        filename=filename,
        start_line=start_line,
        end_line=end_line,
        source_lines=source_lines,
        arguments=arguments,
    )


def print_function_info(func) -> None:
    """
    Print detailed information about a function's location and source.

    Args:
        func: Function to inspect
    """
    try:
        location = get_function_lines(func)
        print(f"Function: {func.__name__}")
        print(f"File: {location.filename}")
        print(
            f"Lines: {location.start_line}-{location.end_line} ({location.line_count()} lines)"
        )
        print("Source code:")
        for i, line in enumerate(location.source_lines, location.start_line):
            print(f"{i:4d}: {line}", end="")
    except (TypeError, OSError) as e:
        print(f"Error inspecting {func}: {e}")


# Example usage and testing
if __name__ == "__main__":
    # Test with a sample function
    def sample_function(x: int, y: str) -> str:
        """A sample function for testing."""
        result = f"{y}: {x}"
        return result

    # Test with a decorated function
    @functools.lru_cache(maxsize=128)
    def cached_function(n: int) -> int:
        """A cached function for testing."""
        if n < 0:
            return 0
        return n * 2

    # Test with a lambda
    square = lambda x: x**2

    # Test with a method
    class TestClass:
        def test_method(self, value: int) -> str:
            """A test method."""
            return f"Value: {value}"

    obj = TestClass()

    print("=== Testing various function types ===")
    print_function_info(sample_function)
    print()
    print_function_info(cached_function)
    print()
    print_function_info(square)
    print()
    print_function_info(obj.test_method)
    print()
    print_function_info(print)  # Built-in function - will show error
