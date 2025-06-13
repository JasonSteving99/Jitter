import asyncio
import inspect
from collections.abc import Callable
from typing import Any, cast

from pydantic import BaseModel, Field

from jitter.generation.llm import call_llm
from jitter.generation.vscode_function_diff import show_vscode_function_diff_and_get_changes
from jitter.source_manipulation.inspection import FunctionLocation, get_function_lines
from jitter.generation.types import GeneratedImplementation


class UserDeclinedImplementation(Exception):
    """Raised when user declines to implement a function."""
    pass


class ImplementationSuggestion(BaseModel):
    """Schema for LLM-generated implementation suggestions."""

    explanation: str = Field(description="Brief explanation of what the implementation does")
    necessary_imports: list[str] = Field(description="List of module import statements that are absolutely unavoidably necessary to implement this function")
    implementation: str = Field(description="Complete Python function definition ONLY - no import statements, just the function")


def prompt_user_for_implementation(func: Callable[..., Any]) -> str:
    """
    Prompt the user to provide an implementation for a function.

    This function will be replaced with something more sophisticated later.

    Args:
        func: The function that needs an implementation

    Returns:
        String containing the user-provided Python code for the function
    """
    func_name = func.__name__
    sig = inspect.signature(func)

    print(f"\nFunction '{func_name}' needs an implementation.")
    print(f"Signature: {func_name}{sig}")

    if func.__doc__:
        print(f"Docstring: {func.__doc__}")

    print("\nPlease provide the implementation (end with an empty line):")

    lines = []
    while True:
        try:
            line = input()
            if line.strip() == "" and lines:
                break
            lines.append(line)
        except (EOFError, KeyboardInterrupt):
            break

    if not lines:
        # Return a default implementation if user provides nothing
        return f'''def {func_name}{sig}:
    """Generated default implementation for {func_name}."""
    print(f"Default implementation: {func_name} called")
    return f"Default result from {func_name}"
'''

    return "\n".join(lines)


def get_llm_implementation_suggestion(func: Callable[..., Any], call_stack: list[FunctionLocation]) -> ImplementationSuggestion:
    """
    Use LLM to generate a suggested implementation for a function.

    Args:
        func: The function that needs an implementation
        call_stack: List of FunctionLocation objects representing the call stack leading to this function

    Returns:
        ImplementationSuggestion containing the LLM-suggested implementation and imports
    """
    func_source = inspect.getsource(func)

    # Build context from call stack (limit to last 10 functions to keep context manageable)
    limited_call_stack = call_stack[-10:] if len(call_stack) > 10 else call_stack

    func_name = func.__name__
    func_sig = inspect.signature(func)

    # Get argument type information for the target function
    try:
        func_location = get_function_lines(func)
        argument_types_context = ""

        # Collect all custom types from arguments
        all_custom_types = {}
        for arg in func_location.arguments:
            for custom_type in arg.custom_types:
                if custom_type.name not in all_custom_types and custom_type.source_code:
                    all_custom_types[custom_type.name] = custom_type

        if all_custom_types:
            argument_types_context += "\n\nARGUMENT TYPE DEFINITIONS:\n"
            argument_types_context += "The function uses these custom types in its arguments:\n\n"

            for type_name, custom_type in all_custom_types.items():
                argument_types_context += f"--- {type_name} (from {custom_type.filename}:{custom_type.start_line}-{custom_type.end_line}) ---\n"
                argument_types_context += custom_type.source_code
                argument_types_context += "\n"
    except Exception:
        # If we can't get argument info, continue without it
        argument_types_context = ""

    # Get implementation references information for the target function
    try:
        # Extract reference context from the target function
        references_context = ""
        references_with_source = [ref for ref in func_location.references if ref.source_code and not ref.error_message]
        
        # Log skipped references
        for ref in func_location.references:
            if ref.error_message:
                print(f"TESTING!!! Skipping reference {ref.raw_reference}: {ref.error_message}")
            elif not ref.source_code:
                print(f"TESTING!!! Skipping reference {ref.raw_reference}: no source code available")
        
        if references_with_source:
            references_context += "\n\nREFERENCED DEPENDENCIES:\n"
            references_context += "The function's implementation plan references these modules/functions that should be used in the implementation.\n"
            references_context += "IMPORTANT: Do NOT include import statements for these modules in your implementation - the module imports will be automatically added to the file (access members via the module).\n\n"
            
            for ref in references_with_source:
                if ref.target_name:
                    # Member reference like @foo.bar::baz -> from foo import bar -> use bar.baz
                    module_parts = ref.module_path.split('.')
                    if len(module_parts) > 1:
                        import_name = module_parts[-1]
                        usage = f"{import_name}.{ref.target_name}"
                    else:
                        usage = f"{ref.module_path}.{ref.target_name}"
                    references_context += f"--- {ref.raw_reference} ({ref.target_name} from {ref.filename}:{ref.start_line}-{ref.end_line}) - Use as: {usage} ---\n"
                else:
                    # Module-only reference like @foo.bar.baz -> from foo.bar import baz -> use baz
                    module_parts = ref.module_path.split('.')
                    if len(module_parts) > 1:
                        usage = module_parts[-1]
                    else:
                        usage = ref.module_path
                    references_context += f"--- {ref.raw_reference} (module from {ref.filename}) - Use as: {usage} ---\n"
                references_context += cast(str, ref.source_code)
                references_context += "\n"
    except Exception:
        # If we can't get reference info, continue without it
        references_context = ""

    call_stack_context = "\n\nTARGET FUNCTION TO IMPLEMENT:\n"
    call_stack_context += f"Function name: {func_name}\n"
    call_stack_context += f"Function signature: {func_name}{func_sig}\n"
    if func.__doc__:
        call_stack_context += f"Function docstring: {func.__doc__}\n"

    call_stack_context += argument_types_context
    call_stack_context += references_context

    call_stack_context += "\n\nCALL STACK CONTEXT:\n"
    call_stack_context += f"Here are the functions in the call stack that led to {func_name} being called (showing last {len(limited_call_stack)} of {len(call_stack)}):\n\n"

    for i, func_location in enumerate(limited_call_stack):
        call_stack_context += f"--- Call Stack Level {i+1}: {func_location.filename}:{func_location.start_line}-{func_location.end_line} ---\n"
        call_stack_context += func_location.source_code()
        call_stack_context += "\n"

    system_prompt = f"""You are a Python code generator. Given a function definition and its call stack context, generate a complete implementation.

The call stack shows you exactly how this function is being used and what the calling functions expect.
Use this context to understand the function's purpose and generate an appropriate implementation.

Return only valid Python code that implements the function based on its signature, docstring, and calling context.
The implementation should be practical and follow Python best practices.{call_stack_context}"""

    english_description = f"Generate an implementation for this Python function located at {func_location.filename}:{func_location.start_line}-{func_location.end_line}:\n\n{func_source}"

    print("\033[93mTESTING! LLM SYSTEM PROMPT:\n\n" + system_prompt + "\n\n\033[0m")

    try:
        response = call_llm(
            system_prompt=system_prompt,
            english_description=english_description,
            model_name="models/gemini-2.5-flash-preview-05-20",
            response_schema=ImplementationSuggestion,
        )

        return cast(ImplementationSuggestion, response.parsed)
    except Exception as e:
        # Fallback to user prompt if LLM fails
        print(f"LLM generation failed: {e}")
        return ImplementationSuggestion(
            explanation="Fallback implementation due to LLM failure",
            necessary_imports=[],
            implementation=prompt_user_for_implementation(func)
        )




