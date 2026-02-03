# navigation.py
import os
from datetime import datetime
from typing import List, Dict, Any, Tuple, Generator, Optional
import utils
import ru_local as ru


def get_current_drive() -> str:
    """
    Get current Windows drive.
    """
    current_path = os.getcwd()
    drive, _ = os.path.splitdrive(current_path)
    return drive


def list_available_drives() -> List[str]:
    """
    Get list of available Windows drives.

    Returns:
        List[str]: List of available drives (['C:', 'D:', ...])
    """
    drives = []
    for letter in range(ord('A'), ord('Z') + 1):
        drive_letter = chr(letter) + ":"
        if os.path.exists(drive_letter + "\\"):
            drives.append(drive_letter)
    return drives


def list_directory(path: str) -> Tuple[bool, List[Dict[str, Any]]]:
    """
    Display directory contents in Windows.

    Args:
        path (str): Directory path

    Returns:
        Tuple[bool, List[Dict[str, Any]]]:
            - First element: True on success, False on error
            - Second element: List of dictionaries with file/folder info
    """
    is_valid, error_msg = utils.validate_windows_path(path)
    if not is_valid:
        return False, []

    items = utils.safe_windows_listdir(path)
    result = []

    for item_name in items:
        item_path = os.path.join(path, item_name)

        try:
            stat_info = os.stat(item_path)
            is_file = os.path.isfile(item_path)

            modified_timestamp = stat_info.st_mtime
            modified_date = datetime.fromtimestamp(modified_timestamp)
            modified_str = modified_date.strftime("%Y-%m-%d")

            item_info = {
                'name': item_name,
                'type': 'file' if is_file else 'folder',
                'size': stat_info.st_size if is_file else 0,
                'modified': modified_str,
                'hidden': utils.is_hidden_windows_file(item_path)
            }

            result.append(item_info)

        except (PermissionError, OSError):
            continue

    return True, result


def format_directory_output(items: List[Dict[str, Any]]) -> None:
    """
    Formatted output of directory contents for Windows.

    Args:
        items (List[Dict[str, Any]]): List of items to display
    """
    if not items:
        print(ru.EMPTY_DIRECTORY)
        return

    print(f"{ru.TYPE:<10} {ru.SIZE:<12} {ru.MODIFIED:<12} {ru.HIDDEN:<8} {ru.NAME:<30}")
    print("-" * 80)

    for item in items:
        if item['type'] == 'file':
            size_str = utils.format_size(item['size'])
        else:
            size_str = ru.FOLDER

        hidden_str = ru.YES if item['hidden'] else ru.NO
        name = item['name']
        if len(name) > 28:
            name = name[:25] + "..."

        print(f"{item['type']:<10} {size_str:<12} {item['modified']:<12} {hidden_str:<8} {name:<30}")


def move_up(current_path: str) -> str:
    """
    Move to parent directory in Windows.

    Args:
        current_path (str): Current path

    Returns:
        str: New path (parent directory)
    """
    parent_path = utils.get_parent_path(current_path)
    is_valid, error_msg = utils.validate_windows_path(parent_path)
    if is_valid:
        return parent_path
    else:
        return current_path


def move_down(current_path: str, target_dir: str) -> Tuple[bool, str]:
    """
    Move to specified subdirectory in Windows.

    Args:
        current_path (str): Current path
        target_dir (str): Subdirectory name to move to

    Returns:
        Tuple[bool, str]:
            - First element: True on success, False on error
            - Second element: New path on success, current path on error
    """
    new_path = os.path.join(current_path, target_dir)
    items = utils.safe_windows_listdir(current_path)

    if target_dir not in items:
        return False, current_path

    if not os.path.isdir(new_path):
        return False, current_path

    is_valid, error_msg = utils.validate_windows_path(new_path)
    if not is_valid:
        return False, current_path

    return True, new_path


