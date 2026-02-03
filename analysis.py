# analysis.py
import os
import hashlib
import re
import time
import stat
from typing import Dict, List, Tuple, Set, Callable, Any
from collections import defaultdict
from datetime import datetime, timedelta

import utils
import navigation
import ru_local as ru


def safe_file_walk(path: str, max_depth: int = 100):
    """
    Safely traverse files recursively with depth limitation.
    
    Args:
        path: Starting directory path for traversal
        max_depth: Maximum recursion depth to prevent infinite loops
        
    Yields:
        File paths discovered during recursive traversal
    """
    def walk_recursive(current_path, current_depth, visited):
        if current_depth > max_depth or current_path in visited:
            return
        visited.add(current_path)
        
        items = utils.safe_windows_listdir(current_path)
        
        for item in items:
            item_path = os.path.join(current_path, item)
            try:
                if os.path.isdir(item_path):
                    yield from walk_recursive(item_path, current_depth + 1, visited)
                elif os.path.isfile(item_path):
                    yield item_path
            except (PermissionError, OSError):
                continue
    
    yield from walk_recursive(path, 0, set())


def get_windows_file_attributes(file_path: str) -> Dict[str, bool]:
    """
    Retrieve all Windows file attributes for a given file path.
    
    Args:
        file_path: Path to the file to examine
        
    Returns:
        Dictionary with boolean values for each Windows file attribute
    """
    attributes = {
        'hidden': False,
        'system': False,
        'readonly': False,
        'archive': False,
        'compressed': False,
        'encrypted': False
    }
    
    try:
        file_stat = os.stat(file_path)
        
        attributes['hidden'] = utils.is_hidden_windows_file(file_path)
        
        try:
            import ctypes
            from ctypes import wintypes
            
            FILE_ATTRIBUTE_READONLY = 0x1
            FILE_ATTRIBUTE_HIDDEN = 0x2
            FILE_ATTRIBUTE_SYSTEM = 0x4
            FILE_ATTRIBUTE_ARCHIVE = 0x20
            FILE_ATTRIBUTE_COMPRESSED = 0x800
            FILE_ATTRIBUTE_ENCRYPTED = 0x4000
            
            GetFileAttributes = ctypes.windll.kernel32.GetFileAttributesW
            GetFileAttributes.argtypes = [wintypes.LPCWSTR]
            GetFileAttributes.restype = wintypes.DWORD
            
            attrs = GetFileAttributes(file_path)
            
            if attrs != 0xFFFFFFFF:
                attributes['readonly'] = bool(attrs & FILE_ATTRIBUTE_READONLY)
                attributes['system'] = bool(attrs & FILE_ATTRIBUTE_SYSTEM)
                attributes['archive'] = bool(attrs & FILE_ATTRIBUTE_ARCHIVE)
                attributes['compressed'] = bool(attrs & FILE_ATTRIBUTE_COMPRESSED)
                attributes['encrypted'] = bool(attrs & FILE_ATTRIBUTE_ENCRYPTED)
                
        except (ImportError, AttributeError, OSError):
            attributes['readonly'] = not os.access(file_path, os.W_OK)
            
            if 'system' in file_path.lower() or file_path.lower().startswith('system'):
                attributes['system'] = True
                
            if file_path.endswith('.zip') or file_path.endswith('.rar'):
                attributes['archive'] = True
                
    except Exception:
        pass
    
    return attributes


def find_largest_files(path: str, limit: int = 10) -> List[Dict[str, Any]]:
    """
    Find the largest files within a directory and its subdirectories.
    
    Args:
        path: Root directory to search for large files
        limit: Maximum number of largest files to return
        
    Returns:
        List of dictionaries containing file information sorted by size
    """
    largest_files = []
    
    for file_path in safe_file_walk(path):
        try:
            file_size = os.path.getsize(file_path)
            file_name = os.path.basename(file_path)
            
            largest_files.append({
                'path': file_path,
                'name': file_name,
                'size': file_size,
                'size_str': utils.format_size(file_size)
            })
            
            largest_files.sort(key=lambda x: x['size'], reverse=True)
            if len(largest_files) > limit:
                largest_files = largest_files[:limit]
                
        except (OSError, PermissionError):
            continue
    
    return largest_files


