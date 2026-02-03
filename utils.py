# utils.py
from typing import Dict, Any, List, Union, Tuple
import os
import platform
from pathlib import Path
import ctypes
import time
import ru_local as ru

PathString = Union[str, Path]

def is_windows_os() -> bool:
    """
    Check if the program is running on Windows operating system.
    Returns:
        bool: True if running on Windows, False otherwise
    """
    operating_system = platform.system()
    
    if operating_system == "Windows":
        return True
    return False


def validate_windows_path(path: PathString) -> Tuple[bool, str]:
    """
    Windows path validation (syntax, not existence)
    Args:
        path: The way to check
    Returns:
        (validity, error reporting)
    """
    if not is_windows_os():
        return False, ru.ONLY_WINDOWS
    
    path_str = str(path)
    
    if ':' in path_str:
        if path_str.count(':') > 1:
            return False, ru.TOO_MANY_COLONS

        colon_index = path_str.find(':')
        if colon_index != 1:
            return False, ru.COLON_POSITION

        if not path_str[0].isalpha():
            return False, ru.INVALID_DRIVE
        
        if len(path_str) > 2 and path_str[2] != '\\':
            return False, ru.MISSING_BACKSLASH
 
    forbidden_chars = ['/', '*', '?', '"', '<', '>', '|']
    for char in forbidden_chars:
        if char in path_str:
            return False, ru.FORBIDDEN_CHAR.format(char=char)

    if len(path_str) > 260:
        return False, ru.PATH_TOO_LONG
    
    return True, ""


def format_size(size_bytes: int) -> str:
    """
    Format file size in bytes to human-readable string using Windows units.
    Args:
        size_bytes (int): File size in bytes
    Returns:
        str: Formatted size string with appropriate unit (B, KB, MB, GB, TB)    
    """
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024**2:
        return f"{size_bytes / 1024:.1f} KB"
    elif size_bytes < 1024**3:
        return f"{size_bytes / (1024**2):.1f} MB"
    elif size_bytes < 1024**4:
        return f"{size_bytes / (1024**3):.1f} GB"
    else:
        return f"{size_bytes / (1024**4):.1f} TB"
    

def get_parent_path(path: PathString) -> str:
    """
    Get the parent directory of a given Windows path.
    Args:
        path (PathString): The file or directory path
    Returns:
        str: Parent directory path. Returns original path if it's a root directory.
    """
    path_str = str(path)
    parent = os.path.dirname(path_str)

    if parent == path_str:
        return path_str
    return parent


def safe_windows_listdir(path: PathString) -> List[str]:
    """
    Safely get directory contents in Windows, handling permission errors.
    Args:
        path (PathString): Directory path to list
    Returns:
        List[str]: List of directory entries (files and folders)
                  Returns empty list on error (permission denied, not found, etc.)
    """
    try:
        return os.listdir(str(path))
    except (PermissionError, FileNotFoundError, OSError):
        return []    


def is_hidden_windows_file(path: PathString) -> bool:
    """
    Check if a file or directory is hidden in Windows.
    Args:
        path (PathString): Path to file or directory
    Returns:
        bool: True if file has hidden attribute, False otherwise or on error
    """
    try:
        file_info = os.stat(path)
        if hasattr(file_info, 'st_file_attributes'):
            marks = file_info.st_file_attributes
            return bool(marks & 2)
        
        attributes = ctypes.windll.kernel32.GetFileAttributesW(str(path))
        return attributes != -1 and (attributes & 2)
        
    except Exception:
        return False
    

