import os
import shutil
import logging
import errno

from . import config
from . import integration

logger = logging.getLogger(__name__)

class AppImageUninstaller:
    def __init__(self, app_info):
        """Initializes the uninstaller with application information from the database."""
        logger.debug(f"Initializing AppImageUninstaller for app: {app_info.get('name', 'Unknown')}")
        if not app_info or not isinstance(app_info, dict):
            raise ValueError("Valid app_info dictionary is required for uninstallation.")
        
        self.app_info = app_info
        self.requires_root = app_info.get('requires_root', self._check_root_requirement_heuristic())
        logger.debug(f"Uninstaller initialized. Requires root: {self.requires_root}")

    def _check_root_requirement_heuristic(self):
        """Determines if root privileges are *likely* needed based on paths."""
        install_path = self.app_info.get("install_path", "")
        exec_symlink = self.app_info.get("executable_symlink", "")
        desktop_file = self.app_info.get("desktop_file_path", "")

        system_prefixes = ["/opt", "/usr/local", "/etc", "/usr/share"] 
        if any(p and any(p.startswith(prefix) for prefix in system_prefixes) 
               for p in [install_path, exec_symlink, desktop_file]):
            logger.info("Root likely required based on system path prefix found in app_info.")
            return True
            
        if self.app_info.get('install_mode') == 'system':
            logger.info("Root required based on 'system' install mode in app_info.")
            return True
                 
        logger.debug("Root not obviously required based on heuristic path checks.")
        return False

    def uninstall(self):
        """Runs the non-root uninstallation process (removing user files/links)."""
        if self.requires_root:
            logger.error("Uninstall (non-root) called, but installation requires root. Aborting non-root attempt.")
            return False
            
        app_name = self.app_info.get('name', 'Unknown App')
        logger.info(f"Uninstalling '{app_name}' (non-root)...") 
        success = True 

        desktop_file_path = self.app_info.get("desktop_file_path")
        if desktop_file_path:
            logger.debug(f"Removing desktop entry: {desktop_file_path}")
            if not integration.remove_desktop_entry(desktop_file_path):
                 logger.warning(f"Desktop file '{desktop_file_path}' could not be removed (or was already gone).")
        else:
            logger.debug("Desktop entry removal skipped: Path not found in app_info.")

        icon_name = self.app_info.get("icon_name") 
        app_name_fallback = self.app_info.get("name") 
        if icon_name or app_name_fallback:
            name_to_use = icon_name if icon_name else app_name_fallback
            logger.debug(f"Removing installed icons for base name: {name_to_use}")
            if not integration.remove_installed_icons(icon_name, app_name_fallback):
                 logger.warning(f"Icons for '{name_to_use}' could not be removed (or were already gone).")
        else:
             logger.debug("Icon removal skipped: No icon or app name found in app_info.")

        exec_symlink = self.app_info.get("executable_symlink")
        if exec_symlink: 
            if os.path.lexists(exec_symlink): 
                try:
                    os.remove(exec_symlink)
                    logger.info(f"Removed executable symlink: {exec_symlink}")
                except (OSError, PermissionError) as e:
                    logger.error(f"Failed to remove executable symlink '{exec_symlink}': {e}")
                    success = False 
            else:
                 logger.debug(f"Executable symlink removal skipped: Path '{exec_symlink}' does not exist.")
        else:
             logger.debug("Executable symlink removal skipped: Path not found in app_info.")

        # --- Remove installation directory OR copied AppImage file --- 
        install_path = self.app_info.get("install_path")
        mgmt_type = self.app_info.get('management_type')
        
        if mgmt_type == config.MGMT_TYPE_REGISTERED:
            # This is now the "Add to Library (Copy)" type
            # install_path points to the copied AppImage file
            if install_path and os.path.isfile(install_path):
                 logger.debug(f"Removing copied AppImage file: {install_path}")
                 try:
                     os.remove(install_path)
                     logger.info(f"Removed copied AppImage file: {install_path}")
                 except (OSError, PermissionError) as e:
                     logger.error(f"Failed to remove copied AppImage file '{install_path}': {e}")
                     success = False
            elif install_path:
                 logger.warning(f"Copied AppImage removal skipped: Path '{install_path}' is not a file or does not exist.")
            else:
                 logger.warning("Copied AppImage removal skipped: Path not found in app_info.")
                 
        elif mgmt_type == config.MGMT_TYPE_INSTALLED:
            # This is a fully installed app, remove the directory
            if install_path and os.path.isdir(install_path): 
                logger.debug(f"Removing installation directory: {install_path}")
                try:
                    shutil.rmtree(install_path)
                    logger.info(f"Removed installation directory: {install_path}")
                except (OSError, PermissionError) as e:
                    logger.error(f"Failed to remove installation directory '{install_path}': {e}")
                    success = False 
            elif install_path:
                logger.debug(f"Installation directory removal skipped: Path '{install_path}' is not a directory or does not exist.")
            else:
                logger.debug("Installation directory removal skipped: Path not found in app_info.")
        else:
            logger.warning(f"Unknown management type '{mgmt_type}', skipping removal of install path '{install_path}'")

        # --- Remove User Config/Cache (Optional, heuristic) --- 
        # Consider adding this later if desired
        # self._remove_heuristic_user_data(app_name)

        if success:
            logger.info(f"'{app_name}' uninstalled successfully (non-root).")
        else:
            logger.warning(f"Some errors occurred during uninstall of '{app_name}' (non-root). Check logs.")
            
        return success 

    def get_uninstall_commands(self):
        """Generates shell commands needed for root uninstallation."""
        if not self.requires_root:
            logger.debug("get_uninstall_commands called for non-root install, returning empty list.")
            return []
            
        commands = []
        app_name = self.app_info.get('name', 'Unknown App')
        logger.info(f"Generating root uninstall commands for '{app_name}'.")
        
        install_path = self.app_info.get("install_path")
        exec_symlink = self.app_info.get("executable_symlink")
        desktop_file_path = self.app_info.get("desktop_file_path")
        icon_name = self.app_info.get("icon_name")
        
        if install_path and any(install_path.startswith(p) for p in ["/opt", "/usr/local", "/etc"]):
            commands.append(f"rm -rf \"{install_path}\"")
        elif install_path:
             logger.warning(f"Install path '{install_path}' does not seem like a system path, skipping rm command for root uninstall.")

        if exec_symlink and any(exec_symlink.startswith(p) for p in ["/usr/local/bin", "/usr/bin", "/bin", "/opt/bin"]):
            commands.append(f"rm -f \"{exec_symlink}\"")
        elif exec_symlink:
             logger.warning(f"Executable symlink '{exec_symlink}' does not seem like a system path, skipping rm command for root uninstall.")
             
        if desktop_file_path and any(desktop_file_path.startswith(p) for p in ["/usr/local/share/applications", "/usr/share/applications"]):
             commands.append(f"rm -f \"{desktop_file_path}\"")
             desktop_dir = os.path.dirname(desktop_file_path)
             commands.append(f"update-desktop-database \"{desktop_dir}\" || true") 
        elif desktop_file_path:
             logger.warning(f"Desktop file path '{desktop_file_path}' does not seem like a system path, skipping rm command for root uninstall.")

        if icon_name:
             system_icon_base_dir = "/usr/share/icons/hicolor" 
             icon_sizes = ["16x16", "22x22", "24x24", "32x32", "48x48", "64x64", "128x128", "256x256", "512x512", "scalable"]
             icon_exts = [".png", ".svg", ".svgz"]
             for size in icon_sizes:
                 for ext in icon_exts:
                     potential_icon_path = os.path.join(system_icon_base_dir, size, "apps", f"{icon_name}{ext}")
                     commands.append(f"rm -f \"{potential_icon_path}\"")
             commands.append(f"gtk-update-icon-cache -f -t \"{system_icon_base_dir}\" || true") 
        else:
             logger.warning("Cannot generate system icon removal commands: Icon name missing.")
             
        logger.info(f"Generated {len(commands)} root uninstall commands.")
        return commands 