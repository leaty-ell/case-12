# search.py
import os
import re
import fnmatch
import time
import datetime
from typing import List, Dict, Any, Tuple, Optional, Generator
from collections import defaultdict

import utils
import navigation
import analysis
import ru_local as ru


def find_files_windows(
        pattern: str,
        path: str,
        case_sensitive: bool = False
) -> List[str]:
    """Поиск файлов по шаблону с поддержкой wildcards (*, ?)."""
    results = []

    def search_recursive(current_path: str, depth: int = 0) -> None:
        if depth > 20:
            return

        success, items = navigation.list_directory(current_path)
        if not success:
            return

        if depth == 0:
            print(ru.SEARCH_PATTERN.format(pattern=pattern, path=path))

        for item in items:
            item_path = os.path.join(current_path, item['name'])

            if item['type'] == 'folder':
                search_recursive(item_path, depth + 1)
            else:
                filename = item['name']
                if not case_sensitive:
                    filename = filename.lower()
                    match_pattern = pattern.lower()
                else:
                    match_pattern = pattern

                if fnmatch.fnmatch(filename, match_pattern):
                    results.append(item_path)

                    if len(results) % 100 == 0 and depth == 0:
                        print(ru.FILES_FOUND.format(count=len(results)))

    try:
        is_valid, error_msg = utils.validate_windows_path(path)
        if not is_valid:
            print(ru.PATH_ERROR.format(error=error_msg))
            return results

        search_recursive(path)

        success, total_files = analysis.count_files(path)
        if success and depth == 0:
            print(ru.SEARCH_COMPLETE.format(found=len(results), total=total_files))

    except Exception as e:
        print(ru.SEARCH_ERROR.format(error=e))

    return results


def find_by_windows_extension(extensions: List[str], path: str) -> List[str]:
    """Поиск файлов по списку расширений Windows."""
    results = []

    normalized_extensions = []
    for ext in extensions:
        if not ext.startswith('.'):
            ext = '.' + ext
        normalized_extensions.append(ext.lower())

    def search_recursive(current_path: str, depth: int = 0) -> None:
        if depth > 20:
            return

        success, items = navigation.list_directory(current_path)
        if not success:
            return

        for item in items:
            item_path = os.path.join(current_path, item['name'])

            if item['type'] == 'folder':
                search_recursive(item_path, depth + 1)
            else:
                file_ext = os.path.splitext(item['name'])[1].lower()
                if file_ext in normalized_extensions:
                    results.append(item_path)

                    if len(results) % 50 == 0 and depth == 0:
                        print(ru.FILES_FOUND.format(count=len(results)))

    try:
        is_valid, error_msg = utils.validate_windows_path(path)
        if not is_valid:
            print(ru.PATH_ERROR.format(error=error_msg))
            return results

        print(ru.SEARCH_EXTENSIONS.format(extensions=', '.join(normalized_extensions)))
        search_recursive(path)
        print(ru.FILES_FOUND.format(count=len(results)))

    except Exception as e:
        print(ru.SEARCH_ERROR.format(error=e))

    return results


def find_large_files_windows(
        min_size_mb: float,
        path: str
) -> List[Dict[str, Any]]:
    """Поиск файлов, размер которых превышает указанный минимум."""
    results = []
    min_size_bytes = min_size_mb * 1024 * 1024

    def search_recursive(current_path: str, depth: int = 0) -> None:
        if depth > 20:
            return

        success, items = navigation.list_directory(current_path)
        if not success:
            return

        for item in items:
            item_path = os.path.join(current_path, item['name'])

            if item['type'] == 'folder':
                search_recursive(item_path, depth + 1)
            else:
                file_size = item.get('size', 0)
                if file_size >= min_size_bytes:
                    file_ext = os.path.splitext(item['name'])[1].lower()

                    file_info = {
                        'path': item_path,
                        'name': item['name'],
                        'size_bytes': file_size,
                        'size_mb': file_size / (1024 * 1024),
                        'type': file_ext,
                        'modified': item.get('modified', ''),
                        'hidden': item.get('hidden', False)
                    }
                    results.append(file_info)

                    if len(results) % 10 == 0 and depth == 0:
                        print(ru.FILES_FOUND.format(count=len(results)))

    try:
        is_valid, error_msg = utils.validate_windows_path(path)
        if not is_valid:
            print(ru.PATH_ERROR.format(error=error_msg))
            return results

        print(ru.LARGE_FILES_SEARCH.format(size=min_size_mb))
        search_recursive(path)

        results.sort(key=lambda x: x['size_bytes'], reverse=True)

        print(ru.LARGE_FILES_FOUND.format(count=len(results)))

    except Exception as e:
        print(ru.SEARCH_ERROR.format(error=e))

    return results


