import importlib
import sys
from types import ModuleType


def hot_reload(module_name: str | ModuleType) -> ModuleType:
    """
    Hot reload a module while preserving its state.

    Automatically captures all non-function/non-class/non-module attributes
    before reloading and restores them after reloading.

    Args:
        module_name: Name of the module to reload OR the module object itself

    Returns:
        The reloaded module

    Example:
        import my_module
        # ... my_module.some_var gets modified during runtime ...
        hot_reload('my_module')  # or hot_reload(my_module)
    """
    if isinstance(module_name, ModuleType):
        module = module_name
        module_name = module.__name__
    else:
        if module_name not in sys.modules:
            raise ValueError(f"Module '{module_name}' not found in sys.modules")
        module = sys.modules[module_name]

    # Reload the module
    reloaded_module = importlib.reload(module)

    return reloaded_module
