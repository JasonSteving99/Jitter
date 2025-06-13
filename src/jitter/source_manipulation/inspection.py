import ast
import functools
import importlib
import inspect
import re
from pathlib import Path
from typing import NamedTuple, get_args, get_origin, get_type_hints


class CustomTypeInfo(NamedTuple):
    """Information about a custom type found in function arguments."""

    name: str
    filename: str | None     # Filename if available
    source_code: str | None  # Source code if available
    start_line: int | None   # Start line if available
    end_line: int | None     # End line if available


class ReferenceInfo(NamedTuple):
    """Information about a @path.to.foo reference found in function source code."""

    raw_reference: str       # The original @path.to.foo or @path.to::foo string
    module_path: str         # The path.to part (before :: if present)
    target_name: str | None  # The foo part after :: (None for module-only references)
    resolved_module: str | None  # Full module name if successfully resolved
    source_code: str | None  # Source code of the referenced item if available
    filename: str | None     # Filename of the referenced item if available
    start_line: int | None   # Start line if available
    end_line: int | None     # End line if available
    error_message: str | None  # Error message if resolution failed


class ArgumentInfo(NamedTuple):
    """Information about a function argument."""

    name: str
    type_annotation: str | None  # Raw annotation as string
    custom_types: list[CustomTypeInfo]  # Extracted custom types


class ReturnTypeInfo(NamedTuple):
    """Information about a function's return type."""

    type_annotation: str | None  # Raw annotation as string
    custom_types: list[CustomTypeInfo]  # Extracted custom types


def _extract_references_from_source(source_code: str) -> list[str]:
    """Extract @path.to.foo and @path.to::foo style references from source code."""
    # Match @module.path, optionally followed by ::member (which we ignore)
    pattern = r'@([a-zA-Z_][a-zA-Z0-9_]*(?:\.[a-zA-Z_][a-zA-Z0-9_]*)*(?:::[a-zA-Z_][a-zA-Z0-9_]*)?)'
    
    matches = re.findall(pattern, source_code)
    references = [f'@{match}' for match in matches]
    
    return references


def _resolve_reference(raw_reference: str) -> ReferenceInfo:
    """Resolve a @path.to.foo or @path.to::foo reference using Python's import system."""
    # Remove the @ prefix
    reference_path = raw_reference[1:]
    
    # Check if it's a member reference (contains ::)
    if '::' in reference_path:
        module_path, target_name = reference_path.split('::', 1)
    else:
        # Module-only reference
        module_path = reference_path
        target_name = None
    
    try:
        # Try to import the module
        module = importlib.import_module(module_path)
        
        if target_name:
            # Member reference - get the specific member
            try:
                target_obj = getattr(module, target_name)
                
                # Try to get source information for the target object
                try:
                    filename = inspect.getfile(target_obj)
                    source_lines, start_line = inspect.getsourcelines(target_obj)
                    source_code = ''.join(source_lines)
                    end_line = start_line + len(source_lines) - 1
                    
                    return ReferenceInfo(
                        raw_reference=raw_reference,
                        module_path=module_path,
                        target_name=target_name,
                        resolved_module=module_path,
                        source_code=source_code,
                        filename=filename,
                        start_line=start_line,
                        end_line=end_line,
                        error_message=None
                    )
                except (TypeError, OSError):
                    # Can't get source (built-in, dynamically created, etc.)
                    return ReferenceInfo(
                        raw_reference=raw_reference,
                        module_path=module_path,
                        target_name=target_name,
                        resolved_module=module_path,
                        source_code=None,
                        filename=None,
                        start_line=None,
                        end_line=None,
                        error_message=None
                    )
            except AttributeError:
                return ReferenceInfo(
                    raw_reference=raw_reference,
                    module_path=module_path,
                    target_name=target_name,
                    resolved_module=None,
                    source_code=None,
                    filename=None,
                    start_line=None,
                    end_line=None,
                    error_message=f"Module {module_path} has no attribute {target_name}"
                )
        else:
            # Module-only reference
            try:
                filename = inspect.getfile(module)
                source_lines, start_line = inspect.getsourcelines(module)
                source_code = ''.join(source_lines)
                end_line = start_line + len(source_lines) - 1
                
                return ReferenceInfo(
                    raw_reference=raw_reference,
                    module_path=module_path,
                    target_name=None,
                    resolved_module=module_path,
                    source_code=source_code,
                    filename=filename,
                    start_line=start_line,
                    end_line=end_line,
                    error_message=None
                )
            except (TypeError, OSError):
                # Can't get file info or source (built-in module, C extension, etc.)
                return ReferenceInfo(
                    raw_reference=raw_reference,
                    module_path=module_path,
                    target_name=None,
                    resolved_module=module_path,
                    source_code=None,
                    filename=None,
                    start_line=None,
                    end_line=None,
                    error_message=None
                )
                
    except ImportError:
        return ReferenceInfo(
            raw_reference=raw_reference,
            module_path=module_path,
            target_name=target_name,
            resolved_module=None,
            source_code=None,
            filename=None,
            start_line=None,
            end_line=None,
            error_message=f"Could not import module {module_path}"
        )


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