def find_windows_system_files(path: str) -> List[str]:
    """Поиск системных файлов Windows в указанном пути."""
    results = []

    system_extensions = {'.exe', '.dll', '.sys', '.drv', '.ocx', '.cpl', '.msi', '.msu'}

    special_folders = navigation.get_windows_special_folders()
    system_folders = {'Windows', 'System32', 'SysWOW64', 'ProgramFiles', 'ProgramFilesX86'}

    def search_recursive(current_path: str, depth: int = 0) -> None:
        if depth > 10:
            return

        success, items = navigation.list_directory(current_path)
        if not success:
            return

        for item in items:
            item_path = os.path.join(current_path, item['name'])

            if item['type'] == 'folder':
                folder_name = item['name'].lower()
                is_system_folder = any(
                    sys_folder.lower() in folder_name
                    for sys_folder in system_folders
                )

                if is_system_folder or depth == 0:
                    search_recursive(item_path, depth + 1)
            else:
                file_ext = os.path.splitext(item['name'])[1].lower()
                if file_ext in system_extensions:
                    results.append(item_path)

    try:
        is_valid, error_msg = utils.validate_windows_path(path)
        if not is_valid:
            print(ru.PATH_ERROR.format(error=error_msg))
            return results

        print(ru.SYSTEM_FILES_SEARCH)

        if not path or path == "/" or path == "\\":
            for folder_name, folder_path in special_folders.items():
                if folder_name in system_folders:
                    print(ru.SCANNING_FOLDER.format(folder=folder_name))
                    search_recursive(folder_path, 0)
        else:
            search_recursive(path, 0)

        print(ru.SYSTEM_FILES_FOUND.format(count=len(results)))

    except Exception as e:
        print(ru.SEARCH_ERROR.format(error=e))

    return results


def search_menu_handler(current_path: str) -> bool:
    """Интерактивное меню поиска с различными опциями."""
    while True:
        print(f"\n{'=' * 60}")
        print(ru.SEARCH_MENU_TITLE)
        print(f"{'=' * 60}")
        print(ru.CURRENT_PATH.format(path=current_path))
        print()
        print(ru.SEARCH_OPTION_PATTERN)
        print(ru.SEARCH_OPTION_EXT)
        print(ru.SEARCH_OPTION_SIZE)
        print(ru.SEARCH_OPTION_SYSTEM)
        print(ru.SEARCH_OPTION_STATS)
        print(ru.SEARCH_OPTION_RETURN)
        print()

        choice = input(ru.CHOOSE_OPTION).strip()

        if choice == "1":
            pattern = input(ru.PATTERN_INPUT).strip()
            if not pattern:
                print(ru.PATTERN_EMPTY)
                continue

            case_sensitive = input(ru.CASE_SENSITIVE).lower() == 'y'

            results = find_files_windows(pattern, current_path, case_sensitive)
            if results:
                print(f"\n{ru.SEARCH_RESULTS.format(count=len(results))}")
                format_windows_search_results(results, "pattern")
            else:
                print(ru.NO_FILES_FOUND)

        elif choice == "2":
            ext_input = input(ru.EXTENSIONS_INPUT).strip()
            if not ext_input:
                print(ru.EXTENSIONS_EMPTY)
                continue

            extensions = [ext.strip() for ext in ext_input.split(',')]
            results = find_by_windows_extension(extensions, current_path)

            if results:
                print(f"\n{ru.SEARCH_RESULTS.format(count=len(results))}")
                format_windows_search_results(results, "extension")
            else:
                print(ru.NO_FILES_FOUND)

        elif choice == "3":
            try:
                min_size = float(input(ru.MIN_SIZE_INPUT).strip())
                if min_size <= 0:
                    print(ru.INVALID_SIZE)
                    continue

                results = find_large_files_windows(min_size, current_path)

                if results:
                    print(f"\n{ru.LARGE_FILES_TOTAL.format(count=len(results), size=min_size)}")
                    format_windows_search_results(results, "large")

                    total_size_mb = sum(f['size_mb'] for f in results)
                    largest_file = max(results, key=lambda x: x['size_mb'])
                    print(f"\n{ru.TOTAL_SIZE_MB.format(size=total_size_mb)}")
                    print(ru.LARGEST_FILE.format(name=largest_file['name'], size=largest_file['size_mb']))
                else:
                    print(ru.NO_LARGE_FILES)

            except ValueError:
                print(ru.INVALID_NUMBER_FORMAT)

        elif choice == "4":
            results = find_windows_system_files(current_path)

            if results:
                print(f"\n{ru.SEARCH_RESULTS.format(count=len(results))}")
                format_windows_search_results(results, "system")

                ext_count = defaultdict(int)
                for file_path in results:
                    ext = os.path.splitext(file_path)[1].lower()
                    ext_count[ext] += 1

                print(f"\n{ru.FILE_TYPE_DISTRIBUTION}")
                for ext, count in sorted(ext_count.items(), key=lambda x: x[1], reverse=True):
                    print(f"  {ext}: {count} файлов")
            else:
                print(ru.NO_SYSTEM_FILES)

        elif choice == "5":
            analysis.show_windows_directory_stats(current_path)

        elif choice == "6":
            return True

        else:
            print(ru.INVALID_CHOICE)

        print()
        continue_search = input(ru.CONTINUE_SEARCH).lower()
        if continue_search != 'y':
            return True

    return False


