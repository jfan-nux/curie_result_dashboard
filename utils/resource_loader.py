"""
Resource loader utility for accessing package data files.
Handles both installed package and development modes.
"""

import os
import sys
from pathlib import Path
from typing import Optional, Union

def get_package_resource(resource_path: str, package: str = "nux_slack_bot") -> str:
    """
    Get the contents of a package resource file.
    
    Args:
        resource_path: Path to the resource (e.g., "data_models/manual_experiments.yaml")
        package: Package name (default: "nux_slack_bot")
    
    Returns:
        str: Contents of the resource file
    
    Raises:
        FileNotFoundError: If the resource cannot be found
    """
    
    # Method 1: Try importlib.resources (Python 3.9+)
    try:
        from importlib.resources import files
        
        # Split the resource path to get the subpackage and filename
        parts = resource_path.split('/')
        if len(parts) == 2:
            subpackage, filename = parts
            package_files = files(f"{package}.{subpackage}")
            resource_file = package_files / filename
            return resource_file.read_text(encoding='utf-8')
        else:
            # Handle nested paths
            subpackages = '/'.join(parts[:-1])
            filename = parts[-1]
            package_files = files(f"{package}.{subpackages.replace('/', '.')}")
            resource_file = package_files / filename
            return resource_file.read_text(encoding='utf-8')
            
    except (ImportError, FileNotFoundError, AttributeError, ModuleNotFoundError):
        pass
    
    # Method 2: Try importlib_resources (Python 3.8 fallback)
    try:
        from importlib_resources import files
        
        parts = resource_path.split('/')
        if len(parts) == 2:
            subpackage, filename = parts
            package_files = files(f"{package}.{subpackage}")
            resource_file = package_files / filename
            return resource_file.read_text(encoding='utf-8')
        else:
            subpackages = '/'.join(parts[:-1])
            filename = parts[-1]
            package_files = files(f"{package}.{subpackages.replace('/', '.')}")
            resource_file = package_files / filename
            return resource_file.read_text(encoding='utf-8')
            
    except (ImportError, FileNotFoundError, AttributeError, ModuleNotFoundError):
        pass
    
    # Method 3: Try pkg_resources
    try:
        import pkg_resources
        return pkg_resources.resource_string(package, resource_path).decode('utf-8')
    except (ImportError, FileNotFoundError, AttributeError):
        pass
    
    # Method 4: Try pkgutil.get_data
    try:
        import pkgutil
        data = pkgutil.get_data(package, resource_path)
        if data:
            return data.decode('utf-8')
    except (ImportError, FileNotFoundError, AttributeError):
        pass
    
    # Method 5: Development mode - find relative to this file
    try:
        # Get the package root directory
        current_file = Path(__file__)
        package_root = current_file.parent.parent  # Go up from utils/ to package root
        resource_file = package_root / resource_path
        
        if resource_file.exists():
            return resource_file.read_text(encoding='utf-8')
    except (FileNotFoundError, AttributeError):
        pass
    
    # Method 6: Try relative to current working directory
    try:
        resource_file = Path(resource_path)
        if resource_file.exists():
            return resource_file.read_text(encoding='utf-8')
    except (FileNotFoundError, AttributeError):
        pass
    
    # Method 7: Try to find the package installation directory
    try:
        import nux_slack_bot
        package_dir = Path(nux_slack_bot.__file__).parent
        resource_file = package_dir / resource_path
        
        if resource_file.exists():
            return resource_file.read_text(encoding='utf-8')
    except (ImportError, FileNotFoundError, AttributeError):
        pass
    
    # If all methods fail, raise an error with debugging info
    error_msg = f"""
    Could not find resource: {resource_path}
    
    Debugging information:
    - Package: {package}
    - Python version: {sys.version}
    - Current working directory: {os.getcwd()}
    - __file__: {__file__ if '__file__' in globals() else 'Not available'}
    
    Tried multiple methods:
    1. importlib.resources (Python 3.9+)
    2. importlib_resources (Python 3.8 fallback)
    3. pkg_resources
    4. pkgutil.get_data
    5. Development mode relative path
    6. Current working directory
    7. Package installation directory
    
    Please ensure the resource file exists and is included in the package.
    """
    
    raise FileNotFoundError(error_msg.strip())


def get_package_resource_path(resource_path: str, package: str = "nux_slack_bot") -> Optional[Path]:
    """
    Get the Path object for a package resource file (for cases where you need the actual file path).
    
    Args:
        resource_path: Path to the resource (e.g., "data_models/manual_experiments.yaml")
        package: Package name (default: "nux_slack_bot")
    
    Returns:
        Optional[Path]: Path to the resource file, or None if not found
    """
    
    # Method 1: Development mode - find relative to this file
    try:
        current_file = Path(__file__)
        package_root = current_file.parent.parent  # Go up from utils/ to package root
        resource_file = package_root / resource_path
        
        if resource_file.exists():
            return resource_file
    except (FileNotFoundError, AttributeError):
        pass
    
    # Method 2: Try relative to current working directory
    try:
        resource_file = Path(resource_path)
        if resource_file.exists():
            return resource_file
    except (FileNotFoundError, AttributeError):
        pass
    
    # Method 3: Try to find the package installation directory
    try:
        import nux_slack_bot
        package_dir = Path(nux_slack_bot.__file__).parent
        resource_file = package_dir / resource_path
        
        if resource_file.exists():
            return resource_file
    except (ImportError, FileNotFoundError, AttributeError):
        pass
    
    return None
