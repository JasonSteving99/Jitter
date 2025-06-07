import functools
import inspect
from pathlib import Path
from typing import NamedTuple


class FunctionLocation(NamedTuple):
    """Container for function location information."""

    filename: str
    start_line: int
    end_line: int
    source_lines: list[str]

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

    return FunctionLocation(
        filename=filename,
        start_line=start_line,
        end_line=end_line,
        source_lines=source_lines,
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