def format_windows_search_results(results: List, search_type: str) -> None:
    """Форматированный вывод результатов поиска в зависимости от типа."""
    if not results:
        print(ru.NO_RESULTS)
        return

    print(f"{'=' * 80}")

    if search_type in ["pattern", "extension"]:
        for i, file_path in enumerate(results[:50], 1):
            display_path = file_path
            if len(display_path) > 70:
                display_path = "..." + display_path[-67:]
            print(f"{i:3d}. {display_path}")

        if len(results) > 50:
            print(ru.AND_MORE_FILES.format(count=len(results) - 50))

    elif search_type == "large":
        print(f"{'#':<3} {ru.SIZE:<12} {ru.TYPE_COL:<6} {ru.NAME:<40} {ru.PATH_COL:<30}")
        print("-" * 95)

        for i, file_info in enumerate(results[:20], 1):
            size_str = utils.format_size(file_info['size_bytes'])
            name = file_info['name']
            if len(name) > 38:
                name = name[:35] + "..."

            path = os.path.dirname(file_info['path'])
            if len(path) > 28:
                path = "..." + path[-25:]

            hidden_mark = "[H]" if file_info.get('hidden', False) else "   "

            print(f"{i:<3} {size_str:<12} {file_info['type']:<6} "
                  f"{name:<40} {path:<30} {hidden_mark}")

        if len(results) > 20:
            print(f"\n{ru.TOTAL_FILES_COUNT.format(count=len(results))}")

        if results:
            sample_files = results[:min(100, len(results))]
            attr_stats = defaultdict(int)
            for file_info in sample_files:
                attrs = analysis.get_windows_file_attributes(file_info['path'])
                for attr_name, attr_value in attrs.items():
                    if attr_value:
                        attr_stats[attr_name] += 1

            if attr_stats:
                print(f"\n{ru.FILE_ATTRIB_SAMPLE}")
                for attr, count in sorted(attr_stats.items()):
                    percentage = (count / len(sample_files)) * 100
                    print(f"  {attr}: {count} ({percentage:.1f}%)")

    elif search_type == "system":
        print(f"{'#':<3} {ru.NAME:<30} {ru.PATH_COL:<40} {ru.SIZE:<10}")
        print("-" * 85)

        for i, file_path in enumerate(results[:30], 1):
            filename = os.path.basename(file_path)
            if len(filename) > 28:
                filename = filename[:25] + "..."

            dirname = os.path.dirname(file_path)
            if len(dirname) > 38:
                dirname = "..." + dirname[-35:]

            try:
                size = os.path.getsize(file_path)
                size_str = utils.format_size(size)
            except Exception:
                size_str = "N/A"

            print(f"{i:<3} {filename:<30} {dirname:<40} {size_str:<10}")

        if len(results) > 30:
            print(f"\n{ru.TOTAL_SYSTEM_FILES.format(count=len(results))}")

    print(f"{'=' * 80}")