def generate_implementation_for_function(
    func: Callable[..., Any], call_stack: list[FunctionLocation]
) -> GeneratedImplementation:
    """
    Generate a new implementation for a function that raised NotImplementedError.

    Prompts user to choose between AI generation or manual implementation.
    If AI is chosen, uses the UI comparison tool for accept/reject.

    Args:
        func: The function that needs an implementation
        call_stack: List of FunctionLocation objects representing the call stack leading to this function

    Returns:
        GeneratedImplementation containing the new Python code and necessary imports
    """
    func_name = func.__name__
    sig = inspect.signature(func)

    print(f"\nFunction '{func_name}' needs an implementation.")
    print(f"Signature: {func_name}{sig}")

    if func.__doc__:
        print(f"Docstring: {func.__doc__}")

    # Ask user if they want AI generation or manual implementation
    while True:
        choice = input("\nGenerate implementation with AI? (y/n): ").lower().strip()

        if choice in ['y', 'yes']:
            # AI generation path
            try:
                suggested_impl = get_llm_implementation_suggestion(func, call_stack)

                # Use VS Code diff for review
                try:
                    location = get_function_lines(func)
                    generated_impl = GeneratedImplementation(
                        implementation=suggested_impl.implementation,
                        necessary_imports=suggested_impl.necessary_imports
                    )
                    
                    if show_vscode_function_diff_and_get_changes(location, generated_impl):
                        # Changes were applied successfully
                        return generated_impl
                    # If VS Code diff returns False, fall through to manual option
                except Exception as e:
                    print(f"VS Code diff failed: {e}")
                    print("Falling back to manual implementation...")
                else:
                    # User declined AI implementation, give them option to write manually or decline entirely
                    while True:
                        choice = input("\nWrite implementation manually instead? (y/n): ").lower().strip()
                        if choice in ['y', 'yes']:
                            return GeneratedImplementation(
                                implementation=prompt_user_for_implementation(func),
                                necessary_imports=[]
                            )
                        elif choice in ['n', 'no']:
                            raise UserDeclinedImplementation("User declined to provide implementation")
                        else:
                            print("Please enter 'y' (yes) or 'n' (no)")

            except Exception as e:
                print(f"Error generating AI suggestion: {e}")
                print("Falling back to manual implementation.")
                return GeneratedImplementation(
                    implementation=prompt_user_for_implementation(func),
                    necessary_imports=[]
                )

        elif choice in ['n', 'no']:
            # Manual implementation path
            return GeneratedImplementation(
                implementation=prompt_user_for_implementation(func),
                necessary_imports=[]
            )
        else:
            print("Please enter 'y' (yes) or 'n' (no)")
