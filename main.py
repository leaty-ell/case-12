# main.py
import os
import sys
import platform
from typing import NoReturn

import utils
import navigation
import analysis
import search
import ru_local as ru


def check_windows_environment() -> bool:
    """
    Checks if the program is running on Windows operating system.
    Returns:
        bool: True if running on Windows, False otherwise.
    """
    if not utils.is_windows_os():
        print(ru.ERROR_WINDOWS_ONLY)
        print(ru.CURRENT_OS.format(os=platform.system()))
        print(ru.PROGRAM_EXIT)
        return False
    return True


def display_windows_banner() -> None:
    """
    Displays a welcome banner with Windows-specific information.
    Shows current drive, path, available drives, and basic instructions.
    """
    print("=" * 70)
    print(ru.TITLE.center(70))
    print("=" * 70)
    print(ru.YEAR_2142.center(70))
    print("=" * 70)
    
    current_drive = navigation.get_current_drive()
    print(ru.CURRENT_DRIVE.format(drive=current_drive))
    
    current_path = os.getcwd()
    print(ru.CURRENT_PATH.format(path=current_path))
    
    drives = navigation.list_available_drives()
    print(ru.AVAILABLE_DRIVES.format(drives=', '.join(drives)))
    
    print("\n" + ru.HELP_COMMAND)
    print("=" * 70)


def display_main_menu(current_path: str) -> None:
    """
    Displays the main menu with available commands.
    Args:
        current_path: Current working directory path.
    """
    print(f"\n{ru.CURRENT_PATH.format(path=current_path)}")
    print("-" * 70)
    
    print(ru.MAIN_MENU_TITLE)
    print(f"  {ru.LIST_CONTENTS}")
    print(f"  {ru.ANALYZE_DIR}")
    print(f"  {ru.SEARCH_FILES}")
    print(f"  {ru.ADVANCED_ANALYSIS}")
    print(f"  {ru.MOVE_UP}")
    print(f"  {ru.MOVE_DOWN}")
    print(f"  {ru.SPECIAL_FOLDERS}")
    print(f"  {ru.CHANGE_DRIVE}")
    print(f"  {ru.EXIT_PROGRAM}")
    print(f"  {ru.HELP_MENU}")
    print("-" * 70)


