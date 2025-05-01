"""
AppImage Manager - Desktop Integration Utilities
Handles creation/deletion of .desktop files, icon management, and cache updates.
"""

import os
import shutil
import subprocess
import logging
# import configparser # Unused import
import traceback

from . import config # Assuming config might be needed for paths etc.
from .utils import sanitize_name # <-- Import from new utils module

logger = logging.getLogger(__name__)

# --- Desktop Database ---

def update_desktop_database(desktop_dir):
    """Updates the desktop database for the specified directory."""
    if not desktop_dir or not os.path.isdir(desktop_dir):
        logger.warning(f"Desktop database güncellenemedi: Geçersiz dizin {desktop_dir}")
        return
        
    if shutil.which("update-desktop-database"):
        try:
            subprocess.run(["update-desktop-database", desktop_dir], check=False, capture_output=True)
            logger.info(f"Masaüstü veritabanı güncellendi: {desktop_dir}")
        except Exception as e:
             logger.warning(f"'update-desktop-database' çalıştırılırken hata: {e}")
    else:
         logger.warning("'update-desktop-database' komutu bulunamadı, veritabanı güncellenmedi.")

# --- Icon Management ---

def update_icon_cache(icon_base_dir=None):
    """Updates the icon theme cache."""
    if not icon_base_dir:
        # Default to user's hicolor cache if no specific dir provided
        icon_base_dir = os.path.join(config.USER_HOME, ".local/share/icons/hicolor")
        
    if not os.path.isdir(icon_base_dir):
         logger.warning(f"Icon cache güncellenemedi: Dizin bulunamadı {icon_base_dir}")
         return
         
    if shutil.which("gtk-update-icon-cache"):
        try:
            logger.info(f"Updating icon cache for directory: {icon_base_dir}")
            subprocess.run(["gtk-update-icon-cache", "-f", "-t", icon_base_dir],
                          check=False, capture_output=True)
            logger.info("Icon cache updated")
        except Exception as e:
            logger.warning(f"Failed to update icon cache: {e}")
    else:
        logger.warning("Icon cache update skipped (gtk-update-icon-cache not found).")
        
