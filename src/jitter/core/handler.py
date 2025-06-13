import inspect
import sys
from collections.abc import Generator
from contextlib import contextmanager

from jitter.generation.generator import generate_implementation_for_function, UserDeclinedImplementation
from jitter.source_manipulation.hot_reload import hot_reload
from jitter.source_manipulation.inspection import get_function_lines
from jitter.source_manipulation.replacement import replace_function_implementation
from jitter.generation.vscode_function_diff import open_function_in_vscode


def extract_call_chain_from_traceback():
    """
    Extract the complete call chain from the current NotImplementedError traceback.

    CRUCIAL! IGNORE THE CALLS IN THE CHAIN THAT ORIGINATE WITHIN THIS JITTER MODULE.
    WE'RE ONLY CONCERNED WITH THE FUNCTIONS IN THE UNDERLYING USER PROGRAM.

    Returns:
        List of (function, args, kwargs, filename, lineno) tuples representing the call chain
        from the context manager down to where NotImplementedError was raised.
    """
    exc_type, exc_value, exc_traceback = sys.exc_info()

    if exc_type is not NotImplementedError:
        return []

    call_chain = []
    tb = exc_traceback
    context_manager_found = False

    # Walk through the traceback to collect all frames
    frames = []
    while tb is not None:
        frames.append(tb.tb_frame)
        tb = tb.tb_next

    # Process frames in reverse order (from context manager down to error)
    for i, frame in enumerate(frames):
        code = frame.f_code
        func_name = code.co_name

        # Skip frames until we find the context manager
        if not context_manager_found:
            if func_name == "Jitter":
                context_manager_found = True
                continue
            else:
                continue

        # Skip internal generator machinery
        if func_name in ("__enter__", "__exit__", "_GeneratorContextManager"):
            continue

        try:
            # Get the function object
            func = _get_function_from_frame(frame)
            if func is None:
                continue

            # Skip calls originating from the jitter module itself
            func_module = inspect.getmodule(func)
            current_module = sys.modules[__name__]
            if func_module is current_module:
                continue

            # Extract arguments from the frame
            args, kwargs = _extract_arguments_from_frame(frame, func)

            # Extract file and line number
            filename = code.co_filename
            lineno = frame.f_lineno

            call_chain.append((func, args, kwargs, filename, lineno))

        except Exception as e:
            print(f"[Jitter] Warning: Could not extract call info for {func_name}: {e}")
            continue

    return call_chain


def _get_function_from_frame(frame):
    """Get the function object from a stack frame."""
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
            if hasattr(method, "__func__") and method.__func__.__code__ is frame.f_code:
                return method
            elif hasattr(method, "__code__") and method.__code__ is frame.f_code:
                return method

    # For class methods
    if "cls" in frame.f_locals:
        cls = frame.f_locals["cls"]
        if hasattr(cls, func_name):
            method = getattr(cls, func_name)
            if hasattr(method, "__func__") and method.__func__.__code__ is frame.f_code:
                return method

    print(f"[Jitter] ****ERROR!!!! No function found in frame: {frame}")
    return None


def _extract_arguments_from_frame(frame, func):
    """Extract the original arguments from a frame using function signature."""
    try:
        sig = inspect.signature(func)
        locals_dict = frame.f_locals

        args = []
        kwargs = {}

        # Handle bound methods - skip 'self' or 'cls' if present
        bound_arg = None
        if "self" in locals_dict and hasattr(func, "__self__"):
            bound_arg = "self"
        elif "cls" in locals_dict and hasattr(func, "__self__"):
            bound_arg = "cls"

        for param_name, param in sig.parameters.items():
            if param_name == bound_arg:
                continue  # Skip self/cls for bound methods

            if param_name in locals_dict:
                value = locals_dict[param_name]

                if param.kind == param.VAR_POSITIONAL:
                    # *args
                    if isinstance(value, tuple):
                        args.extend(value)
                elif param.kind == param.VAR_KEYWORD:
                    # **kwargs
                    if isinstance(value, dict):
                        kwargs.update(value)
                else:
                    # Regular parameter
                    if param.default == param.empty:
                        # Required positional argument
                        args.append(value)
                    else:
                        # Optional argument, add as keyword
                        kwargs[param_name] = value

        return args, kwargs

    except Exception as e:
        # Fallback: try to guess based on common patterns
        print(f"[Jitter] Warning: Could not extract signature for {func}: {e}")
        return [], {}


def _rerun_from_unimplemented(call_chain):
    """Rerun only the top function from the call chain."""
    if not call_chain:
        raise ValueError("Cannot rerun empty call chain")

    # Only call the first (top) function - the deterministic nature of programs
    # will ensure the rest of the call stack is automatically called
    top_func, top_args, top_kwargs, _, _ = call_chain[0]

    # Get fresh function reference after potential hot reload
    func_module = inspect.getmodule(top_func)
    if func_module is not None:
        fresh_func = getattr(func_module, top_func.__name__, top_func)
    else:
        fresh_func = top_func

    print(f"[Jitter] Rerunning top function: {fresh_func.__name__}")
    print("\n" + "─" * 60)
    print("PROGRAM OUTPUT:")
    print("─" * 60, end="\n\n")
    result = fresh_func(*top_args, **top_kwargs)
    print("\n" + ("─" * 60))
    print("END PROGRAM OUTPUT")
    print("─" * 60)
    return result


