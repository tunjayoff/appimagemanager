import time
from pathlib import Path
import os
import shutil
import logging
import tempfile
import subprocess
import configparser
import uuid
import errno # Import errno for checking permission error

from . import config
from . import integration
from .utils import sanitize_name
from .db_manager import DBManager # Add import for DB access

logger = logging.getLogger(__name__)

# Helper function to sanitize app names for directory/file names
# ... (sanitize_name fonksiyonu) ...

# --- UNINSTALLER Class removed ---

# --- Leftover Detection and Removal Functions ---

def find_leftover_installs():
    """Scans standard installation locations for untracked directories."""
    logger.info("Scanning for potentially leftover installations...")
    leftovers = []
    known_install_paths = set()
    MARKER_FILENAME = ".aim_managed" # File indicating directory is managed by this tool

    # 1. Get known installation paths from the database
    try:
        db = DBManager()
        known_apps = db.get_all_apps()
        known_install_paths = {app.get('install_path') for app in known_apps if app.get('install_path')}
        logger.debug(f"Found {len(known_install_paths)} known install paths from DB.")
    except Exception as e:
        logger.error(f"Failed to load database to get known paths: {e}", exc_info=True) 
        return [] # Cannot scan effectively without known paths

    # 2. Define standard directories to scan
    scan_dirs = []
    user_app_dir_base = os.path.join(config.USER_HOME, ".local/share")
    user_app_dir_specific = os.path.join(user_app_dir_base, config.APP_DIR_NAME)
    if os.path.isdir(user_app_dir_specific):
        scan_dirs.append(user_app_dir_specific)
        
    system_install_dir = config.SYSTEM_INSTALL_DIR 
    potential_system_dir_specific = os.path.join(system_install_dir, config.APP_DIR_NAME) 
    if os.path.isdir(potential_system_dir_specific):
        scan_dirs.append(potential_system_dir_specific)
        
    if not scan_dirs:
        logger.info("No standard installation directories found to scan.")
        return []
        
    # 3. Scan directories, find subdirs, and compare with known paths
    for scan_dir in scan_dirs:
        logger.debug(f"Scanning directory for subdirectories: {scan_dir}")
        try:
            for item_name in os.listdir(scan_dir):
                item_path = os.path.join(scan_dir, item_name)
                if os.path.isdir(item_path):
                    if item_path not in known_install_paths:
                        logger.info(f"Found potential leftover directory (not in DB): {item_path}")
                        
                        marker_path = os.path.join(item_path, MARKER_FILENAME)
                        is_marked = os.path.exists(marker_path)
                        leftover_type = 'marked_leftover' if is_marked else 'unmarked_leftover'
                        if is_marked:
                            logger.debug(f"Directory {item_path} contains marker file.")
                        else:
                            logger.debug(f"Directory {item_path} does NOT contain marker file.")
                             
                        parts = item_name.split('_')
                        guessed_name = sanitize_name(parts[0]).title() if parts else item_name
                        if not guessed_name: guessed_name = item_name # Fallback
                        
                        leftovers.append({
                            'path': item_path,
                            'guessed_name': guessed_name,
                            'type': leftover_type 
                        })
        except OSError as e:
            logger.error(f"Error scanning directory {scan_dir}: {e}")
            continue # Skip to next scan_dir on error

    logger.info(f"Found {len(leftovers)} total potential leftover installations.")
    return leftovers