def handle_windows_navigation(command: str, current_path: str) -> str:
    """
    Handles navigation commands for Windows filesystem.
    Args:
        command: Navigation command (5-8).
        current_path: Current working directory path.
    Returns:
        str: New path after navigation, or same path if navigation failed.
    """
    if command == "5":
        new_path = navigation.move_up(current_path)
        if new_path != current_path:
            print(ru.MOVED_TO.format(path=new_path))
            return new_path
        print(ru.ALREADY_ROOT)
        return current_path
    
    elif command == "6":
        success, items = navigation.list_directory(current_path)
        if not success:
            print(ru.FAILED_LIST_DIR)
            return current_path
        
        folders = [item['name'] for item in items if item['type'] == 'folder']
        if not folders:
            print(ru.NO_SUBDIRS)
            return current_path
        
        print(f"\n{ru.AVAILABLE_SUBDIRS}")
        for i, folder in enumerate(folders[:15], 1):
            print(f"  {i}. {folder}")
        if len(folders) > 15:
            print(f"  ... и ещё {len(folders) - 15}")
        
        choice = input(f"\n{ru.ENTER_NUMBER_OR_NAME}").strip()
        if not choice:
            return current_path
        
        if choice.isdigit():
            index = int(choice) - 1
            if 0 <= index < len(folders):
                target_dir = folders[index]
            else:
                print(ru.INVALID_NUMBER)
                return current_path
        else:
            target_dir = choice

        success, new_path = navigation.move_down(current_path, target_dir)
        if success:
            print(ru.MOVED_TO.format(path=new_path))
            return new_path
        
        print(ru.FAILED_MOVE.format(dir=target_dir))
        return current_path
    
    elif command == "8":
        drives = navigation.list_available_drives()
        print(f"\n{ru.AVAILABLE_DRIVES.format(drives=', '.join(drives))}:")
        for i, drive in enumerate(drives, 1):
            print(f"  {i}. {drive}")
        
        choice = input(f"\n{ru.SELECT_DRIVE}").strip()
        if not choice:
            return current_path
        
        if choice.isdigit():
            index = int(choice) - 1
            if 0 <= index < len(drives):
                selected_drive = drives[index]
            else:
                print(ru.INVALID_NUMBER)
                return current_path
        else:
            selected_drive = choice.upper()
            if not selected_drive.endswith(":"):
                selected_drive += ":"
        
        if selected_drive in drives:
            new_path = selected_drive + "\\"
            if os.path.exists(new_path):
                print(ru.SWITCHED_DRIVE.format(drive=selected_drive))
                return new_path
            print(ru.DRIVE_UNAVAILABLE.format(drive=selected_drive))
        else:
            print(ru.DRIVE_NOT_FOUND.format(drive=selected_drive))
        
        return current_path
    
    elif command == "7": 
        special_folders = navigation.get_windows_special_folders()
        if not special_folders:
            print(ru.NO_SPECIAL_FOLDERS)
            return current_path
        
        print(f"\n{ru.WINDOWS_SPECIAL_FOLDERS}")
        folder_items = list(special_folders.items())
        for i, (name, path) in enumerate(folder_items[:10], 1):
            print(f"  {i}. {name}")
        
        choice = input(f"\n{ru.ENTER_FOLDER_NUMBER}").strip()
        if choice and choice.isdigit():
            index = int(choice) - 1
            if 0 <= index < len(folder_items) and index < 10:
                name, path = folder_items[index]
                print(ru.MOVE_TO_FOLDER.format(name=name, path=path))

                is_valid, error_msg = utils.validate_windows_path(path)
                if is_valid and os.path.exists(path):
                    return path
                else:
                    print(ru.PATH_UNAVAILABLE.format(error=error_msg))
        
        return current_path
    
    return current_path


def handle_windows_analysis(command: str, current_path: str) -> None:
    """
    Handles analysis commands for Windows filesystem.
    Args:
        command: Analysis command (2 or 4).
        current_path: Current working directory path.
    """
    if command == "2":
        print(f"\n{ru.BASIC_STATS.format(path=current_path)}")
        success = analysis.show_windows_directory_stats(current_path)
        if not success:
            print(ru.ANALYSIS_ERROR)
    
    elif command == "4":
        print(f"\n{ru.ADVANCED_STATS.format(path=current_path)}")
        print("-" * 50)

        print(f"\n{ru.COUNT_FILES_SIZE}")
        success, file_count = analysis.count_files(current_path)
        if success:
            print(f"   {ru.TOTAL_FILES.format(count=file_count)}")
        
        success, total_bytes = analysis.count_bytes(current_path)
        if success:
            size_str = utils.format_size(total_bytes)
            print(f"   {ru.TOTAL_SIZE_BYTES.format(size=size_str)}")
        
        print(f"\n{ru.FILE_TYPE_STATS}")
        success, type_stats = analysis.analyze_windows_file_types(current_path)
        if success and type_stats:
            sorted_items = sorted(type_stats.items(), key=lambda x: x[1]['count'], reverse=True)[:5]
            for category, data in sorted_items:
                size_str = utils.format_size(data['total_size'])
                print(f"   {category}: {data['count']} файлов ({size_str})")
        
        print(f"\n{ru.FILE_ATTRIB_STATS}")
        attr_stats = analysis.get_windows_file_attributes_stats(current_path)
        total_with_attrs = sum(attr_stats.values())
        if total_with_attrs > 0:
            for attr, count in attr_stats.items():
                if count > 0:
                    print(f"   {attr}: {count}")
        else:
            print(f"   {ru.FILES_WITH_ATTRS}")
        
        print("\n" + "-" * 50)
        print(f" {ru.ANALYSIS_COMPLETE}")