def get_windows_special_folders() -> Dict[str, str]:
    """
    Get paths to Windows special folders.

    Returns:
        Dict[str, str]: Dictionary with paths to special folders
    """
    special_folders = {}
    user_profile = os.environ.get('USERPROFILE', '')

    if user_profile:
        folders_to_check = [
            ('Desktop', 'Desktop'),
            ('Documents', 'Documents'),
            ('Downloads', 'Downloads'),
            ('Music', 'Music'),
            ('Pictures', 'Pictures'),
            ('Videos', 'Videos'),
            ('AppData', 'AppData'),
            ('LocalAppData', os.path.join('AppData', 'Local')),
            ('RoamingAppData', os.path.join('AppData', 'Roaming'))
        ]
        
        for name, folder_path in folders_to_check:
            full_path = os.path.join(user_profile, folder_path)
            if os.path.exists(full_path):
                special_folders[name] = full_path

    system_drive = os.environ.get('SystemDrive', 'C:')
    windows_dir = os.environ.get('SystemRoot', os.path.join(system_drive, 'Windows'))
    
    system_folders = {
        'ProgramFiles': os.path.join(system_drive, 'Program Files'),
        'Windows': windows_dir,
        'System32': os.path.join(windows_dir, 'System32'),
        'Temp': os.environ.get('TEMP', os.path.join(system_drive, 'Temp'))
    }
    
    for name, path in system_folders.items():
        if os.path.exists(path):
            special_folders[name] = path

    return special_folders


def is_windows_system_path(path: str) -> bool:
    """
    Check if path is a Windows system directory.
    """
    system_keywords = ['Windows', 'Program Files', 'ProgramData', '$', 'System Volume Information']
    path_normalized = os.path.normpath(path)
    for keyword in system_keywords:
        if keyword in path_normalized:
            return True
    return False


def normalize_windows_path(path: str) -> str:
    """
    Normalize Windows path.
    """
    return os.path.normpath(path)


def build_windows_tree_recursive(path: str, depth: int = 0, max_depth: int = 5) -> Dict[str, Any]:
    """
    Recursive Windows directory tree building with visualization
    
    Args:
        path: Path to analyze
        depth: Current recursion depth
        max_depth: Maximum recursion depth
    
    Returns:
        Dictionary with directory tree structure
    """
    if depth >= max_depth:
        return {
            "name": os.path.basename(path),
            "type": "directory",
            "children": []
        }

    if is_windows_system_path(path):
        return {
            "name": os.path.basename(path),
            "type": "system_directory",
            "children": []
        }

    try:
        items = utils.safe_windows_listdir(path)
        children = []

        for item_name in items:
            item_path = os.path.join(path, item_name)
            
            try:
                if os.path.isdir(item_path):
                    if is_windows_system_path(item_path):
                        child_tree = {
                            "name": item_name,
                            "type": "system_directory",
                            "children": []
                        }
                    else:
                        child_tree = build_windows_tree_recursive(item_path, depth + 1, max_depth)
                    children.append(child_tree)
                else:
                    file_info = {
                        "name": item_name,
                        "type": "file",
                        "hidden": utils.is_hidden_windows_file(item_path)
                    }
                    children.append(file_info)
            except:
                continue

        return {
            "name": os.path.basename(path),
            "type": "directory",
            "children": children
        }

    except Exception:
        return {
            "name": os.path.basename(path),
            "type": "directory",
            "children": []
        }


def recursive_path_explorer(start_path: str, history: Optional[List[str]] = None) -> Generator[Tuple[str, List[str]], None, None]:
    """
    Recursive generator for navigation with visit history tracking
    
    Args:
        start_path: Starting path
        history: List of visited paths
    
    Yields:
        Tuple: (current_path, visit_history)
    """
    if history is None:
        history = []

    history.append(start_path)
    yield start_path, history.copy()

    try:
        success, items = list_directory(start_path)
        if not success:
            return

        for item in items:
            if item['type'] == 'folder':
                next_path = os.path.join(start_path, item['name'])
                if not is_windows_system_path(next_path):
                    yield from recursive_path_explorer(next_path, history.copy())
    except Exception:
        pass


def analyze_windows_structure_recursive(path: str, pattern: str = "*", level: int = 0) -> List[Tuple[int, str, str]]:
    """
    Recursive directory structure analysis with pattern search

    Args:
        path: Path to analyze
        pattern: Search pattern (e.g., "*.exe")
        level: Current nesting level

    Returns:
        List of tuples: (level, type, path)
    """
    result = []
    max_level = 10

    if level > max_level:
        return result

    try:
        items = utils.safe_windows_listdir(path)

        for item_name in items:
            item_path = os.path.join(path, item_name)

            if not os.path.exists(item_path):
                continue

            if os.path.isdir(item_path):
                elem_type = "DIR"
                if is_windows_system_path(item_path):
                    elem_type = "SYS_DIR"
                elif utils.is_hidden_windows_file(item_path):
                    elem_type = "HID_DIR"
            else:
                elem_type = "FILE"
                if utils.is_hidden_windows_file(item_path):
                    elem_type = "HID_FILE"

                if pattern != "*":
                    if not item_name.lower().endswith(pattern.replace("*", "").lower()):
                        continue

            result.append((level, elem_type, normalize_windows_path(item_path)))

            if os.path.isdir(item_path) and elem_type not in ["SYS_DIR"]:
                if not is_windows_system_path(item_path):
                    sub_result = analyze_windows_structure_recursive(item_path, pattern, level + 1)
                    result.extend(sub_result)

    except Exception:
        result.append((level, "ERROR", path))

    return result


