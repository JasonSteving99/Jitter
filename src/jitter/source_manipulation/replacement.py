import re
from pathlib import Path

from jitter.source_manipulation.inspection import FunctionLocation, get_function_lines


def replace_function_implementation(
    location: FunctionLocation, new_implementation: str
) -> None:
    """
    Replace a function's entire implementation in its source file.

    Args:
        location: FunctionLocation containing the function's file and line info
        new_implementation: Complete new function definition as a string

    Raises:
        FileNotFoundError: If the source file doesn't exist
        OSError: If there are file permission issues
        ValueError: If the new implementation is invalid or doesn't start with 'def'
    """
    file_path = Path(location.filename)

    if not file_path.exists():
        raise FileNotFoundError(f"Source file not found: {location.filename}")

    # Validate that new implementation is a complete function definition
    if not new_implementation.strip().startswith("def "):
        raise ValueError(
            "New implementation must be a complete function definition starting with 'def'"
        )

    # Read the entire file
    try:
        with open(file_path, encoding="utf-8") as f:
            lines = f.readlines()
    except OSError as e:
        raise OSError(f"Cannot read file {location.filename}: {e}")

    # Validate line numbers
    if location.start_line < 1 or location.end_line > len(lines):
        raise ValueError(
            f"Invalid line range {location.start_line}-{location.end_line} "
            f"for file with {len(lines)} lines"
        )

    # Get the original indentation level from the function definition
    original_first_line = location.source_lines[0] if location.source_lines else ""
    base_indentation = _get_indentation(original_first_line)

    # Process the new implementation with proper indentation
    processed_lines = _process_new_implementation(new_implementation, base_indentation)

    # Replace the function lines (convert to 0-based indexing)
    start_idx = location.start_line - 1
    end_idx = location.end_line

    # Replace the lines
    new_lines = lines[:start_idx] + processed_lines + lines[end_idx:]

    # Write the modified content back
    try:
        with open(file_path, "w", encoding="utf-8") as f:
            f.writelines(new_lines)
    except OSError as e:
        raise OSError(f"Cannot write to file {location.filename}: {e}")


def _get_indentation(line: str) -> str:
    """Extract the indentation from a line of code."""
    return re.match(r"^(\s*)", line).group(1) if line else ""


def _process_new_implementation(
    new_implementation: str, base_indentation: str
) -> list[str]:
    """
    Process the new implementation to match the original indentation.

    Args:
        new_implementation: The complete new function definition
        base_indentation: Base indentation level to maintain

    Returns:
        List of lines ready to insert into the file
    """
    if not new_implementation.strip():
        raise ValueError("New implementation cannot be empty")

    # Split into lines
    impl_lines = new_implementation.splitlines()

    processed_lines = []
    for i, line in enumerate(impl_lines):
        if line.strip():  # Non-empty line
            if i == 0:  # First line (def statement)
                processed_lines.append(base_indentation + line.lstrip() + "\n")
            else:  # Body lines - preserve internal indentation structure
                processed_lines.append(base_indentation + line + "\n")
        else:  # Empty line
            processed_lines.append("\n")

    return processed_lines


# Example usage
if __name__ == "__main__":
    # This would be used in conjunction with get_function_lines()
    # from the original script

    # Example: Replace entire function
    new_function = '''def sample_function(x: int, y: str) -> str:
    """An updated sample function."""
    result = f"Updated: {y} = {x}"
    print(f"Processing: {result}")
    return result'''

    print("Function replacer ready to use!")
    print("Use with get_function_lines() to get the FunctionLocation,")
    print(
        "then call replace_function_implementation() with a complete function definition"
    )

    def sample_function(x: int, y: str) -> str:
        """A sample function."""
        raise NotImplementedError("This function is not implemented yet")

    # Usage example:
    location = get_function_lines(sample_function)
    replace_function_implementation(location, new_function)