def find_duplicate_files_recursive(path: str,
                                  checksum_func: Callable = None,
                                  visited: Set[str] = None) -> Dict[str, List[str]]:
    """
    Recursively find duplicate files by content checksum comparison.
    
    Args:
        path: Root directory to search for duplicates
        checksum_func: Optional custom checksum function, defaults to MD5
        visited: Set of already processed file paths
        
    Returns:
        Dictionary mapping file hashes to lists of duplicate file paths
    """
    if visited is None:
        visited = set()
    
    duplicates = defaultdict(list)
    
    for file_path in safe_file_walk(path):
        if file_path in visited:
            continue
        
        try:
            is_valid, error_msg = utils.validate_windows_path(file_path)
            if not is_valid:
                continue
            
            attrs = get_windows_file_attributes(file_path)
            if attrs.get('system', False):
                continue
            
            if checksum_func:
                file_hash = checksum_func(file_path)
            else:
                hasher = hashlib.md5()
                with open(file_path, 'rb') as f:
                    while chunk := f.read(8192):
                        hasher.update(chunk)
                file_hash = hasher.hexdigest()
            
            duplicates[file_hash].append(file_path)
            visited.add(file_path)
            
        except Exception:
            continue
    
    return {hash_val: paths for hash_val, paths in duplicates.items() if len(paths) > 1}


def analyze_file_dependencies_recursive(root_path: str,
                                       target_extensions: List[str] = None,
                                       dependency_tree: Dict[str, List[str]] = None) -> Dict[str, Any]:
    """
    Recursively analyze file dependencies based on import/include statements.
    
    Args:
        root_path: Root directory for dependency analysis
        target_extensions: File extensions to analyze, defaults to programming languages
        dependency_tree: Existing dependency structure to extend
        
    Returns:
        Dictionary containing dependency tree, cycles, and analysis statistics
    """
    if target_extensions is None:
        target_extensions = ['.cpp', '.h', '.hpp', '.c', '.py', '.js', '.ts', '.java']
    
    if dependency_tree is None:
        dependency_tree = {}
    
    analyzed = set()
    
    def find_dependencies(filepath):
        """Extract dependency references from file content."""
        deps = []
        
        try:
            with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
            
            _, ext = os.path.splitext(filepath)
            
            patterns = {
                '.c': r'#include\s+["<]([^">]+)[">]',
                '.cpp': r'#include\s+["<]([^">]+)[">]',
                '.h': r'#include\s+["<]([^">]+)[">]',
                '.hpp': r'#include\s+["<]([^">]+)[">]',
                '.py': r'^(?:import|from)\s+([a-zA-Z0-9_.]+)',
                '.js': r'(?:import|require)[^(]+["\']([^"\']+)["\']',
                '.ts': r'(?:import|require)[^(]+["\']([^"\']+)["\']',
                '.java': r'^import\s+([a-zA-Z0-9_.]+);'
            }
            
            if ext in patterns:
                matches = re.findall(patterns[ext], content, re.MULTILINE)
                deps.extend(matches)
                
        except Exception:
            pass
        
        return deps
    
    for file_path in safe_file_walk(root_path):
        _, ext = os.path.splitext(file_path)
        
        if ext.lower() in target_extensions and file_path not in analyzed:
            deps = find_dependencies(file_path)
            if deps:
                dependency_tree[file_path] = deps
            analyzed.add(file_path)
    
    cycles = []
    visited_nodes = set()
    
    def dfs(node, path):
        """Depth-first search to detect circular dependencies."""
        if node in path:
            cycle_start = path.index(node)
            cycles.append(path[cycle_start:] + [node])
            return
        
        if node in visited_nodes:
            return
        
        visited_nodes.add(node)
        
        if node in dependency_tree:
            for dep in dependency_tree[node]:
                matching_files = [f for f in dependency_tree.keys() if dep in f]
                for match in matching_files:
                    dfs(match, path + [node])
    
    for filepath in dependency_tree:
        dfs(filepath, [])
    
    return {
        'tree': dependency_tree,
        'cycles': list(set(tuple(cycle) for cycle in cycles)),
        'files_count': len(dependency_tree),
        'has_cycles': len(cycles) > 0
    }


