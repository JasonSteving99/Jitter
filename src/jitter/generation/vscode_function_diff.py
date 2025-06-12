"""
VS Code diff integration for function implementation reviews.

This module provides rich VS Code diff UI for reviewing AI-generated function implementations
before they are applied to the original source files.
"""

import subprocess
import os
from pathlib import Path

from jitter.source_manipulation.inspection import FunctionLocation
from jitter.source_manipulation.replacement import replace_function_implementation
from jitter.generation.types import GeneratedImplementation


def show_vscode_function_diff_and_get_changes(
    location: FunctionLocation, generated: GeneratedImplementation
) -> bool:
    """
    Display a function implementation diff in VS Code and apply user's final approved changes.
    
    This function creates a temporary copy of the original source file, applies the generated
    implementation to the temporary file, then shows a VS Code diff between the original
    and modified versions. If the user makes changes and closes VS Code, the entire original 
    file is overwritten with the user's final content.
    
    Args:
        location: FunctionLocation containing the original function's file and location info
        generated: GeneratedImplementation containing the AI-generated code and imports
        
    Returns:
        True if user approved and changes were applied, False if cancelled or failed
        
    Raises:
        FileNotFoundError: If the original source file doesn't exist
        OSError: If there are file permission issues
        ValueError: If the generated implementation is invalid
    """
    original_file_path = Path(location.filename)
    
    if not original_file_path.exists():
        raise FileNotFoundError(f"Source file not found: {location.filename}")
    
    # Read the original file content
    try:
        with open(original_file_path, 'r', encoding='utf-8') as f:
            original_content = f.read()
    except OSError as e:
        raise OSError(f"Cannot read original file {location.filename}: {e}")
    
    # Create a regular file next to the original with .jitter suffix for proper IDE support
    jitter_file_path = original_file_path.with_suffix(f".jitter{original_file_path.suffix}")
    
    try:
        # Write original content to jitter file
        with open(jitter_file_path, 'w', encoding='utf-8') as jitter_file:
            jitter_file.write(original_content)
        
        # Create FunctionLocation copy pointing to jitter file
        jitter_location = location._replace(filename=str(jitter_file_path))
        
        # Apply the generated implementation to the jitter file
        replace_function_implementation(jitter_location, generated)
        
        # Show VS Code diff between original file and modified jitter file
        print(f"\nOpening diff in VS Code: Original vs Proposed changes")
        print(f"Left pane: {original_file_path.name} (original)")
        print(f"Right pane: {jitter_file_path.name} (proposed changes - editable)")
        print("Make any desired changes in the right pane, then close VS Code to continue.\n")
        
        try:
            # Use VS Code diff with original file and jitter file
            vscode_command = ["code", "--diff", str(original_file_path), str(jitter_file_path), "--wait"]
            subprocess.run(vscode_command, check=True)
            print("VS Code diff window closed. Reading final content...")
            
            # Read the final content from the jitter file (right pane)
            with open(jitter_file_path, 'r', encoding='utf-8') as f:
                final_content = f.read()
            
            # Ask user for confirmation before applying changes
            while True:
                choice = input("\nApply the changes you made in VS Code? (y/n): ").lower().strip()
                if choice in ['y', 'yes']:
                    # Overwrite the entire original file with user's final approved content
                    with open(original_file_path, 'w', encoding='utf-8') as f:
                        f.write(final_content)
                    
                    print(f"Successfully applied changes to {original_file_path.name}")
                    return True
                elif choice in ['n', 'no']:
                    print("Changes discarded.")
                    return False
                else:
                    print("Please enter 'y' (yes) or 'n' (no)")
            
        except FileNotFoundError:
            print("Error: 'code' command not found. Make sure VS Code is installed and added to your system's PATH.")
            print("On macOS, you might need to run 'Shell Command: Install 'code' command in PATH' from VS Code's Command Palette.")
            return False
        except subprocess.CalledProcessError as e:
            print(f"Error executing VS Code command: {e}")
            return False
        except Exception as e:
            print(f"An unexpected error occurred: {e}")
            return False
        
    finally:
        # Clean up jitter file
        if jitter_file_path.exists():
            try:
                os.unlink(jitter_file_path)
            except OSError:
                pass  # Ignore cleanup errors


def open_function_in_vscode(location: FunctionLocation) -> None:
    """
    Open the function's file in VS Code at the function's starting line.
    
    This allows the user to see the context of the function that needs implementation
    while waiting for the LLM to generate a replacement.
    
    Args:
        location: FunctionLocation containing the function's file and line info
    """
    try:
        # Open file in VS Code at the specific line
        # Format: code --goto filename:line
        vscode_command = ["code", "--goto", f"{location.filename}:{location.start_line}"]
        subprocess.run(vscode_command, check=True)
        print(f"Opened {location.filename} at line {location.start_line} in VS Code")
    except FileNotFoundError:
        print("VS Code not found - continuing without opening file")
    except subprocess.CalledProcessError as e:
        print(f"Could not open file in VS Code: {e}")
    except Exception as e:
        print(f"Unexpected error opening VS Code: {e}")