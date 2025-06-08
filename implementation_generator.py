import asyncio
import inspect
from collections.abc import Callable
from typing import Any, cast

from pydantic import BaseModel, Field

from llm import call_llm


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


def prompt_user_for_acceptance_or_edit(suggested_impl: str, func: Callable[..., Any]) -> str:
    """
    Present the LLM suggestion to the user and allow them to accept or edit it.

    Args:
        suggested_impl: The LLM-generated implementation
        func: The original function

    Returns:
        Final implementation (either accepted suggestion or user-edited version)
    """
    func_name = func.__name__

    print(f"\nLLM suggested implementation for '{func_name}':")
    print("=" * 50)
    print(suggested_impl)
    print("=" * 50)

    while True:
        choice = input("\nAccept this implementation? (y/n/e for edit): ").lower().strip()

        if choice in ['y', 'yes']:
            return suggested_impl
        elif choice in ['n', 'no']:
            return prompt_user_for_implementation(func)
        elif choice in ['e', 'edit']:
            print("\nEdit the implementation (end with an empty line):")
            print("Current implementation:")
            for i, line in enumerate(suggested_impl.split('\n'), 1):
                print(f"{i:2}: {line}")
            print("\nEnter your modified version:")

            lines = []
            while True:
                try:
                    line = input()
                    if line.strip() == "" and lines:
                        break
                    lines.append(line)
                except (EOFError, KeyboardInterrupt):
                    break

            if lines:
                return "\n".join(lines)
        else:
            print("Please enter 'y' (yes), 'n' (no), or 'e' (edit)")


def generate_implementation_for_function(
    func: Callable[..., Any], call_context: dict | None = None
) -> str:
    """
    Generate a new implementation for a function that raised NotImplementedError.

    Uses LLM to generate a suggested implementation, then allows user to accept or edit it.

    Args:
        func: The function that needs an implementation
        call_context: Additional context about how the function was called

    Returns:
        String containing the new Python code for the function
    """
    try:
        # Get LLM suggestion
        suggested_impl = asyncio.run(get_llm_implementation_suggestion(func))

        # Let user accept or edit the suggestion
        return prompt_user_for_acceptance_or_edit(suggested_impl, func)
    except Exception as e:
        print(f"Error generating LLM suggestion: {e}")
        # Fallback to original user prompt method
        return prompt_user_for_implementation(func)