def remove_leftover_install(path):
    """Removes a directory identified as a leftover installation and attempts heuristic cleanup of related files."""
    if not path or not os.path.isdir(path):
        logger.warning(f"Cannot remove leftover install: Invalid path '{path}'")
        return False
    
    logger.info(f"Attempting to remove leftover installation directory and associated files: {path}")

    guessed_name = None
    icon_name = None
    original_desktop_name = None
    
    potential_desktop_file = None
    for root, _, files in os.walk(path):
        for file in files:
            if file.lower().endswith('.desktop'):
                potential_desktop_file = os.path.join(root, file)
                logger.debug(f"Found potential desktop file in leftover dir: {potential_desktop_file}")
                break
        if potential_desktop_file:
            break
                         
    if potential_desktop_file:
        try:
            parser = configparser.ConfigParser(interpolation=None)
            parser.optionxform = str 
            parser.read(potential_desktop_file, encoding='utf-8')
            if 'Desktop Entry' in parser:
                entry = parser['Desktop Entry']
                guessed_name = entry.get("Name")
                icon_name = entry.get("Icon")
                original_desktop_name = os.path.basename(potential_desktop_file) 
                logger.debug(f"Parsed metadata from leftover desktop: Name={guessed_name}, Icon={icon_name}")
        except Exception as e:
            logger.warning(f"Could not parse potential desktop file '{potential_desktop_file}': {e}")

    if not guessed_name:
        base_dir_name = os.path.basename(path)
        parts = base_dir_name.split('_')
        guessed_name = sanitize_name(parts[0]).title() if parts else base_dir_name
        logger.warning(f"Could not find/parse desktop file in '{path}', guessing name as: '{guessed_name}'")
    
    sanitized_name = sanitize_name(guessed_name) if guessed_name else None
    sanitized_icon_name = sanitize_name(icon_name) if icon_name else sanitized_name 
    
    if sanitized_name:
        logger.debug(f"Checking for leftover symlinks for '{sanitized_name}'")
        user_link = os.path.join(config.USER_HOME, ".local/bin", sanitized_name)
        system_link = os.path.join(config.SYSTEM_BIN_DIR, sanitized_name)
        for link in [user_link, system_link]:
            if os.path.lexists(link): 
                try:
                    link_target = os.readlink(link)
                    if os.path.abspath(link_target).startswith(os.path.abspath(path)):
                        logger.info(f"Found symlink '{link}' pointing into leftover dir, attempting removal.")
                        try:
                            os.remove(link)
                            logger.info(f"Removed potential leftover symlink: {link}")
                        except Exception as e_rm:
                            logger.warning(f"Could not remove potential symlink '{link}': {e_rm}")
                except OSError as e_readlink:
                     logger.warning(f"Could not read symlink '{link}': {e_readlink}")
                except Exception as e_check:
                     logger.warning(f"Error checking symlink '{link}': {e_check}")

    desktop_filename_base = original_desktop_name if original_desktop_name else (f"{sanitized_name}.desktop" if sanitized_name else None)
    desktop_filename_reg = f"appimagekit_{sanitized_name}.desktop" if sanitized_name else None
    
    potential_desktop_filenames = {desktop_filename_base, desktop_filename_reg}
    potential_desktop_filenames.discard(None) 

    if potential_desktop_filenames:
        logger.debug(f"Checking for leftover desktop files: {potential_desktop_filenames}")
        user_desktop_dir = os.path.join(config.USER_HOME, ".local/share/applications")
        system_desktop_dir = config.SYSTEM_DESKTOP_DIR 
        
        for d_filename in potential_desktop_filenames:
            for d_dir in [user_desktop_dir, system_desktop_dir]:
                d_file = os.path.join(d_dir, d_filename)
                if os.path.lexists(d_file): 
                    logger.info(f"Found potential leftover desktop file '{d_file}', attempting removal.")
                    try:
                        os.remove(d_file)
                        logger.info(f"Removed potential leftover desktop file: {d_file}")
                        integration.update_desktop_database(d_dir) 
                    except Exception as e:
                        logger.warning(f"Could not remove potential desktop file '{d_file}': {e}")

    if sanitized_icon_name:
        logger.debug(f"Attempting heuristic removal of user icons for name: {sanitized_icon_name}")
        integration.remove_installed_icons(sanitized_icon_name, guessed_name) 
         
        system_icon_base_dir = "/usr/share/icons/hicolor" 
        likely_system_icons = False
        for size in ["16x16", "32x32", "48x48", "64x64", "128x128", "256x256", "512x512", "scalable"]:
            for ext in [".png", ".svg", ".svgz"]:
                sys_icon_path = os.path.join(system_icon_base_dir, size, "apps", f"{sanitized_icon_name}{ext}")
                if os.path.exists(sys_icon_path):
                    logger.warning(f"Potential leftover system icon found (requires manual/sudo removal): {sys_icon_path}")
                    likely_system_icons = True
                    break 
            if likely_system_icons: 
                break

    logger.info(f"Removing main leftover installation directory: {path}")
    try:
        shutil.rmtree(path)
        logger.info(f"Successfully removed leftover directory: {path}")
        return True
    except (OSError, PermissionError) as e:
        logger.error(f"Failed to remove leftover directory '{path}': {e}")
        return False
    except Exception as e:
        logger.error(f"Unexpected error removing leftover directory '{path}': {e}")
        return False