def _extract_nested_types_from_custom_type(custom_type, visited: set = None) -> list[CustomTypeInfo]:
    """
    Recursively extract all nested custom types from a custom type's field annotations.
    
    Args:
        custom_type: The custom type (class) to inspect
        visited: Set of already-visited types to prevent infinite recursion
        
    Returns:
        List of CustomTypeInfo objects for all nested custom types found
    """
    if visited is None:
        visited = set()
    
    # Prevent infinite recursion
    if custom_type in visited:
        return []
    
    visited.add(custom_type)
    nested_types = []
    
    try:
        # Get type hints for the class
        type_hints = get_type_hints(custom_type)
        
        # Extract custom types from each field annotation
        for field_name, field_type in type_hints.items():
            field_custom_types = _extract_custom_types_from_annotation(field_type, visited)
            nested_types.extend(field_custom_types)
                    
    except (TypeError, AttributeError, NameError):
        # If get_type_hints fails, return empty list
        pass
    
    return nested_types


def _extract_custom_types_from_annotation(annotation, visited: set = None) -> list[CustomTypeInfo]:
    """Extract custom type information from a type annotation."""
    if visited is None:
        visited = set()
    
    custom_types = []

    if annotation is None:
        return custom_types

    # Handle Union types and other generic types
    origin = get_origin(annotation)
    if origin is not None:
        # For Union, Optional, List[CustomType], etc. - check the args
        args = get_args(annotation)
        for arg in args:
            custom_types.extend(_extract_custom_types_from_annotation(arg, visited))
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

    # Recursively extract nested types from this custom type
    nested_types = _extract_nested_types_from_custom_type(annotation, visited)
    custom_types.extend(nested_types)

    # Remove duplicates while preserving order
    seen_names = set()
    unique_types = []
    for custom_type in custom_types:
        if custom_type.name not in seen_names:
            seen_names.add(custom_type.name)
            unique_types.append(custom_type)

    return unique_types


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


def _extract_function_return_type(func) -> ReturnTypeInfo:
    """Extract return type information from a function."""
    try:
        signature = inspect.signature(func)
        return_annotation = signature.return_annotation
        
        annotation_str = None
        custom_types = []
        
        if return_annotation != signature.empty:
            annotation_str = str(return_annotation)
            custom_types = _extract_custom_types_from_annotation(return_annotation)
        
        return ReturnTypeInfo(
            type_annotation=annotation_str,
            custom_types=custom_types
        )
    except (ValueError, TypeError):
        # Can't get signature information
        return ReturnTypeInfo(
            type_annotation=None,
            custom_types=[]
        )


class FunctionLocation(NamedTuple):
    """Container for function location information."""

    filename: str
    start_line: int
    end_line: int
    source_lines: list[str]
    arguments: list[ArgumentInfo]
    return_type: ReturnTypeInfo
    references: list[ReferenceInfo]

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