def predict_storage_growth_recursive(path: str,
                                    days_back: int = 30,
                                    growth_data: Dict[str, List] = None) -> Dict[str, float]:
    """
    Predict storage growth trends using historical file modification data.
    
    Args:
        path: Directory to analyze for growth patterns
        days_back: Number of days to consider for historical analysis
        growth_data: Existing growth data collection to extend
        
    Returns:
        Dictionary mapping file paths to predicted growth rates in MB per day
    """
    if growth_data is None:
        growth_data = defaultdict(list)
    
    cutoff_time = time.time() - (days_back * 24 * 60 * 60)
    current_time = time.time()
    
    def collect_file_data(file_path):
        """Collect file modification timestamp and size data."""
        try:
            stat_info = os.stat(file_path)
            
            if stat_info.st_mtime >= cutoff_time:
                growth_data[file_path].append({
                    'time': stat_info.st_mtime,
                    'size': stat_info.st_size,
                    'date': datetime.fromtimestamp(stat_info.st_mtime)
                })
        except Exception:
            pass
    
    for file_path in safe_file_walk(path):
        collect_file_data(file_path)
    
    for file_path, data in list(growth_data.items()):
        if len(data) < 3:
            try:
                dir_path = os.path.dirname(file_path)
                file_name = os.path.basename(file_path)
                
                backup_patterns = [
                    f"{file_name}.bak",
                    f"{file_name}.old",
                    f"{file_name}.backup",
                    f"backup_{file_name}",
                    f"{os.path.splitext(file_name)[0]}_*.{os.path.splitext(file_name)[1]}"
                ]
                
                for pattern in backup_patterns:
                    import glob
                    for backup_file in glob.glob(os.path.join(dir_path, pattern)):
                        try:
                            backup_stat = os.stat(backup_file)
                            if backup_stat.st_mtime < cutoff_time:
                                growth_data[file_path].append({
                                    'time': backup_stat.st_mtime,
                                    'size': backup_stat.st_size,
                                    'date': datetime.fromtimestamp(backup_stat.st_mtime)
                                })
                        except:
                            continue
            except:
                pass
    
    predictions = {}
    
    for filepath, data in growth_data.items():
        if len(data) >= 3:
            data.sort(key=lambda x: x['time'])
            
            times = [(d['time'] - data[0]['time']) / (24 * 60 * 60) for d in data]
            sizes_mb = [d['size'] / (1024 * 1024) for d in data]
            
            n = len(times)
            sum_x = sum(times)
            sum_y = sum(sizes_mb)
            sum_xy = sum(x * y for x, y in zip(times, sizes_mb))
            sum_x2 = sum(x * x for x in times)
            
            try:
                denominator = n * sum_x2 - sum_x * sum_x
                if denominator != 0:
                    slope = (n * sum_xy - sum_x * sum_y) / denominator
                    predictions[filepath] = slope
            except ZeroDivisionError:
                continue
    
    return predictions


def count_files(path: str) -> Tuple[bool, int]:
    """
    Recursively count files in a Windows directory.
    
    Args:
        path: Directory path to count files in
        
    Returns:
        Tuple containing success status and total file count
    """
    total = 0
    
    def count_recursive(current_path, depth=0):
        nonlocal total
        
        if depth > 20:
            return
        
        success, items = navigation.list_directory(current_path)
        if not success:
            return
        
        for item in items:
            if item['type'] == 'folder':
                next_path = os.path.join(current_path, item['name'])
                count_recursive(next_path, depth + 1)
            else:
                total += 1
    
    try:
        is_valid, error_msg = utils.validate_windows_path(path)
        if not is_valid:
            return False, 0
        
        count_recursive(path)
        return True, total
    except Exception:
        return False, 0


