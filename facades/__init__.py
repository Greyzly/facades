import pkgutil
import importlib
from pathlib import Path

# Automatically import all public functions/classes from all .py files in this folder
__all__ = []
package_dir = Path(__file__).resolve().parent

for _, module_name, _ in pkgutil.iter_modules([str(package_dir)]):
    # Import the module dynamically
    module = importlib.import_module(f"{__name__}.{module_name}")
    
    # Get all public attributes (functions, classes, variables)
    for attribute_name in dir(module):
        # Ignore dunder methods and private functions (starting with _)
        if not attribute_name.startswith('_'):
            # Bring the function into the top-level namespace
            globals()[attribute_name] = getattr(module, attribute_name)
            __all__.append(attribute_name)