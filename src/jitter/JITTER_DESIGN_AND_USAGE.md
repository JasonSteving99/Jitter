# Jitter Design Guide: Structuring Programs for Incremental Development

## Table of Contents
1. [What is Jitter?](#what-is-jitter)
2. [The Functional Programming Foundation](#the-functional-programming-foundation)
3. [The @-Reference System](#the--reference-system)
4. [Core Design Principles](#core-design-principles)
5. [Data Structure Design](#data-structure-design)
6. [Function Design Patterns](#function-design-patterns)
7. [Error Handling Strategy](#error-handling-strategy)
8. [Module Organization](#module-organization)
9. [The Incremental Development Workflow](#the-incremental-development-workflow)
10. [Complete Example: Calculator Implementation](#complete-example-calculator-implementation)
11. [Anti-Patterns to Avoid](#anti-patterns-to-avoid)
12. [Advanced Patterns](#advanced-patterns)

## What is Jitter?

Jitter is a "live programming" system that explores an interactive take on how we develop Python applications. Instead of the traditional cycle of write → test → debug → restart, Jitter enables **incremental, just-in-time development** where functions are implemented exactly when they're needed during program execution.

### The Core Innovation

When your program encounters a `NotImplementedError`, instead of crashing, Jitter:

1. **Captures the complete execution context** (call stack, function arguments, types)
2. **Provides AI-assisted implementation** using LLM with full context
3. **Hot-swaps the implementation** directly in your source files
4. **Resumes execution** from exactly where it left off

This enables a **sketch-first, implement-later** approach where you focus on program structure and logic flow, then fill in implementation details interactively as your program discovers what it needs.

## The Functional Programming Foundation

> **🎯 CRITICAL: Jitter works best with functional programming patterns. This is not optional—it's the architectural foundation that makes incremental development reliable and predictable.**

### Why Functional Programming?

Jitter's hot-reloading and incremental development capabilities depend on **predictable, composable code**. Functional programming provides exactly this through:

- **Immutable data structures** that eliminate state synchronization issues during hot reloading
- **Pure functions** that can be replaced independently without side effects
- **Explicit data flow** that makes dependencies clear for LLM generation
- **Composable design** that supports building programs incrementally

### The Golden Rules

1. **All logic in top-level functions** - No nested function definitions or complex class hierarchies
2. **Functions operate only on explicitly passed data** - No global state, no hidden dependencies  
3. **Use Result objects and Optional types, NEVER exceptions** - The only exception allowed is `NotImplementedError` for Jitter
4. **Immutable data structures everywhere** - Frozen dataclasses and NamedTuples only

## The @-Reference System

> **🎯 MAXIMUM IMPORTANCE: The @-reference system is Jitter's secret weapon for providing context to LLM code generation. Master this pattern.**

### What Are @-References?

@-References are special comments that tell Jitter (and the LLM) about dependencies and context when implementing functions. They follow these formats:

```python
# Reference an entire module
@module.name

# Reference a specific class or function
@module.name::ClassName
@module.name::function_name
```

### Strategic Placement in Function Bodies

**Best Practice: Place @-references in docstrings or as implementation notes:**

```python
def tokenize(input_string: str) -> list[Token]:
    """
    Tokenizes an arithmetic expression string into tokens.
    
    Makes use of all the dataclasses in @calculator.tokenizer
    to represent different token types (Integer, Float, PlusOp, etc.)
    """
    raise NotImplementedError("Tokenization not yet implemented")

def interpret(tokens: list[Token]) -> float:
    """
    Interprets a list of tokens and evaluates the expression.
    
    Uses @calculator.operations::add, @calculator.operations::multiply,
    and @calculator.operations::divide for arithmetic operations.
    """
    raise NotImplementedError("Interpretation logic needed")
```

### Context-Driven Implementation

When Jitter encounters these functions, it:

1. **Parses the @-references** from the function source code
2. **Resolves them** using Python's import system
3. **Extracts source code** for referenced items
4. **Provides rich context** to the LLM including:
   - Function signature and call context
   - Referenced code and documentation
   - Custom type definitions
   - Example usage from call stack

### Reference Patterns

**Module-level references** when you need multiple items:
```python
def calculate_complex_formula(data):
    """
    Complex calculation involving multiple operations.
    Implementation will use functions from @math.operations
    """
```

**Specific member references** for targeted dependencies:
```python
def parse_data(raw_input):
    """
    Parse input using @parser.tokenizer::tokenize and 
    @parser.analyzer::analyze_tokens
    """
```

**Cross-module references** for integration:
```python
def end_to_end_process(input_data):
    """
    Complete processing pipeline:
    1. Parse with @input.parser::parse
    2. Transform with @transform.processor::process  
    3. Output with @output.formatter::format
    """
```

## Core Design Principles

### 1. Sketch-First Architecture

Structure your program as a hierarchy of function calls, starting from high-level orchestration down to specific operations:

```python
def main():
    """Main program orchestration."""
    input_data = get_user_input()
    parsed_data = parse_input(input_data)
    result = process_data(parsed_data)
    display_result(result)

def parse_input(raw_input: str) -> ParsedData:
    """Parse user input into structured data."""
    raise NotImplementedError("Input parsing logic needed")

def process_data(data: ParsedData) -> ProcessedResult:
    """Core business logic processing."""
    raise NotImplementedError("Processing logic needed")
```

### 2. Dependency-Driven Development

Let your program tell you what it needs. When you run it:

1. **High-level functions** run first and call unimplemented dependencies
2. **Context is captured** when each `NotImplementedError` is hit
3. **Dependencies are implemented** with full knowledge of how they're used
4. **Process repeats** until all functions are implemented

### 3. Context-Rich Implementation

Each function gets implemented with maximum context:

```python
# When this function is called during execution:
result = calculate_tax(gross_income=50000, tax_rate=0.22, deductions=5000)

# The LLM sees the following context:
# - Function signature: calculate_tax(gross_income: float, tax_rate: float, deductions: float) -> float
# - Actual call: calculate_tax(gross_income=50000, tax_rate=0.22, deductions=5000)
# - Call context: where it's called from and why
# - Type information: float parameters and return type
# - Any @-references in the function for additional context
```

## Data Structure Design

> **🎯 CRITICAL: Use frozen dataclasses for all domain objects. No exceptions.**

### Frozen Dataclasses Pattern

**Use frozen dataclasses for all domain objects:**

```python
from dataclasses import dataclass

@dataclass(frozen=True)
class User:
    id: int
    name: str
    email: str

@dataclass(frozen=True)
class Order:
    id: int
    user_id: int
    amount: float
    items: list[str]  # This is fine - the list reference is immutable

@dataclass(frozen=True)
class ProcessingResult:
    success: bool
    data: dict[str, any] | None = None
    error_message: str | None = None
```

### Why Frozen Dataclasses?

1. **Hot-reload safety**: No state synchronization issues when code changes
2. **Predictable behavior**: Cannot be modified after creation
3. **Clear data contracts**: Explicit fields with type annotations
4. **No hidden methods**: No behavior beyond data storage
5. **LLM-friendly**: Simple, clear structure for code generation

### NamedTuple for Complex Containers

For complex immutable containers with methods, use NamedTuple:

```python
from typing import NamedTuple

class FunctionLocation(NamedTuple):
    """Container for function metadata."""
    filename: str
    start_line: int
    end_line: int
    source_lines: list[str]
    arguments: list[ArgumentInfo]
    return_type: str | None
    
    def get_source_code(self) -> str:
        """Get the complete function source code."""
        return ''.join(self.source_lines)
```

### Pydantic Models for Validation

Use Pydantic when you need input validation or complex serialization:

```python
from pydantic import BaseModel, validator

class APIRequest(BaseModel):
    """API request with validation."""
    user_id: int
    amount: float
    currency: str = "USD"
    
    @validator('amount')
    def amount_must_be_positive(cls, v):
        if v <= 0:
            raise ValueError('Amount must be positive')
        return v
```

## Function Design Patterns

### 1. Pure Function Structure

**Every function should be pure when possible:**

```python
def calculate_discount(price: float, discount_percent: float) -> float:
    """
    Calculate discounted price.
    
    Args:
        price: Original price
        discount_percent: Discount as percentage (e.g., 0.15 for 15%)
    
    Returns:
        float: Discounted price
    """
    if price < 0 or discount_percent < 0 or discount_percent > 1:
        raise ValueError("Invalid input parameters")
    
    return price * (1 - discount_percent)
```

### 2. Comprehensive Type Annotations

**Use detailed type annotations:**

```python
def process_orders(
    orders: list[Order], 
    user_preferences: dict[int, UserPreference]
) -> ProcessingResult:
    """
    Process a batch of orders according to user preferences.
    
    Implementation will use @order.processor::validate_order and
    @preference.matcher::match_preferences
    """
    raise NotImplementedError("Order processing logic needed")
```

### 3. Explicit Error Handling

**Document all possible errors:**

```python
def divide_numbers(a: float, b: float) -> Result:
    """
    Divide two numbers using functional error handling.
    
    Args:
        a: Dividend
        b: Divisor
        
    Returns:
        Result: Contains division result or error information
        
    Never raises exceptions - uses Result object for all error cases
    including division by zero and invalid inputs.
    """
    raise NotImplementedError("Division logic with Result-based error handling needed")
```

### 4. Functional Composition

**Build complex operations from simple functions:**

```python
def process_user_data(raw_data: str) -> Result:
    """
    Complete user data processing pipeline with functional error handling.
    
    Uses @validation.checker::validate_input,
    @parsing.parser::parse_user_data, and
    @transform.normalizer::normalize_user
    
    This creates a clear call chain for incremental implementation
    with each stage returning Result objects for composable error handling.
    """
    raise NotImplementedError("User data processing pipeline with Result chaining needed")
```

## Error Handling Strategy

> **🎯 CRITICAL: Jitter promotes functional programming patterns. The ONLY exception that should be raised is `NotImplementedError` for Jitter's implementation assistance. All other error handling should use return values.**

### Functional Error Handling with Return Values

**Use Result objects instead of exceptions:**

```python
@dataclass(frozen=True)
class Result:
    """Functional result type for error handling."""
    success: bool
    data: any | None = None
    error_code: str | None = None
    error_message: str | None = None

@dataclass(frozen=True)
class UserResult:
    """Specific result type for user operations."""
    user: User | None = None
    error: str | None = None
    
    @property
    def is_success(self) -> bool:
        return self.error is None

def load_user_data(user_id: int) -> UserResult:
    """
    Load user data from storage.
    
    Returns UserResult with either user data or error information.
    Uses @database.connector::get_user for data access.
    """
    raise NotImplementedError("User loading with result-based error handling needed")

def validate_user_id(user_id: int) -> Result:
    """
    Validate user ID format and constraints.
    
    Returns Result indicating validation success or failure details.
    """
    raise NotImplementedError("User ID validation logic needed")
```

### Error Composition and Chaining

**Chain operations that can fail using Result objects:**

```python
def process_user_safely(user_id: int) -> Result:
    """
    Complete user processing with functional error handling.
    
    Uses @validation.checker::validate_user_id,
    @database.loader::load_user_data, and
    @processing.transformer::transform_user
    """
    raise NotImplementedError("Safe user processing pipeline needed")

def enrich_user_with_fallback(user: User) -> Result:
    """
    Enrich user data with graceful fallback on errors.
    
    Uses @enrichment.primary::enrich_user and
    @enrichment.fallback::basic_enrichment for graceful degradation.
    """
    raise NotImplementedError("User enrichment with fallback needed")
```

### The ONLY Exception: NotImplementedError

**NotImplementedError is reserved exclusively for Jitter:**

```python
def calculate_complex_formula(data: ComplexData) -> Result:
    """
    Perform complex calculations.
    
    This function should NEVER raise exceptions for business logic errors.
    Uses @calculator.engine::compute for the actual calculation.
    """
    # The ONLY exception allowed
    raise NotImplementedError("Complex calculation implementation needed")

def safe_divide(a: float, b: float) -> Result:
    """
    Safely divide two numbers using functional error handling.
    
    Returns Result with either the division result or error information.
    No exceptions are raised for division by zero or invalid inputs.
    """
    raise NotImplementedError("Safe division with result-based error handling needed")
```

### Pattern: Optional Values for Missing Data

**Use Optional types instead of exceptions for missing data:**

```python
def find_user_by_email(email: str) -> User | None:
    """
    Find user by email address.
    
    Returns User if found, None if not found.
    Uses @database.query::user_by_email for lookup.
    """
    raise NotImplementedError("User lookup by email needed")

def get_user_preference(user: User, preference_key: str) -> str | None:
    """
    Get user preference value.
    
    Returns preference value if exists, None otherwise.
    Uses @preferences.store::get_preference for lookup.
    """
    raise NotImplementedError("User preference lookup needed")
```

### Why This Approach Works Better with Jitter

**Functional error handling enables:**

1. **Predictable function signatures** - No hidden exceptions to catch
2. **Composable error handling** - Chain operations safely
3. **Hot-reload safety** - No exception propagation state to synchronize
4. **Clear data flow** - Errors are explicit values, not control flow
5. **LLM-friendly patterns** - Simple, consistent error handling for generation

## Critical Import Requirements for Hot-Reloading

> **🚨 EXTREMELY IMPORTANT: Jitter can only hot-reload MODULES, not individual function/class references. You MUST import modules, NEVER direct imports of names within modules.**

### The Hot-Reload Constraint

When Jitter modifies a function in a source file and hot-reloads the module, it can only update the module object itself. Any direct references to functions or classes that were imported before the reload will still point to the old implementations.

### ✅ CORRECT: Module Imports Only

**Always import the module itself, then access members through dot notation:**

```python
# CORRECT: Import modules (for ./calculator/operations.py)
from calculator import operations
from database import users  
from validation import checker

def process_calculation(a: float, b: float) -> Result:
    """
    Process calculation using module imports for hot-reload compatibility.
    
    Uses @calculator.operations::add for the calculation.
    """
    # CORRECT: Access function through imported module
    result = operations.add(a, b)
    return Result(success=True, data=result)

def validate_and_load_user(user_id: int) -> Result:
    """
    Validate and load user with hot-reload safe imports.
    
    Uses @validation.checker::validate_user_id and
    @database.users::load_user_by_id
    """
    # CORRECT: All function calls through module references
    validation_result = checker.validate_user_id(user_id)
    if not validation_result.success:
        return validation_result
    
    return users.load_user_by_id(user_id)
```

### ❌ WRONG: Direct Name Imports

**NEVER import functions or classes directly - this breaks hot-reloading:**

```python
# WRONG: Direct function/class imports
from calculator.operations import add, multiply, divide
from database.users import load_user_by_id, save_user
from validation.checker import validate_user_id

def process_calculation(a: float, b: float) -> Result:
    """
    This will NOT work with Jitter hot-reloading!
    """
    # WRONG: Direct reference won't update after hot-reload
    result = add(a, b)  # This 'add' points to the old implementation!
    return Result(success=True, data=result)
```

### Why This Matters

**When Jitter hot-reloads a module:**

1. ✅ **Module imports work**: `operations.add` gets the NEW implementation
2. ❌ **Direct imports fail**: `add` (imported directly) still points to the OLD implementation

**Example of the problem:**

```python
# Initial state  
from calculator.operations import add  # 'add' binds to old implementation

def calculate(a, b):
    return add(a, b)  # Uses old implementation forever!

# After Jitter modifies calculator/operations.py:
# - The operations module gets reloaded ✅
# - But 'add' variable still points to old function ❌
# - calculate() never sees the new implementation! 💥
```

### Real-World Example from Calculator

**Correct pattern used in Jitter's calculator example:**

```python
# In test.py - CORRECT
from calculator import operations
from calculator import tokenizer
from calculator import interpreter

def test():
    """
    Test implementation that works with hot-reloading.
    
    Uses @calculator.operations::add, @calculator.tokenizer::tokenize,
    and @calculator.interpreter::interpret
    """
    # All calls through module references - hot-reload safe!
    result1 = operations.add(5, 3)
    tokens = tokenizer.tokenize("1 + 2") 
    result2 = interpreter.interpret(tokens)
    
    raise NotImplementedError("Test logic implementation needed")
```

### Import Pattern Rules

**For a file located at `./foo/bar/baz.py`:**

- ✅ **CORRECT**: `from foo.bar import baz`
- ❌ **WRONG**: `from foo.bar.baz import function_name`
- ❌ **WRONG**: `import foo.bar.baz`

**Then use as**: `baz.function_name()`, `baz.ClassName()`, etc.

### Summary: The Module Import Rule

**For Jitter to work correctly:**

1. **ALWAYS** `from package.subpackage import module`
2. **NEVER** `from package.subpackage.module import function`  
3. **Access functions** via `module.function()`
4. **Remember**: Jitter reloads modules, not individual name bindings

This constraint is fundamental to how Python's import system and hot-reloading work together.

## Module Organization

### Functional Module Structure

Organize modules by **function** rather than by **type**:

```
src/
├── user/
│   ├── __init__.py
│   ├── operations.py      # User-related pure functions
│   ├── types.py          # User-related data structures
│   └── validation.py     # User validation functions
├── order/
│   ├── __init__.py
│   ├── processing.py     # Order processing functions
│   ├── types.py         # Order data structures
│   └── calculations.py  # Order calculation functions
└── integration/
    ├── __init__.py
    ├── api.py           # External API functions
    └── database.py      # Database interaction functions
```

### Clear API Boundaries

**Define explicit public APIs:**

```python
# user/__init__.py
from .operations import create_user, update_user, delete_user
from .types import User, UserPreference, UserProfile
from .validation import validate_user_email, validate_user_age

__all__ = [
    # Operations
    "create_user", "update_user", "delete_user",
    # Types  
    "User", "UserPreference", "UserProfile",
    # Validation
    "validate_user_email", "validate_user_age"
]
```

### Import Patterns

**Use module imports only for hot-reload compatibility:**

```python
# CORRECT: Module imports only
from user import operations
from user import types  
from order import processing
from integration import database

# Then use as:
# operations.create_user()
# types.User()
# processing.process_order()
# database.save_to_database()

# WRONG: Direct name imports (breaks hot-reload)
from user.operations import create_user, update_user
from user.types import User, UserProfile
from order.processing import process_order

# WRONG: Star imports
from user import *
from order import *
```

## The Incremental Development Workflow

### Step 1: Sketch Your Program Structure

Start with high-level orchestration:

```python
# foo.py
def main():
    """Main application entry point."""
    user_input = get_user_input()
    processed_data = process_input(user_input)
    result = execute_business_logic(processed_data)
    display_results(result)

def get_user_input() -> UserInput:
    """Get and validate user input."""
    raise NotImplementedError("Input collection logic needed")

def process_input(raw_input: UserInput) -> ProcessedInput:
    """Process and validate user input."""
    raise NotImplementedError("Input processing logic needed")

def execute_business_logic(data: ProcessedInput) -> BusinessResult:
    """Core business logic execution."""
    raise NotImplementedError("Business logic needed")

def display_results(result: BusinessResult) -> None:
    """Display results to user.""" 
    raise NotImplementedError("Display logic needed")

```

# In it's own file separate from any other code (this is currently to avoid a limitation in the Jitter implementation that causes hot reloading not to work as expected in the same module that entered the Jitter handler).
```python
from jitter import Jitter
from foo import main

if __name__ == "__main__":
    with Jitter():
        main()
```

### Step 2: Add Data Structures

Define your data contracts:

```python
@dataclass(frozen=True)
class UserInput:
    command: str
    parameters: dict[str, str]
    timestamp: float

@dataclass(frozen=True)
class ProcessedInput:
    validated_command: str
    parsed_parameters: dict[str, any]
    user_context: UserContext

@dataclass(frozen=True)
class BusinessResult:
    success: bool
    data: dict[str, any] | None = None
    message: str | None = None
```

### Step 3: Add @-References for Context

Provide guidance for LLM implementation:

```python
def process_input(raw_input: UserInput) -> ProcessedInput:
    """
    Process and validate user input.
    
    Uses @validation.input::validate_command and 
    @parsing.parameters::parse_parameters for processing.
    Also references @user.context::get_user_context
    """
    raise NotImplementedError("Input processing logic needed")
```

### Step 4: Run and Implement Incrementally

1. **Run your program** within `Jitter()`
2. **First NotImplementedError** is caught - Jitter shows you the call context
3. **Choose implementation**: AI-generated or manual
4. **Review and approve** the generated implementation
5. **Code is hot-swapped** and execution continues
6. **Repeat** until all functions are implemented

### Step 5: Refine and Iterate

Since you can re-trigger `NotImplementedError` in any function, you can:

- Refine implementations based on actual usage
- Add features incrementally  
- Optimize performance based on real profiling data

## Complete Example: Calculator Implementation

Here's how the calculator example demonstrates all these principles:

### Data Structures (All Frozen)

```python
# tokenizer.py - Token types as frozen dataclasses
@dataclass(frozen=True)
class Integer:
    val: int

@dataclass(frozen=True)
class Float:
    val: float

@dataclass(frozen=True)
class PlusOp:
    pass

@dataclass(frozen=True)
class MinusOp:
    pass
```

### Function Signatures with @-References

```python
def tokenize(input_string: str) -> list[LPar | RPar | Integer | Float | PlusOp | MinusOp | MulOp | DivOp | PowOp]:
    """
    Tokenizes an input arithmetic expression string.
    Makes use of all the dataclasses in @calculator.tokenizer
    """
    raise NotImplementedError("Tokenization not yet implemented")

def interpret(program_tokens: list[tokenizer.LPar | tokenizer.RPar | tokenizer.Integer | tokenizer.Float | tokenizer.PlusOp | tokenizer.MinusOp | tokenizer.MulOp | tokenizer.DivOp | tokenizer.PowOp]) -> float:
    """
    Interprets a list of tokens representing an arithmetic expression.
    
    The implementation will use the functions in @calculator.operations to implement this logic.
    """
    raise NotImplementedError("Interpretation logic not yet implemented")
```

### Pure Operations Functions

```python
def add(a, b):
    """Add numbers together.
    
    Args:
        a (float): The first number
        b (float): The second number
    
    Returns:
        float: The sum of a and b
    """
    raise NotImplementedError("Addition operation not yet implemented")

def divide(a, b):
    """Divide the first number by the second number.
    
    Args:
        a (float): The dividend
        b (float): The divisor
    
    Returns:
        float: The result of a / b
    
    Raises:
        ZeroDivisionError: If b is zero
    """
    raise NotImplementedError("Division operation not yet implemented")
```

### Integration and Testing

```python
def test():
    """
    Test the calculator functionality end-to-end.
    
    For the implementation, we'll first make the formula a string, and then parse it using
    @calculator.tokenizer::tokenize and then @calculator.interpreter to interpret the evaluation of the tokens.
    """
    raise NotImplementedError("Test implementation needed")

if __name__ == "__main__":
    with Jitter():
        test()
```

## Anti-Patterns to Avoid

### ❌ Mutable Global State

```python
# BAD: Global mutable state
current_user = None
application_config = {}

def process_request():
    global current_user, application_config
    # This breaks hot reloading and makes functions unpredictable
```

### ❌ Complex Class Hierarchies

```python
# BAD: Complex inheritance
class AbstractProcessor:
    def process(self):
        raise NotImplementedError
        
class AdvancedProcessor(AbstractProcessor):
    def __init__(self, config):
        self.config = config
        self.state = {}
    
    def process(self):
        # Complex stateful processing
```

### ❌ Side Effects in Business Logic

```python
# BAD: Hidden I/O and side effects
def calculate_user_score(user_id: int) -> float:
    # Hidden database call
    user_data = database.get_user(user_id)
    # Hidden file write
    log.write(f"Calculating score for {user_id}")
    return complex_calculation(user_data)
```

### ❌ Exception-Heavy Control Flow

```python
# BAD: Using exceptions for control flow
def find_user(user_id: int) -> User:
    try:
        return database.get_user(user_id)
    except UserNotFound:
        try:
            return cache.get_user(user_id)
        except UserNotFound:
            return create_default_user(user_id)
```

### ❌ Mutable Data Structures

```python
# BAD: Mutable data classes
@dataclass
class User:
    name: str
    preferences: list[str]  # This can be modified!
    
    def add_preference(self, pref: str):
        self.preferences.append(pref)  # Mutation!
```

## Advanced Patterns

### Pattern 1: Functional Pipeline Processing

```python
def process_data_pipeline(input_data: RawData) -> ProcessedData:
    """
    Process data through a functional pipeline.
    
    Pipeline stages:
    1. Validation with @validation.checker::validate_raw_data
    2. Normalization with @transform.normalizer::normalize_data  
    3. Enrichment with @enrichment.service::enrich_data
    4. Final processing with @processing.finalizer::finalize_data

    Each stage is a pure function that can be implemented independently
    """
    raise NotImplementedError("Functional pipeline implementation needed")
```

### Pattern 2: Context Objects for Complex Operations

```python
@dataclass(frozen=True)
class ProcessingContext:
    """Context object for complex processing operations."""
    user_id: int
    session_id: str
    preferences: UserPreferences
    environment: str

def complex_operation(
    data: InputData, 
    context: ProcessingContext
) -> OperationResult:
    """
    Complex operation with rich context.
    
    Uses @processor.validator::validate_with_context and
    @processor.executor::execute_with_context
    """
    raise NotImplementedError("Complex operation implementation needed")
```

### Pattern 3: Result Objects for Error Handling

```python
@dataclass(frozen=True)
class OperationResult:
    """Result object that encapsulates success/failure."""
    success: bool
    data: any | None = None
    error_code: str | None = None
    error_message: str | None = None

def safe_operation(input_data: InputData) -> OperationResult:
    """
    Operation that returns results instead of raising exceptions.
    
    Uses @validation.checker::check_input and
    @processing.executor::execute_operation
    """
    raise NotImplementedError("Safe operation implementation needed")
```

### Pattern 4: Partial Implementation with Conditional NotImplementedError

**The ONLY exception to the "NotImplementedError only" rule is when you implement partial functionality:**

```python
def advanced_calculation(data: ComplexData, mode: str) -> Result:
    """
    Advanced calculation with multiple modes using functional error handling.
    
    Supports basic mode initially, with @advanced.processor::complex_mode
    and @advanced.processor::expert_mode for advanced functionality.
    """
    if mode == "basic":
        # Basic mode is fully implemented - returns success Result
        return Result(
            success=True, 
            data=CalculationResult(
                value=data.simple_value * 2,
                mode="basic",
                complexity="low"
            )
        )
    elif mode == "advanced":
        raise NotImplementedError("Advanced mode calculation needed")
    elif mode == "expert":
        raise NotImplementedError("Expert mode calculation needed")
    else:
        # Return error Result instead of raising exception
        return Result(
            success=False,
            error_code="INVALID_MODE",
            error_message=f"Unknown mode: {mode}"
        )

def load_data_source(source_type: str, config: dict) -> Result:
    """
    Load data from various sources using functional error handling.
    
    Currently supports file loading, with @database.connector::connect
    and @api.client::fetch for other sources.
    """
    if source_type == "file":
        # File loading is implemented - returns success or error Result
        filename = config.get("filename")
        if not filename:
            return Result(
                success=False,
                error_code="MISSING_FILENAME",
                error_message="Filename required for file source"
            )
        
        return Result(
            success=True,
            data=FileDataSource(filename)
        )
    elif source_type == "database":
        raise NotImplementedError("Database source loading needed")
    elif source_type == "api":
        raise NotImplementedError("API source loading needed")
    else:
        return Result(
            success=False,
            error_code="UNSUPPORTED_SOURCE",
            error_message=f"Unsupported source type: {source_type}"
        )
```

**This pattern is powerful because:**
- You can ship working functionality immediately (basic mode)
- Advanced features are implemented incrementally as needed
- Each unimplemented path gets full context when triggered
- The working parts provide examples for implementing the missing parts

---

## Summary: The Jitter Way

Jitter enables a revolutionary approach to software development through:

1. **Functional-First Architecture**: Immutable data, pure functions, explicit dependencies
2. **@-Reference Context System**: Rich context for LLM-assisted implementation
3. **Incremental Implementation**: Implement exactly what you need, when you need it
4. **Hot-Reload Capabilities**: Code changes take effect immediately without restart
5. **Context-Driven Development**: Let your program tell you what it needs

By following these patterns, you create programs that are:
- **Predictable**: Easy to understand and modify
- **Composable**: Functions can be combined and recombined easily
- **Hot-Reload Safe**: No state synchronization issues
- **LLM-Friendly**: Clear contracts and context for code generation
- **Incrementally Developable**: Build complexity gradually with confidence

**Remember**: Jitter is not just a tool—it's a fundamentally different way of thinking about software development. Embrace the functional patterns, master the @-reference system, and let your programs guide their own implementation.