def count_bytes(path: str) -> Tuple[bool, int]:
    """
    Recursively calculate total file size in bytes.
    
    Args:
        path: Directory path to calculate total size for
        
    Returns:
        Tuple containing success status and total size in bytes
    """
    total_bytes = 0
    
    def sum_recursive(current_path, depth=0):
        nonlocal total_bytes
        
        if depth > 20:
            return
        
        success, items = navigation.list_directory(current_path)
        if not success:
            return
        
        for item in items:
            if item['type'] == 'folder':
                next_path = os.path.join(current_path, item['name'])
                sum_recursive(next_path, depth + 1)
            else:
                total_bytes += item.get('size', 0)
    
    try:
        is_valid, error_msg = utils.validate_windows_path(path)
        if not is_valid:
            return False, 0
        
        sum_recursive(path)
        return True, total_bytes
    except Exception:
        return False, 0


def analyze_windows_file_types(path: str) -> Tuple[bool, Dict[str, Dict[str, Any]]]:
    """
    Analyze distribution of Windows-specific file types by extension.
    
    Args:
        path: Directory to analyze file type distribution in
        
    Returns:
        Tuple containing success status and file type statistics dictionary
    """
    stats = {}
    windows_extensions = {
        '.exe': 'Executable file',
        '.dll': 'Dynamic library',
        '.msi': 'Installer',
        '.bat': 'Batch file',
        '.ps1': 'PowerShell script',
        '.cmd': 'Command file',
        '.docx': 'Word document',
        '.xlsx': 'Excel spreadsheet',
        '.pptx': 'PowerPoint presentation',
        '.pdf': 'PDF document',
        '.txt': 'Text file',
        '.jpg': 'Image',
        '.jpeg': 'Image',
        '.png': 'Image',
        '.gif': 'Image',
        '.zip': 'Archive',
        '.rar': 'Archive',
        '.7z': 'Archive',
        '.tar': 'Archive',
        '.gz': 'Archive',
        '.log': 'Log file',
        '.ini': 'Configuration file',
        '.sys': 'System file',
        '.tmp': 'Temporary file'
    }
    
    def analyze_recursive(current_path, depth=0):
        if depth > 20:
            return
        
        success, items = navigation.list_directory(current_path)
        if not success:
            return
        
        for item in items:
            if item['type'] == 'folder':
                next_path = os.path.join(current_path, item['name'])
                analyze_recursive(next_path, depth + 1)
            else:
                _, ext = os.path.splitext(item['name'])
                ext = ext.lower()
                
                if ext in windows_extensions:
                    category = windows_extensions[ext]
                else:
                    category = 'Other'
                
                if category not in stats:
                    stats[category] = {'count': 0, 'total_size': 0, 'extensions': set()}
                
                stats[category]['count'] += 1
                stats[category]['total_size'] += item.get('size', 0)
                stats[category]['extensions'].add(ext)
    
    try:
        is_valid, error_msg = utils.validate_windows_path(path)
        if not is_valid:
            return False, {}
        
        analyze_recursive(path)
        
        if stats:
            total_files = sum(data['count'] for data in stats.values())
            total_size = sum(data['total_size'] for data in stats.values())
            
            for category, data in stats.items():
                data['percentage'] = (data['count'] / total_files * 100) if total_files > 0 else 0
                data['size_percentage'] = (data['total_size'] / total_size * 100) if total_size > 0 else 0
                data['avg_size'] = data['total_size'] / data['count'] if data['count'] > 0 else 0
                data['extensions'] = list(data['extensions'])
        
        return True, stats
    except Exception:
        return False, {}