def recursive_content_search(
        root_path: str,
        search_pattern: str,
        file_extensions: List[str] = None,
        content_cache: Dict[str, str] = None
) -> List[Tuple[str, List[int]]]:
    """Рекурсивный поиск текста в содержимом файлов с кэшированием."""
    results = []
    if content_cache is None:
        content_cache = {}

    encodings = ['utf-8', 'cp1251', 'cp866', 'latin-1']

    def search_in_file(file_path: str) -> List[int]:
        matching_lines = []

        if file_path in content_cache:
            content = content_cache[file_path]
        else:
            content = None
            for encoding in encodings:
                try:
                    with open(file_path, 'r', encoding=encoding, errors='ignore') as f:
                        content = f.read()
                    break
                except UnicodeDecodeError:
                    continue
                except Exception:
                    break

            if content is None:
                return matching_lines

            content_cache[file_path] = content

        lines = content.split('\n')
        for line_num, line in enumerate(lines, 1):
            if search_pattern.lower() in line.lower():
                matching_lines.append(line_num)

        return matching_lines

    def search_recursive(current_path: str, depth: int = 0) -> None:
        if depth > 10:
            return

        success, items = navigation.list_directory(current_path)
        if not success:
            return

        for item in items:
            item_path = os.path.join(current_path, item['name'])

            if item['type'] == 'folder':
                search_recursive(item_path, depth + 1)
            else:
                if file_extensions:
                    file_ext = os.path.splitext(item['name'])[1].lower()
                    if file_ext not in file_extensions:
                        continue

                try:
                    matching_lines = search_in_file(item_path)
                    if matching_lines:
                        results.append((item_path, matching_lines))

                        if len(results) % 10 == 0:
                            print(ru.FILES_FOUND.format(count=len(results)))
                except Exception:
                    continue

    try:
        print(ru.CONTENT_SEARCH.format(pattern=search_pattern))
        search_recursive(root_path)
        print(ru.CONTENT_FILES_FOUND.format(count=len(results)))

    except Exception as e:
        print(ru.SEARCH_ERROR.format(error=e))

    return results


def smart_recursive_search(
        root_path: str,
        query: str,
        search_context: Dict[str, Any] = None,
        relevance_threshold: float = 0.5
) -> List[Tuple[str, float]]:
    """Умный поиск с оценкой релевантности на основе TF."""
    results = []

    query_terms = query.lower().split()

    def calculate_relevance(content: str, filename: str) -> float:
        text = (content + " " + filename).lower()

        total_terms = len(text.split())
        if total_terms == 0:
            return 0.0

        term_count = 0
        for term in query_terms:
            term_count += text.count(term)

        relevance = term_count / max(total_terms, 1)
        return min(relevance, 1.0)

    def search_recursive(current_path: str, depth: int = 0) -> None:
        if depth > 8:
            return

        success, items = navigation.list_directory(current_path)
        if not success:
            return

        for item in items:
            item_path = os.path.join(current_path, item['name'])

            if item['type'] == 'folder':
                folder_relevance = calculate_relevance("", item['name'])
                if folder_relevance >= relevance_threshold:
                    search_recursive(item_path, depth + 1)
            else:
                try:
                    with open(item_path, 'r', encoding='utf-8', errors='ignore') as f:
                        content = f.read(10000)

                    relevance = calculate_relevance(content, item['name'])
                    if relevance >= relevance_threshold:
                        results.append((item_path, relevance))

                except Exception:
                    relevance = calculate_relevance("", item['name'])
                    if relevance >= relevance_threshold:
                        results.append((item_path, relevance))

    try:
        print(ru.SMART_SEARCH.format(query=query))
        search_recursive(root_path)

        results.sort(key=lambda x: x[1], reverse=True)

        print(ru.FILES_FOUND.format(count=len(results)))

    except Exception as e:
        print(ru.SEARCH_ERROR.format(error=e))

    return results