@contextmanager
def Jitter(enable_replay: bool = True) -> Generator[None, None, None]:
    """
    Context manager that handles NotImplementedError with full call chain replay.

    Args:
        enable_replay: Whether to enable automatic retry by replaying the call chain

    Usage:
        with Jitter():
            result = some_function_that_might_raise_not_implemented()
    """
    try:
        yield

    except NotImplementedError as e:
        # Extract the complete call chain from this original exception.
        call_chain = extract_call_chain_from_traceback()

        while (
            True
        ):  # Keep looping until we implement and run every unimplemented function.
            if not enable_replay:
                print("\n═══ [Jitter] NotImplementedError in call chain ═══")
                for i, (func, args, kwargs, filename, lineno) in enumerate(call_chain):
                    print(
                        f"  {i + 1}. {func.__name__} at {filename}:{lineno}"
                    )
                print("═" * 50)
                raise e

            print("\n╔══════════════════════════════════════════════════╗")
            print("║ NotImplementedError detected! Extracting call   ║")
            print("║ chain for replay...                             ║")
            print("╚══════════════════════════════════════════════════╝")

            if not call_chain:
                print("[Jitter] Could not extract call chain, re-raising original error")
                raise e

            print(f"\n┌─ [Jitter] Extracted call chain with {len(call_chain)} calls ─┐")
            for i, (func, args, kwargs, filename, lineno) in enumerate(call_chain):
                print(
                    f"│  {i + 1}. {func.__name__}({len(args)} args, {len(kwargs)} kwargs) at {filename}:{lineno}"
                )
            print("└" + "─" * (len(f"Extracted call chain with {len(call_chain)} calls") + 20) + "┘")

            # Generate implementation for the failing function (last in call chain)
            if call_chain:
                failing_func, _, _, _, _ = call_chain[
                    -1
                ]  # Last function in chain raised NotImplementedError
                print(f"\n>>> Generating implementation for {failing_func.__name__}...")
                
                # Open the function in VS Code so user can see context while waiting for LLM
                failing_func_location = get_function_lines(failing_func)
                open_function_in_vscode(failing_func_location)
                
                try:
                    # Get the call stack of function locations for code generation. Everything but
                    # the last in the call chain since that's the failing func we're gonna rewrite.
                    call_stack = [get_function_lines(func) for func, _, _, _, _ in call_chain[:-1]]
                    # Generate new implementation (user confirmation and file replacement handled inside)
                    generated = generate_implementation_for_function(failing_func, call_stack)

                    # Hot reload the module to get the updated function
                    func_module = inspect.getmodule(failing_func)
                    if func_module is None:
                        raise RuntimeError(f"Could not get module for function {failing_func.__name__}") from e
                    hot_reload(func_module)

                    print(
                        f"\n✓ Successfully replaced implementation of "
                        f"{failing_func.__name__}"
                    )
                except UserDeclinedImplementation:
                    print("[Jitter] User declined replacement. Re-raising original error.")
                    raise e
                except Exception as gen_error:
                    print(f"[Jitter] Failed to generate/replace implementation: {gen_error}")
                    raise gen_error

            # Rerun the call chain that reached the unimplemented function
            print("\n▶ Attempting to rerun call chain that reached unimplemented...")
            try:
                result = _rerun_from_unimplemented(call_chain)
                print("✓ Rerun of call chain succeeded!")
                return result
            except NotImplementedError as rerun_error:
                e = rerun_error
                # Extract the complete call chain from this latest exception.
                call_chain = extract_call_chain_from_traceback()
                continue


# Usage examples and tests
if __name__ == "__main__":

    def level_4_function(zzz):
        raise NotImplementedError("This is also not implemented.")

    def level_3_function(z=10):
        """The deepest function that raises NotImplementedError."""
        print(f"In level_3_function with z={z} - raising NotImplementedError")
        raise NotImplementedError("This feature is not implemented yet")

    def level_2_function(x, y=10):
        """Middle function that calls level_3."""
        print(f"In level_2_function with x={x}, y={y}")
        return level_3_function()

    def level_1_function(name: str, *args, **kwargs):
        """Top-level function that starts the call chain."""
        print(f"In level_1_function with name='{name}', args={args}, kwargs={kwargs}")
        return level_2_function(4242, y=kwargs.get("y", 20))

    print("\n" + "=" * 50)
    print("    Testing Call Chain Replay")
    print("=" * 50)
    try:
        with Jitter():
            result = level_1_function("test", "extra_arg", y=30, extra_arg_debug=True)
            print(f"\nFinal Result: {result}")
    except NotImplementedError:
        print("\n❌ Event replay failed!")