def find_leftovers(app_name):
    """Finds potential leftover user config/data files after uninstall, based on app name variations."""
    if not app_name:
        logger.warning("find_leftovers called with no app name.")
        return []
             
    logger.info(f"Checking for potential leftover user data/config for '{app_name}'...")
    potential_paths = []
    sanitized_name = sanitize_name(app_name) 
    
    name_variations = set()
    if app_name:
         name_variations.add(app_name) 
         name_variations.add(app_name.lower()) 
         name_variations.add(app_name.replace(' ',''))
         name_variations.add(app_name.replace(' ','').lower())
         name_variations.add('.' + app_name.replace(' ',''))
         name_variations.add('.' + app_name.replace(' ','').lower())

    if sanitized_name and sanitized_name != app_name.lower(): 
         name_variations.add(sanitized_name)
         name_variations.add(sanitized_name.lower())
         name_variations.add('.' + sanitized_name)
         name_variations.add('.' + sanitized_name.lower())
    
    name_variations.discard('')
    if '.' in name_variations: name_variations.discard('.') 
    
    logger.debug(f"Checking name variations for leftovers: {name_variations}")

    scan_dirs = [
        os.path.join(config.USER_HOME, '.config'),
        os.path.join(config.USER_HOME, '.cache'),
        os.path.join(config.USER_HOME, '.local', 'share'),
    ]

    for scan_dir in scan_dirs:
        if not os.path.isdir(scan_dir):
            logger.debug(f"Skipping scan, directory not found: {scan_dir}")
            continue
            
        logger.debug(f"Scanning config/cache directory: {scan_dir}")
        try:
            for item_name in os.listdir(scan_dir):
                if item_name in name_variations or item_name.lower() in name_variations:
                    item_path = os.path.join(scan_dir, item_name)
                    if os.path.lexists(item_path) and item_path not in potential_paths: 
                        logger.info(f"Found potential config/cache leftover: {item_path}")
                        potential_paths.append(item_path)
        except OSError as e:
            logger.error(f"Error scanning directory '{scan_dir}' for leftovers: {e}")
            continue 

    if potential_paths:
        logger.info(f"Found {len(potential_paths)} potential leftover user files/dirs.")
    else:
        logger.info("No potential leftover user files/dirs found matching name variations.")
        
    return potential_paths

def remove_selected_leftovers(paths):
    """Removes a list of files or directories (typically user config/cache leftovers)."""
    if not paths:
        logger.debug("remove_selected_leftovers called with empty list.")
        return True, 0
        
    logger.info(f"Attempting to remove {len(paths)} selected leftover items...")
    success_count = 0
    total_count = len(paths)
    items_that_did_not_exist = 0
    overall_success = True 

    for path in paths:
        logger.debug(f"Attempting removal of: {path}")
        removed = False
        try:
            if os.path.isfile(path) or os.path.islink(path):
                os.remove(path)
                logger.info(f"Removed leftover file/link: {path}")
                removed = True
            elif os.path.isdir(path):
                shutil.rmtree(path)
                logger.info(f"Removed leftover directory: {path}")
                removed = True
            else:
                 logger.warning(f"Leftover item not found or is not file/dir/link: {path}")
                 items_that_did_not_exist += 1
                 continue 
        except (OSError, PermissionError) as e: 
            logger.error(f"Failed to remove leftover item {path}: {e}")
            overall_success = False
        except Exception as e:
             logger.error(f"Unexpected error removing leftover item {path}: {e}", exc_info=True)
             overall_success = False
        
        if removed: 
           success_count += 1 

    adjusted_total = total_count - items_that_did_not_exist
    logger.info(f"Finished removing selected leftovers. Successfully removed {success_count}/{adjusted_total} items.")
    return overall_success, success_count

# --- Orphaned Integration File Detection ---