def handle_windows_search(command: str, current_path: str) -> None:
    """
    Handles search commands for Windows filesystem.
    Args:
        command: Search command (3).
        current_path: Current working directory path.
    """
    if command == "3":
        print(f"\n{ru.SEARCH_MENU.format(path=current_path)}")
        print(ru.STARTING_SEARCH)
        should_continue = search.search_menu_handler(current_path)
        if not should_continue:
            print(ru.RETURN_MAIN_MENU)


def run_windows_command(command: str, current_path: str) -> str:
    """
    Main command handler using match-case.
    Args:
        command: User command input.
        current_path: Current working directory path.
    Returns:
        str: New path after command execution.
    """
    match command:
        case "1":
            print(f"\n{ru.DIRECTORY_CONTENTS.format(path=current_path)}")
            success, items = navigation.list_directory(current_path)
            if success:
                navigation.format_directory_output(items)
                print(f"\n{ru.TOTAL_ITEMS.format(count=len(items))}")
            else:
                print(ru.FAILED_LIST_DIR)
            return current_path
            
        case "2" | "4":
            handle_windows_analysis(command, current_path)
            return current_path
            
        case "3":
            handle_windows_search(command, current_path)
            return current_path
            
        case "5" | "6" | "7" | "8":
            return handle_windows_navigation(command, current_path)
            
        case "0":
            print(f"\n{ru.EXIT_PROGRAM_CONFIRM}")
            print(ru.THANK_YOU)
            sys.exit(0)
            
        case "help":
            print("\n" + "=" * 70)
            print(ru.HELP_TITLE.center(70))
            print("=" * 70)
            print(ru.SHOW_CONTENTS)
            print(ru.BASIC_STATISTICS)
            print(ru.SEARCH_MENU_HELP)
            print(ru.ADVANCED_STATISTICS)
            print(ru.GO_PARENT)
            print(ru.GO_SUBDIR)
            print(ru.SPECIAL_FOLDERS_HELP)
            print(ru.CHANGE_DRIVE_HELP)
            print(ru.EXIT_HELP)
            print("=" * 70)
            return current_path
            
        case "":
            return current_path
            
        case _:
            print(ru.UNKNOWN_COMMAND.format(command=command))
            print(f"   {ru.ENTER_HELP}")
            return current_path


def main() -> NoReturn:
    """
    Main program function for Windows File Archaeologist.
    Handles program initialization, main loop, and cleanup.
    """
    if not check_windows_environment():
        input(f"\n{ru.PRESS_ENTER_EXIT}")
        sys.exit(1)

    display_windows_banner()

    current_path = os.getcwd()
    
    try:
        while True:
            try:
                display_main_menu(current_path)
                command = input("\nВведите команду: ").strip()
                
                if command.lower() in ["exit", "quit", "q"]:
                    print(f"\n {ru.EXIT_PROGRAM_CONFIRM}")
                    break
                
                new_path = run_windows_command(command, current_path)
                
                if new_path != current_path:
                    current_path = new_path
                
                if command not in ["help", ""]:
                    input(f"\n{ru.PRESS_ENTER_CONTINUE}")
                    
            except KeyboardInterrupt:
                print(f"\n\n {ru.INTERRUPTED}")
                confirm = input(f"{ru.EXIT_CONFIRM}").strip().lower()
                if confirm == 'y':
                    print(f" {ru.EXITING}")
                    break
                continue
                
            except Exception as e:
                print(f"\n {ru.CRITICAL_ERROR.format(error=e)}")
                print(ru.PROGRAM_COMPLETE)
                continue
                
    except Exception as e:
        print(f"\n{ru.CRITICAL_ERROR.format(error=e)}")
        input(ru.PRESS_ENTER_EXIT)
    
    print(f"\n{ru.PROGRAM_COMPLETE}")
    sys.exit(0)


if __name__ == "__main__":
    main()