def recursive_security_scan(
        root_path: str,
        security_rules: Dict[str, Any],
        scan_context: Dict[str, Any] = None
) -> Dict[str, List[Dict]]:
    """Рекурсивное сканирование файловой системы на предмет угроз безопасности."""
    if scan_context is None:
        scan_context = {}

    results = {
        'suspicious_executables': [],
        'open_permissions': [],
        'hidden_objects': [],
        'temp_files': [],
        'potential_threats': []
    }

    default_rules = {
        'suspicious_locations': ['temp', 'downloads', 'appdata\\local\\temp'],
        'dangerous_extensions': ['.exe', '.bat', '.cmd', '.ps1', '.vbs', '.js'],
        'max_temp_file_age_days': 30,
        'check_hidden_files': True,
        'check_open_permissions': True
    }

    rules = {**default_rules, **security_rules}

    import time

    def check_suspicious_location(file_path: str) -> bool:
        file_path_lower = file_path.lower()
        for location in rules['suspicious_locations']:
            if location in file_path_lower:
                return True
        return False

    def check_dangerous_extension(filename: str) -> bool:
        file_ext = os.path.splitext(filename)[1].lower()
        return file_ext in rules['dangerous_extensions']

    def check_temp_file_age(file_path: str) -> bool:
        try:
            stat_info = os.stat(file_path)
            file_age = time.time() - stat_info.st_mtime
            max_age = rules['max_temp_file_age_days'] * 24 * 60 * 60
            return file_age > max_age
        except Exception:
            return False

    def scan_recursive(current_path: str, depth: int = 0) -> None:
        if depth > 5:
            return

        success, items = navigation.list_directory(current_path)
        if not success:
            return

        for item in items:
            item_path = os.path.join(current_path, item['name'])

            if item['type'] == 'folder':
                if rules['check_hidden_files'] and item.get('hidden', False):
                    results['hidden_objects'].append({
                        'path': item_path,
                        'type': 'folder',
                        'reason': 'Hidden folder',
                        'severity': 'medium'
                    })

                scan_recursive(item_path, depth + 1)
            else:
                if check_dangerous_extension(item['name']):
                    if check_suspicious_location(item_path):
                        results['suspicious_executables'].append({
                            'path': item_path,
                            'name': item['name'],
                            'location': current_path,
                            'reason': 'Executable in suspicious location',
                            'severity': 'high'
                        })

                if rules['check_hidden_files'] and item.get('hidden', False):
                    results['hidden_objects'].append({
                        'path': item_path,
                        'type': 'file',
                        'name': item['name'],
                        'reason': 'Hidden file',
                        'severity': 'low'
                    })

                if 'temp' in item_path.lower() or item['name'].lower().endswith('.tmp'):
                    if check_temp_file_age(item_path):
                        results['temp_files'].append({
                            'path': item_path,
                            'name': item['name'],
                            'reason': 'Old temporary file',
                            'severity': 'low'
                        })

                if rules['check_open_permissions']:
                    try:
                        if os.access(item_path, os.W_OK):
                            if 'system' in item_path.lower() or 'windows' in item_path.lower():
                                results['open_permissions'].append({
                                    'path': item_path,
                                    'name': item['name'],
                                    'reason': 'System file is writable',
                                    'severity': 'high'
                                })
                    except Exception:
                        pass

    try:
        print(ru.SECURITY_SCAN)
        scan_recursive(root_path)

        total_threats = sum(len(category) for category in results.values())
        print(ru.SECURITY_SCAN_COMPLETE.format(count=total_threats))

        if total_threats > 0:
            print(f"\n{ru.SECURITY_RESULTS}")
            for category, items in results.items():
                if items:
                    print(f"  {category}: {len(items)}")

    except Exception as e:
        print(ru.SEARCH_ERROR.format(error=e))

    return results


def show_search_help():
    """Отображение справочной информации по функциям поиска."""
    print(f"\n{ru.SEARCH_HELP_TITLE}")
    print("=" * 50)
    print(ru.SEARCH_PATTERNS)
    print(ru.WINDOWS_EXTENSIONS)
    print(ru.EXECUTABLES)
    print(ru.SYSTEM_FILES)
    print(ru.DOCUMENTS)
    print(ru.SCRIPTS)
    print()
    print(ru.SECURITY_SCAN_HELP)
    print(ru.SECURITY_CHECKS)
    print("=" * 50)