def copy_app_icons(final_icon_path, app_install_dir, app_info):
    """Copies icons found in the installation dir to standard user locations.
    
    Args:
        final_icon_path (str): Path to the primary icon file found in the install dir.
        app_install_dir (str): The root directory where the app was installed.
        app_info (dict): Application metadata dictionary (needs 'name', 'icon_name').

    Returns:
        str: The path or name of the primary icon copied to the standard location,
             or the original icon_name if copy fails. None if no icon info.
    """
    copied_icon_primary_path_or_name = app_info.get("icon_name") # Fallback
    icon_name = app_info.get("icon_name", "")
    app_name = app_info.get("name", "unknown")
    
    if not icon_name:
        # Try to use sanitized app name if icon name is missing in desktop file
        icon_name = sanitize_name(app_name)
        logger.warning(f"Icon name missing in metadata, using sanitized app name: {icon_name}")
        
    if not icon_name:
        logger.error("Cannot copy icons: No icon name or app name available.")
        return None

    standard_icon_base_dir = os.path.join(config.USER_HOME, ".local/share/icons/hicolor")
    icons_copied = False

    # 1. Copy the primary icon (if found and exists)
    if final_icon_path and os.path.exists(final_icon_path):
        try:
            icon_ext = os.path.splitext(final_icon_path)[1].lower()
            if icon_ext in ['.svg', '.svgz']:
                target_icon_dir = os.path.join(standard_icon_base_dir, "scalable", "apps")
            else: # Assume PNG or other bitmap, use 128x128 as default size dir
                target_icon_dir = os.path.join(standard_icon_base_dir, "128x128", "apps")
                
            os.makedirs(target_icon_dir, exist_ok=True)
            # Use the determined icon_name for the target file name
            target_icon_path = os.path.join(target_icon_dir, f"{icon_name}{icon_ext}")
            
            logger.debug(f"Copying primary icon to standard location: {final_icon_path} -> {target_icon_path}")
            shutil.copy2(final_icon_path, target_icon_path)
            logger.info(f"Primary icon copied to: {target_icon_path}")
            copied_icon_primary_path_or_name = icon_name # Use name for desktop file
            icons_copied = True
        except Exception as e:
            logger.error(f"Failed to copy primary icon to standard location: {e}")
    else:
         logger.warning(f"Cannot copy primary icon: Source path invalid or not found. Path: {final_icon_path}")

    # 2. Search for and copy additional icons from hicolor within install_dir
    try:
        hicolor_dir_relative_paths = ["share/icons/hicolor", "usr/share/icons/hicolor"]
        hicolor_dir_install = None
        for rel_path in hicolor_dir_relative_paths:
            potential_dir = os.path.join(app_install_dir, rel_path)
            if os.path.isdir(potential_dir):
                hicolor_dir_install = potential_dir
                break

        if hicolor_dir_install:
            logger.debug(f"Searching for additional icons in source hicolor directory: {hicolor_dir_install}")
            for size_dir in os.listdir(hicolor_dir_install):
                size_path = os.path.join(hicolor_dir_install, size_dir)
                # Basic check for common size directory names (e.g., 128x128, scalable)
                if os.path.isdir(size_path) and ("x" in size_dir or size_dir == "scalable"):
                    apps_dir = os.path.join(size_path, "apps")
                    if os.path.isdir(apps_dir):
                        for icon_file in os.listdir(apps_dir):
                            # Match icons starting with the icon_name and common extensions
                            if icon_file.startswith(icon_name + ".") and icon_file.endswith((".png", ".svg", ".svgz")):
                                src_icon = os.path.join(apps_dir, icon_file)
                                # Determine target directory based on size_dir
                                target_icon_dir = os.path.join(standard_icon_base_dir, size_dir, "apps")
                                os.makedirs(target_icon_dir, exist_ok=True)
                                target_icon = os.path.join(target_icon_dir, icon_file)
                                # Copy the icon
                                shutil.copy2(src_icon, target_icon)
                                logger.debug(f"Copied additional icon: {src_icon} -> {target_icon}")
                                icons_copied = True
    except Exception as e:
        logger.error(f"Error searching for/copying additional icons: {e}")

    # 3. Update icon cache if any icons were copied
    if icons_copied:
        update_icon_cache(standard_icon_base_dir)
        
    return copied_icon_primary_path_or_name


# --- Desktop Entry Management ---

def install_icon_with_xdg(icon_path, icon_name):
    """Installs an icon file using xdg-icon-resource."""
    if not shutil.which("xdg-icon-resource"):
        logger.warning("xdg-icon-resource command not found. Cannot install icon file properly.")
        return False
        
    if not icon_path or not os.path.exists(icon_path):
        logger.warning(f"Cannot install icon: Source path invalid or not found: {icon_path}")
        return False
        
    if not icon_name:
        logger.warning("Cannot install icon: Icon name not provided.")
        return False
        
    try:
        # --->>> Improve Size/Type Detection <<<---
        icon_ext = os.path.splitext(icon_path)[1].lower()
        size = ""
        
        if icon_ext in (".svg", ".svgz"):
            size = "scalable"
        elif icon_ext == ".png":
            # For PNG, ideally we'd read the size, but xdg-utils
            # often wants a hint. 128 is a reasonable default guess.
            size = "128" 
        elif icon_ext == ".xpm":
            # XPM doesn't usually use size specifier with xdg-icon-resource
            pass # Leave size empty
        else:
            logger.warning(f"Unsupported icon type ('{icon_ext}') for xdg-icon-resource install. Skipping icon installation.")
            return False
            
        logger.info(f"Installing icon '{icon_path}' with name '{icon_name}' (type: {icon_ext}, size hint: {size or 'default'}) using xdg-icon-resource...")
        
        # Build command, omitting --size if empty
        command = ["xdg-icon-resource", "install"]
        if size:
            command.extend(["--size", size])
        command.extend(["--novendor", icon_path, f'{icon_name}']) 
        
        # --->>> Execute Command <<<---
        logger.debug(f"Executing xdg-icon-resource command: {' '.join(command)}") # Log the command
        result = subprocess.run(command, check=True, capture_output=True, text=True)
        logger.info("xdg-icon-resource completed successfully.")
        # Cache is usually updated automatically by xdg-icon-resource, but update explicitly just in case.
        update_icon_cache() 
        return True
    except subprocess.CalledProcessError as e:
        logger.error(f"xdg-icon-resource failed: {e}")
        logger.error(f"Command output: {e.stderr}")
        return False
    except Exception as e:
        logger.error(f"Unexpected error installing icon with xdg-icon-resource: {e}")
        return False

