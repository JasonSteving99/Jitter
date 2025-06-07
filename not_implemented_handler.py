def get_function_from_not_implemented_error():
    """Get the function object where NotImplementedError was raised."""
    # Get the current exception info
    exc_type, exc_value, exc_traceback = sys.exc_info()

    if exc_type is not NotImplementedError:
        return None

    # Walk through the traceback to find where the error was raised
    tb = exc_traceback
    while tb.tb_next is not None:
        tb = tb.tb_next

    frame = tb.tb_frame

    # Try to get the function from the frame
    try:
        # This works for most cases
        func_name = frame.f_code.co_name

        # Check if it's in locals first (for nested functions)
        if func_name in frame.f_locals:
            candidate = frame.f_locals[func_name]
            if callable(candidate) and hasattr(candidate, "__code__"):
                if candidate.__code__ is frame.f_code:
                    return candidate

        # Check globals
        if func_name in frame.f_globals:
            candidate = frame.f_globals[func_name]
            if callable(candidate) and hasattr(candidate, "__code__"):
                if candidate.__code__ is frame.f_code:
                    return candidate

        # For methods, try to reconstruct from self/cls
        if "self" in frame.f_locals:
            obj = frame.f_locals["self"]
            if hasattr(obj, func_name):
                method = getattr(obj, func_name)
                if hasattr(method, "__func__"):
                    return method.__func__

    except Exception:
        pass

    return None


# Usage with context manager
import sys


class NotImplementedHandler:
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, exc_traceback):
        if exc_type is NotImplementedError:
            func = get_function_from_not_implemented_error()
            if func:
                print(f"NotImplementedError raised in: {func.__name__}")
                print(
                    f"Location: {func.__code__.co_filename}:{func.__code__.co_firstlineno}"
                )
                print(f"Docstring: {func.__doc__}")
        return False  # Don't suppress the exception


def foo2():
    bar2()


def bar2():
    unimplemented_feature()


# Example usage with context manager
def unimplemented_feature():
    """A feature that's not ready yet."""
    raise NotImplementedError("Coming soon!")


with NotImplementedHandler():
    foo2()
