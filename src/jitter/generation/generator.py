import asyncio
import inspect
from collections.abc import Callable
from typing import Any, cast

from pydantic import BaseModel, Field

from jitter.generation.llm import call_llm
from jitter.generation.ui import show_implementation_comparison_and_confirm


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


async def get_llm_implementation_suggestion(func: Callable[..., Any]) -> str:
    """
    Use LLM to generate a suggested implementation for a function.

    Args:
        func: The function that needs an implementation

    Returns:
        String containing the LLM-suggested Python code for the function
    """
    func_source = inspect.getsource(func)

    system_prompt = """You are a Python code generator. Given a function definition, generate a complete implementation.
Return only valid Python code that implements the function based on its signature and docstring.
The implementation should be practical and follow Python best practices."""

    english_description = f"Generate an implementation for this Python function:\n\n{func_source}"

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
    func: Callable[..., Any], call_context: dict | None = None  # noqa: ARG001
) -> str:
    """
    Generate a new implementation for a function that raised NotImplementedError.

    Prompts user to choose between AI generation or manual implementation.
    If AI is chosen, uses the UI comparison tool for accept/reject.

    Args:
        func: The function that needs an implementation
        call_context: Additional context about how the function was called

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
                suggested_impl = asyncio.run(get_llm_implementation_suggestion(func))
                
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
