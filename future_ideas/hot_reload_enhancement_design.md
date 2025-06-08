# Hot Reload Enhancement Design

## Problem Statement

The current hot reloading capability in PLJam has a limitation: it doesn't work properly when functions are imported using the `from module import function` syntax. The hot reload successfully updates the function in its original module, but other modules that have directly imported the function still hold references to the old implementation.

### Current Behavior
- ✅ Works: `import test_not_impl; test_not_impl.sample_function()`
- ❌ Fails: `from test_not_impl import sample_function; sample_function()`

## Root Cause

When using `from module import function`, Python creates a direct reference to the function object in the importing module's namespace. When `importlib.reload()` updates the source module, it doesn't update these cross-module references.

## Proposed Solution

Enhance the hot reload mechanism with static analysis to find and update all cross-module function references.

## Implementation Strategy

### Phase 1: AST-Based Import Scanner

Create a static analysis system using Python's built-in `ast` module to identify all direct function imports across the codebase.

```python
import ast
from pathlib import Path

class ImportAnalyzer(ast.NodeVisitor):
    def __init__(self, target_function, target_module):
        self.target_function = target_function
        self.target_module = target_module
        self.import_locations = []
        
    def visit_ImportFrom(self, node):
        if node.module == self.target_module:
            for alias in node.names:
                if alias.name == self.target_function:
                    self.import_locations.append({
                        'line': node.lineno,
                        'imported_as': alias.asname or alias.name,
                        'level': node.level  # For relative imports
                    })
        self.generic_visit(node)

def find_direct_imports(target_function, target_module):
    """Find all files that directly import a specific function."""
    results = []
    
    for py_file in Path('.').rglob('*.py'):
        try:
            with open(py_file, 'r') as f:
                source = f.read()
            tree = ast.parse(source)
            
            analyzer = ImportAnalyzer(target_function, target_module)
            analyzer.visit(tree)
            
            if analyzer.import_locations:
                results.append({
                    'file': py_file,
                    'imports': analyzer.import_locations
                })
                
        except Exception as e:
            print(f"Warning: Could not analyze {py_file}: {e}")
            continue
    
    return results
```

### Phase 2: Enhanced Hot Reload System

Modify the existing `hot_reload()` function to include cross-reference updates:

```python
def enhanced_hot_reload(module_name: str | ModuleType, updated_function_name: str = None) -> ModuleType:
    """
    Enhanced hot reload that updates cross-module references.
    
    Args:
        module_name: Module to reload
        updated_function_name: Specific function that was updated (optional)
    """
    if isinstance(module_name, ModuleType):
        module = module_name
        module_name = module.__name__
    else:
        module = sys.modules[module_name]
    
    # Step 1: Standard module reload
    reloaded_module = importlib.reload(module)
    
    # Step 2: Update cross-module references (if function specified)
    if updated_function_name:
        _update_cross_module_references(module_name, updated_function_name, reloaded_module)
    
    return reloaded_module

def _update_cross_module_references(source_module_name: str, function_name: str, reloaded_module: ModuleType):
    """Update all modules that directly imported the specified function."""
    
    # Find all files that import this function
    import_locations = find_direct_imports(function_name, source_module_name)
    
    # Get the updated function from the reloaded module
    updated_function = getattr(reloaded_module, function_name)
    
    for location in import_locations:
        file_path = location['file']
        module_name = _file_path_to_module_name(file_path)
        
        if module_name in sys.modules:
            target_module = sys.modules[module_name]
            
            # Update each import in the target module
            for import_info in location['imports']:
                imported_as = import_info['imported_as']
                
                # Update the reference in the target module's namespace
                setattr(target_module, imported_as, updated_function)
                print(f"Updated {imported_as} in {module_name}")

def _file_path_to_module_name(file_path: Path) -> str:
    """Convert file path to Python module name."""
    # Remove .py extension and convert path separators to dots
    relative_path = file_path.relative_to(Path.cwd())
    module_path = str(relative_path.with_suffix(''))
    return module_path.replace('/', '.').replace('\\', '.')
```

### Phase 3: Integration with Existing System

Update `with_replay.py` to use the enhanced hot reload:

```python
# In with_replay.py, line 239-243:
# Replace:
hot_reload(func_module)

# With:
enhanced_hot_reload(func_module, failing_func.__name__)
```


## Implementation Plan

### Phase 1: Basic AST Implementation
1. Create `import_analyzer.py` with AST-based scanning
2. Add basic cross-reference updating to `hot_reload.py`
3. Test with existing `test_handler.py` scenario

### Phase 2: Robustness Improvements
1. Handle edge cases (relative imports, aliased imports, nested modules)
2. Add error handling and fallback mechanisms
3. Performance optimization for large codebases

### Phase 3: Advanced Features (Optional)
1. Support for class methods and complex import patterns
2. Caching of import analysis results
3. Performance optimization for large codebases

## Benefits

1. **Seamless Hot Reloading**: Works with both `import module` and `from module import function` patterns
2. **No Code Changes Required**: Existing code using direct imports will work automatically
3. **Built-in Dependencies**: Uses only Python standard library
4. **Maintainable**: Simple, focused solution without external dependencies

## Considerations

1. **Performance**: AST scanning adds overhead, but can be cached
2. **Edge Cases**: Complex import patterns may need special handling
3. **File System Changes**: New files created during execution won't be tracked until restart
4. **Module Reloading Limitations**: Some modules (C extensions, certain built-ins) cannot be reloaded

## Testing Strategy

1. Create test cases for various import patterns:
   - `from module import function`
   - `from module import function as alias`
   - `from package.module import function`
   - Relative imports: `from .module import function`

2. Verify cross-module reference updates work correctly

## Future Enhancements

1. **Hot Reloading for Classes**: Extend the same principles to class definitions and methods