def print_analysis_results(analysis_results: List[Tuple[int, str, str]]) -> None:
    """
    Formatted output of analysis results
    
    Args:
        analysis_results: Analysis results
    """
    if not analysis_results:
        print(ru.NO_DATA)
        return

    print(f"\n{ru.DIRECTORY_ANALYSIS}")
    print(ru.TOTAL_ELEMENTS.format(count=len(analysis_results)))
    print("-" * 80)
    print(f"{ru.LEVEL:<4} {ru.TYPE_COL:<10} {ru.PATH_COL}")
    print("-" * 80)
    
    type_stats = {}
    
    for level, elem_type, path in analysis_results:
        type_stats[elem_type] = type_stats.get(elem_type, 0) + 1
        indent = "  " * level
        
        if len(path) > 70:
            path = path[:35] + "..." + path[-32:]
        
        print(f"{level:<4} {elem_type:<10} {indent}{path}")
    
    print(f"\n{ru.STATISTICS}")
    for elem_type, count in sorted(type_stats.items()):
        percentage = (count / len(analysis_results)) * 100
        print(f"{elem_type:<10}: {count:>4} ({percentage:>5.1f}%)")


def navigate_with_history(start_path: str) -> None:
    """
    Interactive navigation with history
    """
    print(ru.START_NAVIGATION.format(path=start_path))
    print(ru.PRESS_ENTER_CONTINUE_NAV)
    
    try:
        for current_path, history in recursive_path_explorer(start_path):
            print(f"\n{ru.CURRENT_PATH_NAV.format(path=current_path)}")
            print(ru.HISTORY_DEPTH.format(depth=len(history)))
            
            success, items = list_directory(current_path)
            if success:
                folders = [item for item in items if item['type'] == 'folder']
                files = [item for item in items if item['type'] == 'file']
                print(ru.FOLDERS_COUNT.format(folders=len(folders), files=len(files)))
            
            command = input(f"\n{ru.COMMAND_PROMPT}").strip().lower()
            if command == 'q':
                print(ru.NAVIGATION_END)
                break
                
    except Exception as e:
        print(ru.NAVIGATION_ERROR.format(error=e))


def export_tree_to_json(tree: Dict[str, Any], filename: str) -> bool:
    """
    Export directory tree to JSON file
    
    Args:
        tree: Directory tree
        filename: Output filename
    
    Returns:
        True if successful, False on error
    """
    try:
        import json
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(tree, f, ensure_ascii=False, indent=2)
        print(ru.TREE_EXPORTED.format(filename=filename))
        return True
    except Exception as e:
        print(ru.EXPORT_ERROR.format(error=e))
        return False


def save_analysis_to_file(analysis_results: List[Tuple[int, str, str]], filename: str) -> bool:
    """
    Save analysis results to file
    
    Args:
        analysis_results: Analysis results
        filename: Output filename
    
    Returns:
        True if successful, False on error
    """
    try:
        with open(filename, 'w', encoding='utf-8') as f:
            f.write("Уровень;Тип;Путь\n")
            for level, elem_type, path in analysis_results:
                f.write(f"{level};{elem_type};{path}\n")
        print(ru.ANALYSIS_SAVED.format(filename=filename))
        return True
    except Exception as e:
        print(ru.SAVE_ERROR.format(error=e))
        return False


def is_readonly_windows_file(path: str) -> bool:
    """
    Check if file is read-only in Windows
    """
    try:
        return not os.access(path, os.W_OK)
    except:
        return False


def is_system_windows_file(path: str) -> bool:
    """
    Check if file has system attribute in Windows
    """
    try:
        import ctypes
        attributes = ctypes.windll.kernel32.GetFileAttributesW(str(path))
        return attributes != -1 and (attributes & 4)
    except:
        return False