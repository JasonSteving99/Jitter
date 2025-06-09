import asyncio
import inspect
from collections.abc import Callable
from typing import Any, cast

from pydantic import BaseModel, Field

from jitter.generation.llm import call_llm
from jitter.generation.ui import show_implementation_comparison_and_confirm
from jitter.source_manipulation.inspection import FunctionLocation, get_function_lines


class UserDeclinedImplementation(Exception):
    """Raised when user declines to implement a function."""
    pass


class ImplementationSuggestion(BaseModel):
    """Schema for LLM-generated implementation suggestions."""

    implementation: str = Field(description="Complete Python function implementation code")
    explanation: str = Field(description="Brief explanation of what the implementation does")


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


async def get_llm_implementation_suggestion(func: Callable[..., Any], call_stack: list[FunctionLocation]) -> str:
    """
    Use LLM to generate a suggested implementation for a function.

    Args:
        func: The function that needs an implementation
        call_stack: List of FunctionLocation objects representing the call stack leading to this function

    Returns:
        String containing the LLM-suggested Python code for the function
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
            argument_types_context += f"\n\nARGUMENT TYPE DEFINITIONS:\n"
            argument_types_context += f"The function uses these custom types in its arguments:\n\n"
            
            for type_name, custom_type in all_custom_types.items():
                argument_types_context += f"--- {type_name} (from {custom_type.filename}:{custom_type.start_line}-{custom_type.end_line}) ---\n"
                argument_types_context += custom_type.source_code
                argument_types_context += "\n"
    except Exception:
        # If we can't get argument info, continue without it
        argument_types_context = ""
    
    call_stack_context = f"\n\nTARGET FUNCTION TO IMPLEMENT:\n"
    call_stack_context += f"Function name: {func_name}\n"
    call_stack_context += f"Function signature: {func_name}{func_sig}\n"
    if func.__doc__:
        call_stack_context += f"Function docstring: {func.__doc__}\n"
    
    call_stack_context += argument_types_context
    
    call_stack_context += f"\n\nCALL STACK CONTEXT:\n"
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

    english_description = f"Generate an implementation for this Python function:\n\n{func_source}"

    print("\033[93mTESTING! LLM SYSTEM PROMPT:\n\n" + system_prompt + "\n\n\033[0m")

    try:
        response = await call_llm(
            system_prompt=system_prompt,
            english_description=english_description,
            model_name="models/gemini-2.5-flash-preview-05-20",
            response_schema=ImplementationSuggestion,
        )

        return cast(ImplementationSuggestion, response.parsed).implementation
    except Exception as e:
        # Fallback to user prompt if LLM fails
        print(f"LLM generation failed: {e}")
        return prompt_user_for_implementation(func)




def generate_implementation_for_function(
    func: Callable[..., Any], call_stack: list[FunctionLocation]
) -> str:
    """
    Generate a new implementation for a function that raised NotImplementedError.

    Prompts user to choose between AI generation or manual implementation.
    If AI is chosen, uses the UI comparison tool for accept/reject.

    Args:
        func: The function that needs an implementation
        call_stack: List of FunctionLocation objects representing the call stack leading to this function

    Returns:
        String containing the new Python code for the function
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
                suggested_impl = asyncio.run(get_llm_implementation_suggestion(func, call_stack))
                
                # Use UI comparison tool for accept/reject
                if show_implementation_comparison_and_confirm(func, suggested_impl):
                    return suggested_impl
                else:
                    # User declined AI implementation, give them option to write manually or decline entirely
                    while True:
                        choice = input("\nWrite implementation manually instead? (y/n): ").lower().strip()
                        if choice in ['y', 'yes']:
                            return prompt_user_for_implementation(func)
                        elif choice in ['n', 'no']:
                            raise UserDeclinedImplementation("User declined to provide implementation")
                        else:
                            print("Please enter 'y' (yes) or 'n' (no)")
                    
            except Exception as e:
                print(f"Error generating AI suggestion: {e}")
                print("Falling back to manual implementation.")
                return prompt_user_for_implementation(func)
                
        elif choice in ['n', 'no']:
            # Manual implementation path
            return prompt_user_for_implementation(func)
        else:
            print("Please enter 'y' (yes) or 'n' (no)")