def find_orphaned_integrations():
    """Scans for .desktop files marked as managed but not linked to a known app in the database."""
    logger.info("Scanning for orphaned integration files (.desktop)...")
    orphans = []
    known_apps_info = {} 
    known_key_paths = set() 

    try:
        db = DBManager()
        known_apps = db.get_all_apps()
        for app in known_apps:
            key = (app.get('install_path',''), 
                   app.get('desktop_file_path',''), 
                   app.get('executable_symlink',''))
            known_key_paths.add(key)
        logger.debug(f"Loaded {len(known_apps)} known app entries from DB ({len(known_key_paths)} unique path sets).")
    except Exception as e:
        logger.error(f"Failed to load known apps from database: {e}", exc_info=True)
        return [] 

    app_dirs = [
        os.path.expanduser("~/.local/share/applications"),
        "/usr/local/share/applications",
        "/usr/share/applications" 
    ]
    MARKER_COMMENT = "Managed by AppImage Manager"

    found_desktop_files = []
    for app_dir in app_dirs:
        if os.path.isdir(app_dir):
            try:
                logger.debug(f"Scanning for .desktop files in: {app_dir}")
                for filename in os.listdir(app_dir):
                    if filename.lower().endswith(".desktop"):
                        full_path = os.path.join(app_dir, filename)
                        if os.path.isfile(full_path): 
                            found_desktop_files.append(full_path)
            except OSError as e:
                logger.warning(f"Could not scan directory '{app_dir}': {e}")

    logger.debug(f"Found {len(found_desktop_files)} total .desktop files to check.")

    for desktop_path in found_desktop_files:
        try:
            with open(desktop_path, 'r', encoding='utf-8') as f:
                content = f.read()

            if MARKER_COMMENT not in content:
                logger.debug(f"Skipping '{desktop_path}': Does not contain marker comment.")
                continue 

            is_known_by_path = False
            for (_, known_desktop_p, _) in known_key_paths:
                if known_desktop_p and os.path.exists(known_desktop_p) and os.path.samefile(desktop_path, known_desktop_p):
                    is_known_by_path = True
                    logger.debug(f"Desktop file '{desktop_path}' matches known app by path.")
            break

            if is_known_by_path:
                         continue

            exec_path_in_desktop = None
            for line in content.splitlines():
                if line.strip().startswith("Exec="):
                    exec_value = line.strip()[5:] 
                    if ' ' in exec_value:
                        exec_value = exec_value.split(' ')[0]
                    exec_path_in_desktop = exec_value.strip('"\'')
                    break
            
            if not exec_path_in_desktop:
                logger.warning(f"Found marked desktop file '{desktop_path}' but could not parse Exec= line. Assuming orphan.")

            is_known_by_exec = False
            if exec_path_in_desktop:
                 for (known_install_p, _, known_symlink_p) in known_key_paths:
                     if known_install_p and exec_path_in_desktop.startswith(known_install_p):
                         is_known_by_exec = True
                         logger.debug(f"Desktop file '{desktop_path}' Exec= points into known install path '{known_install_p}'.")
                         break 
                     if known_symlink_p and os.path.exists(known_symlink_p) and os.path.exists(exec_path_in_desktop) and os.path.samefile(exec_path_in_desktop, known_symlink_p):
                         is_known_by_exec = True
                         logger.debug(f"Desktop file '{desktop_path}' Exec= points to known symlink '{known_symlink_p}'.")
                         break
            
            if is_known_by_exec:
                 continue 

            logger.info(f"Found potential orphaned integration file: {desktop_path} (Exec={exec_path_in_desktop})")
            guessed_name = os.path.splitext(os.path.basename(desktop_path))[0]
            if guessed_name.startswith("appimagekit_"): guessed_name = guessed_name[len("appimagekit_"):]
            
            orphans.append({"path": desktop_path, "name": guessed_name, "type": "integration"})

        except Exception as e:
            logger.warning(f"Could not read or parse desktop file '{desktop_path}': {e}")

    logger.info(f"Orphaned integration scan complete. Found {len(orphans)} potential orphans.")
    return orphans

def remove_orphaned_integration(desktop_file_path):
    """Removes an orphaned .desktop file and updates system caches."""
    if not desktop_file_path or not os.path.lexists(desktop_file_path): 
        logger.warning(f"Cannot remove orphaned integration: Invalid or non-existent path '{desktop_file_path}'")
        return False
        
    logger.info(f"Attempting to remove orphaned integration file: {desktop_file_path}")
    success = True
    
    try:
        os.remove(desktop_file_path)
        logger.info(f"Successfully removed orphaned desktop file: {desktop_file_path}")
    except (OSError, PermissionError) as e: 
        if isinstance(e, PermissionError) or (hasattr(e, 'errno') and e.errno == errno.EACCES):
             logger.error(f"Permission denied removing orphaned desktop file '{desktop_file_path}'. Root privileges may be required.")
        else:
             logger.error(f"Failed to remove orphaned desktop file '{desktop_file_path}': {e}")
             success = False
    except Exception as e_gen:
         logger.error(f"Unexpected error removing orphaned desktop file '{desktop_file_path}': {e_gen}")
         success = False
                        
    if success: 
        try:
            parent_dir = os.path.dirname(desktop_file_path)
            integration.update_desktop_database(parent_dir)
            integration.update_icon_cache() 
            if parent_dir.startswith("/usr"):
                 logger.warning("Removed system desktop file, but cannot update system icon cache without root.")
        except Exception as e_cache:
            logger.warning(f"Failed to update system caches after removing '{desktop_file_path}': {e_cache}")

    return success

# Assuming sanitize_name is correctly imported from .utils

# ... rest of file ... 