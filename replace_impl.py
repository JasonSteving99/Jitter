import inspect
import types
from collections.abc import Callable
from typing import Any


def replace_function_implementation(func: Callable[..., Any], new_code: str) -> None:
    """
    Replace the implementation of an existing function with new code.

    Args:
        func: The function object whose implementation should be replaced
        new_code: String containing the new Python code for the function

    Raises:
        SyntaxError: If the new code is not valid Python
        ValueError: If no function found in code or parameter structure mismatch
    """
    # Compile the code string
    try:
        compiled_code = compile(new_code, "<string>", "exec")
    except SyntaxError as e:
        raise SyntaxError(f"Invalid Python syntax: {e}") from e

    # Find the function's code object in the compiled constants
    func_code_obj = None
    for const in compiled_code.co_consts:
        if isinstance(const, types.CodeType) and const.co_name != "<module>":
            func_code_obj = const
            break

    if func_code_obj is None:
        raise ValueError("No function definition found in the provided code")

    # Create the new function using the original function's globals
    new_func = types.FunctionType(
        func_code_obj,
        func.__globals__,  # Use original function's globals - this is key!
        func_code_obj.co_name,
    )

    # Validate parameter structure compatibility
    original_sig = inspect.signature(func)
    new_sig = inspect.signature(new_func)

    if not _parameter_structures_match(original_sig, new_sig):
        raise ValueError(
            f"Parameter structure mismatch. Original: {original_sig}, New: {new_sig}"
        )

    # Replace the original function's implementation
    func.__code__ = new_func.__code__
    # func.__defaults__ = new_func.__defaults__
    # func.__kwdefaults__ = new_func.__kwdefaults__

    # Copy annotations from the original function to preserve type information
    func.__annotations__ = func.__annotations__.copy()


def _parameter_structures_match(
    sig1: inspect.Signature, sig2: inspect.Signature
) -> bool:
    """
    Check if two function signatures have compatible parameter structures.
    Ignores type annotations and parameter names, only checks counts.
    """
    params1 = list(sig1.parameters.values())
    params2 = list(sig2.parameters.values())

    if len(params1) != len(params2):
        return False

    return True


# Example usage and tests
if __name__ == "__main__":
    # Example 1: Replace a simple function's implementation
    def greet(name: str) -> str:
        return f"Hello, {name}!"

    print("Original:", greet("World"))

    new_implementation = """
def greet(name: str) -> str:
    return f"Hi there, {name}! How are you?"
"""

    replace_function_implementation(greet, new_implementation)
    print("After replacement:", greet("World"))

    # Example 2: Demonstrate that the original function object is modified
    def add(a: int, b: int) -> int:
        return a + b

    # Store a reference to the same function object
    original_add_reference = add

    print("Original add(3, 4):", add(3, 4))
    print("Reference add(3, 4):", original_add_reference(3, 4))

    multiply_code = """
def add(a: int, b: int) -> int:
    return a * b  # Now it multiplies instead!
"""

    replace_function_implementation(add, multiply_code)
    print("After replacement add(3, 4):", add(3, 4))
    print("Reference after replacement(3, 4):", original_add_reference(3, 4))

    # Example 3: Show that new function can access same globals as original
    import math

    def calculate_area(radius: float) -> float:
        return math.pi * radius**2

    print("Original area:", calculate_area(5.0))

    new_area_code = """
def calculate_area(radius: float) -> float:
    # This can access math because it uses the original function's globals
    return 2 * math.pi * radius  # Now calculates circumference instead
"""

    replace_function_implementation(calculate_area, new_area_code)
    print("After replacement (circumference):", calculate_area(5.0))

    # Example 4: Show signature validation working
    try:
        wrong_signature_code = """
def add(a: int, b: int, c: int) -> int:  # Extra parameter!
    return a * b * c
"""
        replace_function_implementation(add, wrong_signature_code)
    except ValueError as e:
        print("Signature validation caught error:", e)