def get_windows_file_attributes_stats(path: str) -> Dict[str, int]:
    """
    Collect statistics on Windows file attributes within a directory.
    
    Args:
        path: Directory to analyze file attributes in
        
    Returns:
        Dictionary with counts for each Windows file attribute type
    """
    stats = {
        'hidden': 0,
        'system': 0,
        'readonly': 0,
        'archive': 0,
        'compressed': 0,
        'encrypted': 0
    }
    
    def check_recursive(current_path, depth=0):
        if depth > 20:
            return
        
        success, items = navigation.list_directory(current_path)
        if not success:
            return
        
        for item in items:
            item_path = os.path.join(current_path, item['name'])
            
            if item['type'] == 'folder':
                check_recursive(item_path, depth + 1)
            else:
                attrs = get_windows_file_attributes(item_path)
                
                for attr_name, attr_value in attrs.items():
                    if attr_value:
                        stats[attr_name] += 1
    
    try:
        is_valid, error_msg = utils.validate_windows_path(path)
        if not is_valid:
            return stats
        
        check_recursive(path)
        return stats
    except Exception:
        return stats


def show_windows_directory_stats(path: str) -> bool:
    """
    Display comprehensive Windows directory statistics summary.
    
    Args:
        path: Directory path to analyze and display statistics for
        
    Returns:
        True if analysis completed successfully, False otherwise
    """
    try:
        print(f"\n{'='*60}")
        print(ru.DIRECTORY_STATS.format(path=path))
        print(f"{'='*60}")
        
        is_valid, error_msg = utils.validate_windows_path(path)
        if not is_valid:
            print(ru.PATH_ERROR.format(error=error_msg))
            return False
        
        print(f"\n{ru.GENERAL_INFO}")
        success, file_count = count_files(path)
        if success:
            print(f"   {ru.FILES_COUNT.format(count=file_count)}")
        
        success, total_bytes = count_bytes(path)
        if success:
            size_str = utils.format_size(total_bytes)
            print(f"   {ru.TOTAL_SIZE.format(size=size_str)}")
        
        print(f"\n{ru.FILE_TYPES}")
        success, type_stats = analyze_windows_file_types(path)
        if success and type_stats:
            sorted_stats = sorted(type_stats.items(), key=lambda x: x[1]['count'], reverse=True)
            
            for category, data in sorted_stats[:10]:
                size_str = utils.format_size(data['total_size'])
                print(f"   {category}:")
                print(f"     {ru.FILES_COUNT.format(count=data['count'])} ({data['percentage']:.1f}%)")
                print(f"     {ru.SIZE}: {size_str} ({data['size_percentage']:.1f}%)")
                print(f"     Средний размер: {utils.format_size(data['avg_size'])}")
                if data['extensions']:
                    extensions_str = ', '.join(sorted(data['extensions'])[:5])
                    if len(data['extensions']) > 5:
                        extensions_str += f"... (+{len(data['extensions']) - 5})"
                    print(f"     Расширения: {extensions_str}")
        
        print(f"\n{ru.FILE_ATTRIBUTES}")
        attr_stats = get_windows_file_attributes_stats(path)
        for attr, count in attr_stats.items():
            if count > 0:
                print(f"   {attr}: {count}")
        
        print(f"\n{ru.LARGEST_FILES}")
        largest_files = find_largest_files(path, limit=5)
        if largest_files:
            for i, file_info in enumerate(largest_files, 1):
                display_path = file_info['path']
                if len(display_path) > 50:
                    display_path = "..." + display_path[-47:]
                
                print(f"   {i}. {file_info['name']}: {file_info['size_str']}")
                print(f"      {ru.PATH_COL}: {display_path}")
        else:
            print(f"   {ru.EMPTY_RESULTS}")
        
        print(f"\n{'='*60}")
        print(f"{ru.ANALYSIS_COMPLETE}")
        print(f"{'='*60}")
        
        return True
        
    except Exception as e:
        print(f"\n{ru.ANALYSIS_ERROR_MSG.format(error=e)}")
        return False