def validate_windows_path_recursive(path: PathString, depth: int = 0) -> Tuple[bool, List[str]]:
    """
    Recursively validate a Windows path and all parent directories.
    Args:
        path (PathString): Path to validate (string or Path object)
        depth (int): Current recursion depth (internal use, default: 0)
    Returns:
        Tuple[bool, List[str]]: 
            - True if all path levels are valid, False otherwise
            - List of error messages for invalid segments (empty if valid)
    """
    MAX_RECURSION_DEPTH = 100
    
    if not is_windows_os():
        return False, [ru.FUNCTION_WINDOWS_ONLY]
    
    if depth > MAX_RECURSION_DEPTH:
        return False, [ru.MAX_RECURSION_DEPTH]
    
    path_str = str(path)
    problems = []
    
    is_valid, error_msg = validate_windows_path(path_str)
    
    if not is_valid:
        problems.append(f"{path_str}: {error_msg}")

    parent = get_parent_path(path_str)
    if parent != path_str and parent:
        parent_valid, parent_problems = validate_windows_path_recursive(parent, depth + 1)
        
        if not parent_valid:
            problems.extend(parent_problems)
    
    overall_valid = len(problems) == 0
    
    return overall_valid, problems


def collect_windows_metadata_recursive(path: PathString, max_depth: int = 10, 
                                       current_depth: int = 0) -> Dict[str, Any]:
    """
    Recursively collect metadata from Windows file system hierarchy.
    Args:
        path (PathString): Starting directory path
        max_depth (int): Maximum recursion depth (default: 10)
        current_depth (int): Current recursion level (internal use)
    Returns:
        Dict[str, Any]: Hierarchical metadata with file stats, 
                       children list, and performance metrics
    """
    start_time = time.time()
    
    if current_depth > max_depth:
        return {}
    
    path_str = str(path)
    metadata = {
        "path": path_str,
        "name": os.path.basename(path_str) if os.path.basename(path_str) else path_str,
        "type": "directory" if os.path.isdir(path_str) else "file",
        "level": current_depth,
        "hidden": is_hidden_windows_file(path_str),
        "size": os.path.getsize(path_str) if os.path.isfile(path_str) else 0,
        "children": [],
        "file_stats": {
            "total": 0,
            "hidden": 0,
            "by_extension": {}
        }
    }
    
    if os.path.isdir(path_str) and current_depth < max_depth:
        try:
            for item in safe_windows_listdir(path_str):
                item_path = os.path.join(path_str, item)
                
                child_metadata = collect_windows_metadata_recursive(
                    item_path, max_depth, current_depth + 1
                )
                
                if child_metadata:
                    metadata["children"].append(child_metadata)
                    
                    if child_metadata["type"] == "file":
                        metadata["file_stats"]["total"] += 1
                        
                        if child_metadata["hidden"]:
                            metadata["file_stats"]["hidden"] += 1
                        
                        _, ext = os.path.splitext(item)
                        ext = ext.lower() if ext else "no_extension"
                        metadata["file_stats"]["by_extension"][ext] = \
                            metadata["file_stats"]["by_extension"].get(ext, 0) + 1
                            
        except (PermissionError, OSError):
            pass

    execution_time = time.time() - start_time
    metadata["execution_time_ms"] = execution_time * 1000
    metadata["recursion_depth"] = current_depth
    
    return metadata


def resolve_long_paths_recursive(path: PathString, prefix: str = "\\\\?\\") -> str:
    """
    Recursively convert Windows paths exceeding 260-character limit.
    Args:
        path (PathString): Path to process
        prefix (str): Long path prefix (default: "\\\\?\\")
    Returns:
        str: Processed path with prefix if length > 260 chars,
             otherwise original path unchanged
    """
    path_str = str(path)
    
    if len(path_str) > 260:
        if path_str.startswith("\\\\"):
            if not path_str.startswith("\\\\?\\UNC\\"):
                return "\\\\?\\UNC\\" + path_str[2:]
        elif not path_str.startswith("\\\\?\\"):
            return prefix + path_str
        else:
            return path_str
    
    parent = get_parent_path(path_str)
    
    if not parent or parent == path_str:
        return path_str
    
    resolved_parent = resolve_long_paths_recursive(parent, prefix)
    
    if resolved_parent != parent:
        current_name = os.path.basename(path_str)
        return os.path.join(resolved_parent, current_name)
    
    return path_str