def _update_desktop_file_content(desktop_file_path, exec_target, icon_name_or_path):
    """Internal helper to update Exec= and Icon= lines of a given desktop file."""
    if not desktop_file_path or not os.path.exists(desktop_file_path):
        logger.error(f"Cannot update desktop file: {desktop_file_path} does not exist")
        return False
        
    try:
        logger.info(f"Updating desktop file content at {desktop_file_path}")
        MARKER_COMMENT = "Managed by AppImage Manager"
        
        with open(desktop_file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
            
        updated = False
        comment_updated = False
        with open(desktop_file_path, 'w', encoding='utf-8') as f:
            in_desktop_entry_section = False
            for line in lines:
                strip_line = line.strip()
                if strip_line == '[Desktop Entry]':
                     in_desktop_entry_section = True
                     f.write(line) # Write the section header
                     continue
                elif strip_line.startswith('[') and strip_line.endswith(']'):
                     # Write out the marker comment *before* the next section if not already done
                     if in_desktop_entry_section and not comment_updated:
                          f.write(f"Comment={MARKER_COMMENT}\n")
                          logger.debug(f"Added marker comment: Comment={MARKER_COMMENT}")
                          comment_updated = True
                          updated = True
                     in_desktop_entry_section = False
                     f.write(line)
                     continue
                     
                if not in_desktop_entry_section:
                     f.write(line) # Write lines outside the target section as is
                     continue

                # Process lines within [Desktop Entry]
                if strip_line.startswith("Exec="):
                    if exec_target:
                        new_line = f"Exec={exec_target}\n"
                        f.write(new_line)
                        logger.debug(f"Updated Exec line: '{strip_line}' -> '{new_line.strip()}'")
                        updated = True
                    else:
                        f.write(line) # Keep original if no target
                elif strip_line.startswith("Icon="):
                    if icon_name_or_path:
                         new_line = f"Icon={icon_name_or_path}\n"
                         f.write(new_line)
                         logger.debug(f"Updated Icon line: '{strip_line}' -> '{new_line.strip()}'")
                         updated = True
                    else:
                         f.write(line) # Keep original if no icon
                elif strip_line.startswith("Comment="):
                     # Overwrite existing comment with our marker
                     new_line = f"Comment={MARKER_COMMENT}\n"
                     f.write(new_line)
                     logger.debug(f"Updated Comment line: '{strip_line}' -> '{new_line.strip()}'")
                     comment_updated = True # Mark comment as handled
                     updated = True 
                else:
                    f.write(line)
            
            # Add marker comment if section ended without finding one
            if in_desktop_entry_section and not comment_updated:
                f.write(f"Comment={MARKER_COMMENT}\n")
                logger.debug(f"Added marker comment at end of section: Comment={MARKER_COMMENT}")
                comment_updated = True
                updated = True
                    
        if updated:
            logger.info(f"Successfully updated desktop file: {desktop_file_path}")
        else:
            logger.info(f"No changes made to desktop file: {desktop_file_path}")
        return True
    except Exception as e:
        logger.error(f"Error updating desktop file {desktop_file_path}: {e}")
        logger.error(traceback.format_exc())
        return False

def register_appimage_integration(appimage_path, app_info, extracted_icon_path=None):
    """Creates symlink and desktop file for a registered AppImage.

    Args:
        appimage_path (str): The full path to the original AppImage.
        app_info (dict): Dictionary containing app metadata (name, version, icon_name etc.).
        extracted_icon_path (str, optional): Path to an icon file extracted from the AppImage.
                                            Defaults to None.
                                            
    Returns:
        tuple: (path_to_symlink_or_None, path_to_desktop_file_or_None)
    """
    bin_link_path = None
    desktop_file_path = None
    icon_name = None # This will be the name used in the .desktop file
    
    try:
        # --- Determine names and paths --- 
        app_name = app_info.get('name') or os.path.basename(appimage_path).replace('.AppImage','').replace('.appimage','')
        sanitized_app_name = sanitize_name(app_name) 
        if not sanitized_app_name:
            raise ValueError("Could not determine a valid sanitized name for the application.")
        
        # Determine icon name (use provided, fallback to sanitized app name)
        icon_name = app_info.get('icon_name') or sanitized_app_name

        # --- Install Icon if provided ---
        logger.debug(f"Icon Installation Check: AppName='{app_name}', Sanitized='{sanitized_app_name}', IconName='{icon_name}', ExtractedPath='{extracted_icon_path}'")
        if extracted_icon_path and os.path.exists(extracted_icon_path):
            logger.info("Attempting to install extracted icon file...")
            if not install_icon_with_xdg(extracted_icon_path, icon_name):
                logger.warning("Failed to install extracted icon file using xdg-icon-resource. Desktop entry might use a generic icon.")
        else:
             logger.debug("No extracted icon path provided or file does not exist, skipping icon installation.")

        # --- Create Executable Symlink --- 
        bin_link_dir = os.path.join(config.USER_HOME, ".local/bin")
        os.makedirs(bin_link_dir, exist_ok=True)
        bin_link_path = os.path.join(bin_link_dir, sanitized_app_name)
        
        logger.debug(f"Creating registration symlink: {bin_link_path} -> {appimage_path}")
        if os.path.lexists(bin_link_path):
            os.remove(bin_link_path) # Remove old link if it exists
        os.symlink(appimage_path, bin_link_path)
        logger.info(f"Created symlink: {bin_link_path}")
        
        # --- Create Desktop File --- 
        desktop_link_dir = os.path.join(config.USER_HOME, ".local/share/applications")
        os.makedirs(desktop_link_dir, exist_ok=True)
        # Use a unique name convention, e.g., appimagekit_<sanitized_name>.desktop
        desktop_filename = f"appimagekit_{sanitized_app_name}.desktop"
        desktop_file_path = os.path.join(desktop_link_dir, desktop_filename)
        
        logger.debug(f"Creating registration desktop file: {desktop_file_path}")
        
        # Basic .desktop file content
        desktop_content = f"""[Desktop Entry]
Version=1.1
Type=Application
Name={app_name}
Comment={app_info.get('comment', '')}
Exec={bin_link_path} %U
Icon={icon_name}
Categories={app_info.get('categories', 'Utility;')}
Terminal=false
StartupNotify=true
# Managed by AppImage Manager
"""
        with open(desktop_file_path, 'w', encoding='utf-8') as f:
            f.write(desktop_content)
            
        # Make desktop file executable? Usually not needed, but some environments might prefer it.
        os.chmod(desktop_file_path, 0o664) # Owner rw, group rw, others r
        logger.info(f"Created desktop file: {desktop_file_path}")

        # Update desktop database
        update_desktop_database(desktop_link_dir)
        
    except Exception as e:
        logger.error(f"Error during AppImage registration: {e}", exc_info=True)
        # Attempt partial cleanup
        if bin_link_path and os.path.lexists(bin_link_path):
            try: os.remove(bin_link_path) 
            except OSError: pass
        if desktop_file_path and os.path.exists(desktop_file_path):
            try: remove_desktop_entry(desktop_file_path) # Use existing remove function
            except OSError: pass
        # Return None if error occurred
        return None, None
        
    return bin_link_path, desktop_file_path

def create_desktop_entry(final_desktop_path, desktop_link_dir, bin_symlink_target, icon_name_or_path):
    """Copies the original .desktop file and updates its content.
    
    Args:
        final_desktop_path (str): Path to the original desktop file in the install dir.
        desktop_link_dir (str): Target directory (e.g., ~/.local/share/applications).
        bin_symlink_target (str): The target path for the Exec= line.
        icon_name_or_path (str): The icon name or path for the Icon= line.

    Returns:
        str: Path to the created/updated desktop file in the target directory, or None on failure.
    """
    target_desktop_path = None
    
    if not final_desktop_path or not os.path.exists(final_desktop_path):
        logger.warning("Desktop file integration skipped: Original desktop file path not found or invalid.")
        return None
        
    if not desktop_link_dir or not bin_symlink_target:
         logger.error("Cannot create desktop entry: Missing target directory or executable target path.")
         return None
         
    desktop_filename = os.path.basename(final_desktop_path)
    target_desktop_path = os.path.join(desktop_link_dir, desktop_filename)
    
    try:
        # Ensure target directory exists
        os.makedirs(desktop_link_dir, exist_ok=True)
        
        # Remove existing file/link first
        if os.path.lexists(target_desktop_path):
             logger.debug(f"Removing existing desktop file/link: {target_desktop_path}")
             os.remove(target_desktop_path)
        
        # Copy the original desktop file
        logger.debug(f"Copying desktop file: {final_desktop_path} -> {target_desktop_path}")
        shutil.copy2(final_desktop_path, target_desktop_path)
        logger.info(f"Desktop file copied to: {target_desktop_path}")
        
        # Update the COPIED desktop file
        if not _update_desktop_file_content(target_desktop_path, bin_symlink_target, icon_name_or_path):
            logger.error("Failed to update the copied desktop file content.")
            # Return the path anyway, it might partially work
        
        # Update desktop database after copy/update
        update_desktop_database(desktop_link_dir)
        
    except (OSError, PermissionError, shutil.Error) as e:
         logger.error(f"Desktop file copy/update failed: {e}")
         return None # Return None on error
         
    return target_desktop_path # Return path to the new/updated file
    
def remove_desktop_entry(desktop_file_path):
     """Removes a desktop entry file and updates the database."""
     if not desktop_file_path or not os.path.exists(desktop_file_path):
          logger.debug(f"Desktop file not found (already removed?): {desktop_file_path}")
          return False
          
     try:
          desktop_dir = os.path.dirname(desktop_file_path)
          os.remove(desktop_file_path)
          logger.info(f"Removed desktop file: {desktop_file_path}")
          update_desktop_database(desktop_dir)
          return True
     except (OSError, PermissionError) as e:
          logger.error(f"Failed to remove desktop file {desktop_file_path}: {e}")
          return False
          
def remove_installed_icons(icon_name, app_name):
     """Removes icons associated with an app from standard user locations."""
     if not icon_name:
          icon_name = sanitize_name(app_name)
     if not icon_name:
          logger.warning("Cannot remove icons: No icon name or app name available.")
          return False
          
     logger.info(f"Attempting to remove icons matching base name: {icon_name}")
     standard_icon_base_dir = os.path.join(config.USER_HOME, ".local/share/icons/hicolor")
     icon_sizes = ["16x16", "22x22", "24x24", "32x32", "48x48", "64x64", "128x128", "256x256", "512x512", "scalable"]
     icon_exts = [".png", ".svg", ".svgz"] # Add other relevant extensions if needed
     icons_removed = False
     
     for size in icon_sizes:
         size_dir = os.path.join(standard_icon_base_dir, size, "apps")
         if not os.path.isdir(size_dir):
             continue
         for ext in icon_exts:
             icon_path_to_remove = os.path.join(size_dir, f"{icon_name}{ext}")
             if os.path.exists(icon_path_to_remove):
                 try:
                     os.remove(icon_path_to_remove)
                     logger.info(f"Removed installed icon: {icon_path_to_remove}")
                     icons_removed = True
                 except OSError as e:
                     logger.error(f"Failed to remove icon {icon_path_to_remove}: {e}")
                     
     # Update icon cache if we removed any icons
     if icons_removed:
         update_icon_cache(standard_icon_base_dir)
         
     return icons_removed # Indicate if any action was taken 

def unregister_appimage_integration(bin_link_path, desktop_file_path):
    """Removes the symlink and .desktop file created during registration."""
    success = True
    
    # Remove desktop file
    if desktop_file_path and os.path.lexists(desktop_file_path):
        try:
            desktop_dir = os.path.dirname(desktop_file_path)
            os.remove(desktop_file_path)
            logger.info(f"Removed registration desktop file: {desktop_file_path}")
            update_desktop_database(desktop_dir) # Update after removal
        except (OSError, PermissionError) as e:
            logger.error(f"Failed to remove registration desktop file {desktop_file_path}: {e}")
            success = False
    
    # Remove bin symlink
    if bin_link_path and os.path.lexists(bin_link_path):
        try:
            os.remove(bin_link_path)
            logger.info(f"Removed registration symlink: {bin_link_path}")
        except (OSError, PermissionError) as e:
            logger.error(f"Failed to remove registration symlink {bin_link_path}: {e}")
            success = False
            
    return success 