def generate_import_statements_from_references(references: list[ReferenceInfo]) -> list[str]:
    """
    Generate import statements from ReferenceInfo objects.
    
    Only generates imports for modules themselves, never for specific members.
    For @foo.bar::baz references, generates 'from foo import bar'
    For @foo.bar.baz references, generates 'from foo.bar import baz'
    
    Args:
        references: List of ReferenceInfo objects to generate imports for
        
    Returns:
        List of import statement strings
    """
    imports = []
    
    for ref in references:
        if ref.error_message or not ref.resolved_module:
            # Skip failed references
            continue
            
        if ref.target_name:
            # Member reference like @foo.bar::baz -> from foo import bar
            module_parts = ref.module_path.split('.')
            if len(module_parts) > 1:
                from_module = '.'.join(module_parts[:-1])
                import_name = module_parts[-1]
                imports.append(f"from {from_module} import {import_name}")
            else:
                # Single module with member like @foo::bar -> import foo
                imports.append(f"import {ref.module_path}")
        else:
            # Module-only reference like @foo.bar.baz -> from foo.bar import baz
            module_parts = ref.module_path.split('.')
            if len(module_parts) > 1:
                from_module = '.'.join(module_parts[:-1])
                import_name = module_parts[-1]
                imports.append(f"from {from_module} import {import_name}")
            else:
                # Single module like @foo -> import foo
                imports.append(f"import {ref.module_path}")
    
    # Remove duplicates while preserving order
    seen = set()
    unique_imports = []
    for imp in imports:
        if imp not in seen:
            seen.add(imp)
            unique_imports.append(imp)
    
    return unique_imports


def _parse_existing_imports(file_content: str) -> set[str]:
    """
    Parse existing import statements from a Python file.
    
    Returns a set of normalized import statements for comparison.
    """
    try:
        tree = ast.parse(file_content)
    except SyntaxError:
        # If we can't parse the file, assume no imports
        return set()
    
    existing_imports = set()
    
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                existing_imports.add(f"import {alias.name}")
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                for alias in node.names:
                    existing_imports.add(f"from {node.module} import {alias.name}")
    
    return existing_imports


def add_imports_to_file(file_path: str, import_statements: list[str]) -> None:
    """
    Add import statements to the top of a Python file, avoiding duplicates.
    
    Args:
        file_path: Path to the Python file to modify
        import_statements: List of import statement strings to add
    """
    if not import_statements:
        return
    
    # Read the current file content
    with open(file_path, 'r') as f:
        file_content = f.read()
    
    # Parse existing imports
    existing_imports = _parse_existing_imports(file_content)
    
    # Filter out imports that already exist
    new_imports = [imp for imp in import_statements if imp not in existing_imports]
    
    if not new_imports:
        return  # No new imports to add
    
    # Find the best place to insert imports
    lines = file_content.split('\n')
    insert_index = 0
    
    # Skip over shebang, encoding declarations, and existing imports
    for i, line in enumerate(lines):
        stripped = line.strip()
        if (stripped.startswith('#') or 
            stripped.startswith('import ') or 
            stripped.startswith('from ') or
            stripped == '' or
            stripped.startswith('"""') or
            stripped.startswith("'''")):
            insert_index = i + 1
        else:
            break
    
    # Insert new imports
    for imp in reversed(new_imports):  # Insert in reverse to maintain order
        lines.insert(insert_index, imp)
    
    # Write the modified content back
    with open(file_path, 'w') as f:
        f.write('\n'.join(lines))


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
    
    # Extract return type information
    return_type = _extract_function_return_type(func)
    
    # Extract references from source code
    source_code = ''.join(source_lines)
    raw_references = _extract_references_from_source(source_code)
    references = [_resolve_reference(ref) for ref in raw_references]

    return FunctionLocation(
        filename=filename,
        start_line=start_line,
        end_line=end_line,
        source_lines=source_lines,
        arguments=arguments,
        return_type=return_type,
        references=references,
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
