import time
from pathlib import Path
import os
import shutil
import logging
import tempfile
import subprocess
import configparser
import uuid
import re
import datetime

from . import config
from . import integration
from .utils import sanitize_name

logger = logging.getLogger(__name__)

def _run_subprocess_non_blocking(cmd, cwd=None, timeout=60, env=None, check_interval=0.1):
    """Run a subprocess without blocking the UI thread.
    
    Uses Popen with polling and QApplication.processEvents() to keep UI responsive
    during long-running operations like AppImage extraction.
    
    Args:
        cmd: Command list to execute
        cwd: Working directory
        timeout: Maximum time to wait (seconds)
        env: Environment variables
        check_interval: How often to check process status (seconds)
        
    Returns:
        tuple: (return_code, stdout, stderr) or (None, None, error_msg) on timeout
    """
    try:
        # Try to import QApplication for UI responsiveness
        from PyQt6.QtWidgets import QApplication
        has_qt = True
    except ImportError:
        has_qt = False
    
    try:
        process = subprocess.Popen(
            cmd,
            cwd=cwd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=env
        )
        
        start_time = time.time()
        while True:
            # Check if process has completed
            return_code = process.poll()
            if return_code is not None:
                # Process completed
                stdout, stderr = process.communicate()
                return return_code, stdout.decode('utf-8', errors='replace'), stderr.decode('utf-8', errors='replace')
            
            # Check timeout
            elapsed = time.time() - start_time
            if elapsed > timeout:
                process.kill()
                process.wait()
                return None, None, f"Process timed out after {timeout}s"
            
            # Keep UI responsive
            if has_qt:
                app = QApplication.instance()
                if app:
                    app.processEvents()
            
            # Small sleep to avoid busy-waiting
            time.sleep(check_interval)
            
    except Exception as e:
        return None, None, str(e)

class AppImageInstaller:
    def __init__(self, appimage_path, install_mode="user", custom_install_path=None):
        logger.debug(f"Entering __init__ for {appimage_path}, mode={install_mode}, custom_path={custom_install_path}")
        # --- Basic Initialization ---
        self.appimage_path = appimage_path
        if not appimage_path or not os.path.isfile(self.appimage_path):
            raise FileNotFoundError(f"AppImage file not found or invalid: {appimage_path}")
            
        self.install_mode = install_mode
        self.custom_install_path = custom_install_path
        self.requires_root = (install_mode == "system")
        self.app_info = {} # Initialize app_info dictionary
        self.extract_dir = None # Directory where AppImage is extracted
        self.temp_dir = None # General temporary directory for quick extracts
        self.temp_files = [] # List to track temporary files/dirs for cleanup
        self.extracted_desktop_path = None # Path to the desktop file found during extraction
        self.final_executable_path = None
        self.final_desktop_path = None
        self.final_icon_path = None
        self.temp_preview_icon_path = None # Path to temporarily extracted icon for preview
        self.symlinks_created = [] # Track created symlinks (mainly for non-root removal)
        self.bin_symlink_target = None # Initialize symlink target
        self.final_copied_desktop_path = None # Initialize path for created desktop file

        logger.debug(f"Initializing AppImageInstaller for '{self.appimage_path}'...")

        # --- Determine Base Paths --- 
        self._determine_base_paths()
        
        # --- Check root requirement based on determined paths (can be preliminary) ---
        self._check_root_requirement_based_on_paths()

        logger.debug(f"AppImageInstaller initialized for '{self.appimage_path}'. Mode: {self.install_mode}")
        logger.debug(f"Exiting __init__")

    def _determine_base_paths(self):
        """Determines base installation prefix and link directories based on mode."""
        if self.install_mode == "system":
            self.base_install_prefix = config.SYSTEM_INSTALL_DIR
            self.bin_link_dir = config.SYSTEM_BIN_DIR
            self.desktop_link_dir = config.SYSTEM_DESKTOP_DIR
        elif self.install_mode == "custom":
            if not self.custom_install_path:
                raise ValueError("Custom install path is required for custom mode.")
            self.base_install_prefix = self.custom_install_path 
            self.bin_link_dir = os.path.join(config.USER_HOME, ".local/bin")
            self.desktop_link_dir = os.path.join(config.USER_HOME, ".local/share/applications")
        else: # User mode
            self.base_install_prefix = os.path.join(config.USER_HOME, ".local/share", config.APP_DIR_NAME) 
            self.bin_link_dir = os.path.join(config.USER_HOME, ".local/bin")
            self.desktop_link_dir = os.path.join(config.USER_HOME, ".local/share/applications")
        logger.debug(f"Base install prefix: {self.base_install_prefix}")
        logger.debug(f"Bin link dir: {self.bin_link_dir}")
        logger.debug(f"Desktop link dir: {self.desktop_link_dir}")
    
    def _extract_initial_metadata(self):
        """Extracts basic metadata (.desktop file) without full extraction."""
        logger.info(f"Extracting initial metadata from {self.appimage_path}")
        metadata = {}
        self._ensure_temp_dir() 
        extract_meta_dir = os.path.join(self.temp_dir, "meta_extract")
        if os.path.exists(extract_meta_dir): shutil.rmtree(extract_meta_dir)
        os.makedirs(extract_meta_dir)
        self.temp_files.append(extract_meta_dir)

        try:
            extract_command = [self.appimage_path, f"--appimage-extract=*.desktop"]
            # Create environment that prevents AppImage from launching GUI
            extract_env = os.environ.copy()
            extract_env["APPIMAGE_EXTRACT_AND_RUN"] = "0"
            extract_env["NO_CLEANUP"] = "1"
            extract_env.pop("DISPLAY", None)  # Remove DISPLAY to prevent GUI launch
            extract_env.pop("WAYLAND_DISPLAY", None)  # Also remove Wayland display
            result = subprocess.run(extract_command, cwd=extract_meta_dir, check=False, 
                                   capture_output=True, text=True, timeout=15, env=extract_env)

            if result.returncode == 0:
                squashfs_root = os.path.join(extract_meta_dir, "squashfs-root")
                if os.path.isdir(squashfs_root):
                    found_desktop = None
                    for root, _, files in os.walk(squashfs_root):
                        for file in files:
                            if file.lower().endswith(".desktop"):
                                found_desktop = os.path.join(root, file)
                                logger.debug(f"Found potential desktop file: {found_desktop}")
                                break # Inner loop
                        if found_desktop: break # Outer loop
                        
                    if found_desktop:
                        self.extracted_desktop_path = found_desktop 
                        metadata = self._parse_desktop_file(found_desktop)
                    else: 
                        logger.warning("Could not find .desktop file after extraction.")
                else: 
                    logger.warning("Extraction command succeeded but squashfs-root not found in meta_extract.")
            else: 
                stderr_output = result.stderr.strip() if result.stderr else ""
                log_msg = f"Failed to extract .desktop file (Code: {result.returncode})"
                if stderr_output and "No such file" not in stderr_output:
                    log_msg += f": {stderr_output}"
                logger.error(log_msg)

        except (subprocess.TimeoutExpired, Exception) as e:
            logger.error(f"Error during initial metadata extraction: {e}")
            
        return metadata

    def _parse_desktop_file(self, desktop_file_path):
        """Parses a .desktop file and returns key information."""
        parser = configparser.ConfigParser(interpolation=None)
        parser.optionxform = str 
        data = {"name": None, "version": None, "icon_name": None, "exec": None, "exec_relative": None}
        try:
            parser.read(desktop_file_path, encoding='utf-8')
            if 'Desktop Entry' in parser:
                entry = parser['Desktop Entry']
                data['name'] = entry.get("Name")
                data['version'] = entry.get("X-AppImage-Version", entry.get("Version")) 
                data['icon_name'] = entry.get("Icon")
                data['exec'] = entry.get("Exec")
                if data['exec']:
                    if '/' not in data['exec']:
                        data['exec_relative'] = data['exec']
                    else:
                        parts = data['exec'].split('/')
                        if len(parts) > 1 and parts[0] in ['.', 'usr']:
                            data['exec_relative'] = '/'.join(parts[1:]) if parts[0]=='.' else '/'.join(parts)
                        else:
                            data['exec_relative'] = data['exec'] 
                
                # Add sanitized name directly
                if data['name']:
                    data['name_sanitized'] = sanitize_name(data['name'])
                
                logger.debug(f"Parsed desktop entry: Name='{data['name']}', Version='{data['version']}', Icon='{data['icon_name']}', Exec='{data['exec']}', ExecRel='{data['exec_relative']}'")
            else:
                logger.warning(f"Could not find [Desktop Entry] section in {desktop_file_path}")
        except Exception as e:
            logger.error(f"Error parsing desktop file {desktop_file_path}: {e}")
        return data

    def _get_app_specific_install_dir(self):
        """Determines the specific installation directory based on app name.
           Uses sanitized name and a cleaned version string.
        """
        app_name = self.app_info.get('name')
        if not app_name:
            logger.error("Cannot determine app-specific dir: App name is missing from app_info.")
            return None 

        sanitized_app_name = sanitize_name(app_name) 
        if not sanitized_app_name:
            logger.error("Cannot determine app-specific dir: Sanitized app name is empty.")
            return None # Or use a fallback?
            
        version_raw = self.app_info.get('version')
        cleaned_version = "unknown" # Default
        if version_raw:
            # Simple cleaning for version: replace known problematic chars with underscore
            # Keep dots, allow alphanumeric, underscore, hyphen.
            cleaned_version = re.sub(r'[^a-zA-Z0-9_\-\.]', '_', str(version_raw))
            cleaned_version = cleaned_version.strip('_-') # Remove leading/trailing separators
            if not cleaned_version: # Handle case where cleaning results in empty string
                cleaned_version = "unknown"
        
        # Use lowercase for consistency, handle "unknown"
        version_part = cleaned_version.lower()
        
        # Construct directory name
        if version_part != 'unknown':
             dir_name = f"{sanitized_app_name}_{version_part}"
        else:
             dir_name = sanitized_app_name
        
        if not self.base_install_prefix:
            logger.error("Cannot determine app-specific dir: base_install_prefix not set.")
            return None
            
        final_path = os.path.join(self.base_install_prefix, dir_name)
        logger.debug(f"Determined app specific install dir: {final_path} (Name: '{sanitized_app_name}', Version: '{version_part}')")
        return final_path
         
    def _determine_final_paths_placeholder(self):
        """Calculates the target symlink path (used before full install/extraction)."""
        self.bin_symlink_target = None
        app_name = self.app_info.get('name')
        if app_name and self.bin_link_dir:
            sanitized = sanitize_name(app_name)
            if sanitized:
                self.bin_symlink_target = os.path.join(self.bin_link_dir, sanitized)
                logger.debug(f"Determined preliminary bin symlink target: {self.bin_symlink_target}")
            else:
                logger.warning(f"Could not determine preliminary bin symlink target (sanitized name is empty for '{app_name}').")
        else:
            logger.warning("Could not determine preliminary bin symlink target (missing app name or bin_link_dir).")
            
    def _determine_final_paths(self):
        """Determines the final installation paths based on metadata and selected mode."""
        if not self.app_install_dir:
            logger.error("Cannot determine final paths: Install directory not set.")
            self.final_executable_path = None
            self.final_desktop_path = None
            return

        if not self.app_info or 'exec_relative' not in self.app_info:
            logger.error("Cannot determine final executable path: Metadata (exec_relative) missing.")
            self.final_executable_path = None
        else:
            # Look for the executable in different possible locations
            exec_relative = self.app_info['exec_relative']
            app_name_sanitized = self.app_info.get('name_sanitized', '').lower()
            
            # Possible paths for executable (in priority order):
            # 1. In usr/bin (common structure for traditional AppImages)
            usr_bin_path = os.path.join(self.app_install_dir, "usr/bin", exec_relative)
            
            # 2. In app/ directory (common for Electron apps)
            app_dir_path = os.path.join(self.app_install_dir, "app", app_name_sanitized) if app_name_sanitized else None
            
            # 3. Direct in app dir (legacy support - AppRun)
            direct_path = os.path.join(self.app_install_dir, exec_relative)
            
            # 4. Check for AppRun.wrapped which might point to the correct executable
            apprun_wrapped_path = os.path.join(self.app_install_dir, "AppRun.wrapped")
            
            # Helper function to check if a file is a real executable binary (not a shell script for desktop integration)
            def is_real_executable(path):
                if not path or not os.path.exists(path) or not os.path.isfile(path):
                    return False
                # Check if it's executable
                if not os.access(path, os.X_OK):
                    return False
                # Check if it's a shell script (AppRun integration scripts often are)
                try:
                    with open(path, 'rb') as f:
                        header = f.read(128)
                        # Check for shell script shebang
                        if header.startswith(b'#!/'):
                            # This is likely a shell script, check if it's an integration script
                            if b'desktop' in header.lower() or b'appimage' in header.lower():
                                return False  # Skip integration scripts
                        # ELF binary
                        if header.startswith(b'\x7fELF'):
                            return True
                        # Could be a script that actually runs the app
                        return True
                except (IOError, OSError):
                    return False
                return True
            
            # Decide which path to use by checking existence
            self.final_executable_path = None
            
            if os.path.exists(self.app_install_dir):
                # Priority 1: Check usr/bin
                if os.path.exists(usr_bin_path) and is_real_executable(usr_bin_path):
                    self.final_executable_path = usr_bin_path
                    logger.debug(f"Found executable in usr/bin: {self.final_executable_path}")
                
                # Priority 2: Check AppRun FIRST - this is the standard AppImage entry point
                # AppRun is a shell script or symlink that sets up the environment properly
                elif os.path.exists(direct_path) and os.access(direct_path, os.X_OK):
                    self.final_executable_path = direct_path
                    logger.debug(f"Found AppRun executable: {self.final_executable_path}")
                
                # Priority 3: Check AppRun.wrapped symlink (some AppImages use this pattern)
                elif os.path.islink(apprun_wrapped_path):
                    try:
                        wrapped_target = os.readlink(apprun_wrapped_path)
                        target_path = os.path.normpath(os.path.join(self.app_install_dir, wrapped_target))
                        if os.path.exists(target_path) and is_real_executable(target_path):
                            self.final_executable_path = target_path
                            logger.debug(f"Found executable via AppRun.wrapped symlink: {self.final_executable_path}")
                    except (OSError, IOError) as e:
                        logger.warning(f"Failed to read AppRun.wrapped symlink: {e}")
                
                # Priority 4: Check app/ directory for main binary (Electron apps)
                # Skip .so files as they are shared libraries, not executables
                elif app_dir_path and os.path.exists(app_dir_path) and is_real_executable(app_dir_path):
                    self.final_executable_path = app_dir_path
                    logger.debug(f"Found executable in app/ (Electron): {self.final_executable_path}")
                
                # Priority 5: Search app/ directory for any executable matching app name
                # But skip shared libraries (.so files)
                elif os.path.isdir(os.path.join(self.app_install_dir, "app")):
                    app_subdir = os.path.join(self.app_install_dir, "app")
                    for item in os.listdir(app_subdir):
                        # Skip shared libraries
                        if item.endswith('.so') or '.so.' in item:
                            continue
                        item_path = os.path.join(app_subdir, item)
                        if os.path.isfile(item_path) and is_real_executable(item_path):
                            # Check if the name matches approximately
                            item_lower = item.lower()
                            if app_name_sanitized and (app_name_sanitized in item_lower or item_lower in app_name_sanitized):
                                self.final_executable_path = item_path
                                logger.debug(f"Found executable in app/ by name match: {self.final_executable_path}")
                                break
                            # Or just take the first real ELF binary found in app/ (not a .so)
                            try:
                                with open(item_path, 'rb') as f:
                                    if f.read(4) == b'\x7fELF':
                                        self.final_executable_path = item_path
                                        logger.debug(f"Found ELF executable in app/: {self.final_executable_path}")
                                        break
                            except (IOError, OSError):
                                pass
            
            # Fallback: If nothing found and directory doesn't exist yet (new installation)
            if not self.final_executable_path:
                # For new installations, try to determine based on app structure in extract_dir
                if self.extract_dir and os.path.isdir(self.extract_dir):
                    # First check for AppRun in extract_dir
                    extract_apprun = os.path.join(self.extract_dir, "AppRun")
                    if os.path.exists(extract_apprun) and os.access(extract_apprun, os.X_OK):
                        self.final_executable_path = os.path.join(self.app_install_dir, "AppRun")
                        logger.debug(f"Determined AppRun from extract: {self.final_executable_path}")
                    # Check extract_dir for app/ structure (fallback)
                    elif os.path.isdir(os.path.join(self.extract_dir, "app")):
                        extract_app_dir = os.path.join(self.extract_dir, "app")
                        for item in os.listdir(extract_app_dir):
                            # Skip shared libraries
                            if item.endswith('.so') or '.so.' in item:
                                continue
                            item_path = os.path.join(extract_app_dir, item)
                            if os.path.isfile(item_path) and is_real_executable(item_path):
                                # Use the relative path from install dir
                                self.final_executable_path = os.path.join(self.app_install_dir, "app", item)
                                logger.debug(f"Determined executable from extract (app/): {self.final_executable_path}")
                                break
                
                # Ultimate fallback: usr/bin path
                if not self.final_executable_path:
                    self.final_executable_path = usr_bin_path
                    logger.debug(f"Using default usr/bin location for executable: {self.final_executable_path}")
            
            logger.debug(f"Calculated final executable path: {self.final_executable_path}")

        # Calculate expected desktop file path *within* the install directory
        desktop_filename = self._find_desktop_file_in_dir(self.app_install_dir, return_relative=True)
        if desktop_filename:
             # Use the actual relative path if found (e.g. after extraction to temp)
             self.final_desktop_path = os.path.join(self.app_install_dir, desktop_filename)
             logger.debug(f"Calculated final desktop path (found relative): {self.final_desktop_path}")
        elif self.extracted_desktop_path and self.extract_dir and self.extracted_desktop_path.startswith(self.extract_dir):
             # Fallback: If we have the path from a temp extraction, calculate relative from that
             try:
                  relative_desktop_path = os.path.relpath(self.extracted_desktop_path, self.extract_dir)
                  self.final_desktop_path = os.path.join(self.app_install_dir, relative_desktop_path)
                  logger.debug(f"Calculated final desktop path (from temp relative): {self.final_desktop_path}")
             except ValueError:
                  logger.warning("Could not determine relative desktop path from temp extraction.")
                  self.final_desktop_path = None
        else:
            # Fallback: Try common naming convention if no specific file found yet
            # This might happen if only metadata was read selectively
            app_name_sanitized = self.app_info.get('name_sanitized')
            if app_name_sanitized:
                 # Look for common patterns like appname.desktop, package.name.desktop etc.
                 # This is less reliable than finding the actual file during extraction
                 # For now, just log that we couldn't pinpoint it precisely yet
                 logger.warning(f"Could not precisely determine final desktop file path within {self.app_install_dir}. May rely on link target later.")
                 # We might still be able to create the link if name_sanitized is known
                 self.final_desktop_path = None # Mark as undetermined for now
            else:
                 logger.error("Cannot determine final desktop path: Metadata (name_sanitized) missing and file not found.")
                 self.final_desktop_path = None

        # Placeholder determination remains separate as it only needs the name
        self._determine_final_paths_placeholder()

        logger.debug(f"Post-extraction Info: Name='{self.app_info.get('name')}', InstallDir='{self.app_install_dir}', BinLink='{self.bin_symlink_target}', FinalExec='{self.final_executable_path}', FinalDesktop='{self.final_desktop_path}'")
        return True # Extraction successful

    def _find_desktop_file_in_dir(self, search_dir, return_relative=False):
        """Scans a directory for the first .desktop file found."""
        if not search_dir or not os.path.isdir(search_dir):
            logger.debug(f"_find_desktop_file_in_dir: Search directory invalid or doesn't exist: {search_dir}")
            return None

        logger.debug(f"Scanning for desktop file in: {search_dir}")
        for root, _, files in os.walk(search_dir):
            for file in files:
                if file.lower().endswith(".desktop"):
                    full_path = os.path.join(root, file)
                    logger.debug(f"Found desktop file: {full_path}")
                    if return_relative:
                        try:
                            relative_path = os.path.relpath(full_path, search_dir)
                            logger.debug(f"Returning relative path: {relative_path}")
                            return relative_path
                        except ValueError as e:
                            logger.warning(f"Could not get relative path for {full_path} from {search_dir}: {e}")
                            return None # Fallback if relpath fails
                    else:
                        logger.debug(f"Returning full path: {full_path}")
                        return full_path
        logger.debug(f"No desktop file found in {search_dir}")
        return None

    def _check_root_requirement_based_on_paths(self):
        """Checks if root is required based on target directories (relevant for system mode)."""
        if self.install_mode == "system":
            self.requires_root = True
            logger.info("Root required: System installation mode selected.")
        else:
            self.requires_root = False

    def extract_appimage(self):
        """Performs a full extraction of the AppImage to a temporary directory."""
        logger.debug(f"Entering extract_appimage for {self.appimage_path}")
        if not self.appimage_path or not os.path.exists(self.appimage_path): 
            logger.error("Cannot extract: AppImage path is invalid.")
            return False
        if not os.access(self.appimage_path, os.X_OK):
            try: 
                os.chmod(self.appimage_path, os.stat(self.appimage_path).st_mode | 0o111)
                logger.info(f"Made AppImage executable: {self.appimage_path}")
            except OSError as e:
                logger.error(f"Failed to make AppImage executable: {e}")
                return False 

        self._ensure_temp_dir()
        self.extract_dir = os.path.join(self.temp_dir, "squashfs-root")
        if os.path.exists(self.extract_dir):
            logger.info(f"Removing existing extraction directory: {self.extract_dir}")
            shutil.rmtree(self.extract_dir)

        logger.info(f"Starting full extraction of {self.appimage_path} to {self.extract_dir}...")
        try:
            extract_command = [self.appimage_path, "--appimage-extract"]
            logger.debug(f"Running command: {' '.join(extract_command)} in {self.temp_dir}")
            # Create environment that prevents AppImage from launching GUI
            extract_env = os.environ.copy()
            extract_env["APPIMAGE_EXTRACT_AND_RUN"] = "0"
            extract_env["NO_CLEANUP"] = "1"
            extract_env.pop("DISPLAY", None)  # Remove DISPLAY to prevent GUI launch
            extract_env.pop("WAYLAND_DISPLAY", None)  # Also remove Wayland display
            result = subprocess.run(extract_command, cwd=self.temp_dir, check=True, 
                                   capture_output=True, text=True, timeout=120, env=extract_env)
            
            if not os.path.isdir(self.extract_dir):
                logger.error(f"Extraction command succeeded but expected directory '{self.extract_dir}' not found.")
                return False
                 
            logger.info(f"Full extraction completed. RC={result.returncode}")
            logger.debug("Updating metadata and final paths after full extraction...")
            self._update_metadata_from_desktop_file()
            self.app_install_dir = self._get_app_specific_install_dir()
            self._determine_final_paths()
            self._determine_final_paths_placeholder()
            logger.debug(f"Post-extraction Info: Name='{self.app_info.get('name')}', InstallDir='{self.app_install_dir}', BinLink='{self.bin_symlink_target}', FinalExec='{self.final_executable_path}', FinalDesktop='{self.final_desktop_path}'")
            return True
            
        except Exception as e:
            logger.error(f"Failed during AppImage extraction or metadata update: {e}", exc_info=True)
            # Ensure cleanup happens even if extraction fails mid-way
            # self.cleanup() # Cleanup might be called by the caller, avoid double cleanup here unless necessary
            return False # Indicate failure
        # We need a finally block if self.cleanup() is called here, or ensure the except block covers all cases
        # Add a basic except block if try was the only issue

    def _update_metadata_from_desktop_file(self):
        """Finds and parses the .desktop file within the full extract_dir."""
        if not self.extract_dir or not os.path.isdir(self.extract_dir):
            logger.warning("Cannot update metadata: Extraction directory not found.")
            return 
            
        found_desktop = None
        for root, _, files in os.walk(self.extract_dir):
            for file in files:
                if file.lower().endswith(".desktop"):
                    found_desktop = os.path.join(root, file)
                    logger.debug(f"Found desktop file in full extraction: {found_desktop}")
                    break # Inner loop
            if found_desktop: 
                break # Outer loop

        if found_desktop:
            self.extracted_desktop_path = found_desktop 
            new_metadata = self._parse_desktop_file(found_desktop)
            logger.debug(f"Updating metadata from fully extracted desktop file. Old: {self.app_info}, New: {new_metadata}")
            for key, value in new_metadata.items():
                if value is not None:
                    self.app_info[key] = value
            
            # Ensure name_sanitized is set when name exists
            if 'name' in self.app_info and 'name_sanitized' not in self.app_info:
                self.app_info['name_sanitized'] = sanitize_name(self.app_info['name'])
                logger.debug(f"Added missing name_sanitized: {self.app_info['name_sanitized']}")
                
            logger.debug(f"Merged metadata: {self.app_info}")
        else: 
            logger.warning("Could not find .desktop file in the full extraction directory.")
            if not self.app_info.get('name'): 
                self._populate_fallback_metadata()
    
    def install_files(self):
        """Copies files from the temporary extraction dir to the final install dir (non-root only)."""
        logger.debug(f"Entering install_files. Source: {self.extract_dir}, Target: {self.app_install_dir}")
        if self.requires_root:
            logger.error("install_files should not be called for root installs (use get_install_commands).")
            return False
        if not self.extract_dir or not os.path.isdir(self.extract_dir):
            logger.error("Cannot install files: Extraction directory not found.")
            return False 
        if not self.app_install_dir:
            logger.error("Cannot install files: Target installation directory not set.")
            return False 
            
        source_dir_to_copy = self.extract_dir
        target_dir = self.app_install_dir
        logger.info(f"Copying files from {source_dir_to_copy} to {target_dir}")

        try:
            os.makedirs(target_dir, exist_ok=True)
            shutil.copytree(source_dir_to_copy, target_dir, symlinks=True, dirs_exist_ok=True)
            
            marker_path = os.path.join(target_dir, ".aim_managed")
            try:
                with open(marker_path, 'w') as f:
                    f.write(f"Installed by AppImage Manager at {time.time()}\n")
                logger.debug(f"Created marker file: {marker_path}")
            except Exception as marker_e:
                logger.warning(f"Could not create marker file '{marker_path}': {marker_e}")

            logger.info("Files copied successfully (non-root).")
            self._determine_final_paths() 
            logger.debug("Exiting install_files (success)")
            return True 
        except Exception as e:
            logger.error(f"Failed to copy files to installation directory: {e}", exc_info=True)
            logger.debug("Exiting install_files (failed)")
            return False 

    def get_installation_info(self):
        """Returns a dictionary with relevant info for database saving."""
        info = self.app_info.copy()
        
        # Create a sanitized name if not already present
        if 'name' in info and 'name_sanitized' not in info:
            info['name_sanitized'] = sanitize_name(info['name'])
        
        # Create desktop file path if not set
        desktop_file_path = getattr(self, 'final_copied_desktop_path', None)
        if not desktop_file_path and self.final_desktop_path:
            # Determine expected desktop filename
            app_name_sanitized = info.get('name_sanitized')
            if app_name_sanitized:
                desktop_filename = f"appimagekit_{app_name_sanitized}.desktop"
                
                # For system installations, use standard XDG path
                if self.install_mode == "system":
                    desktop_file_path = os.path.join(self.desktop_link_dir, desktop_filename)
                # For user installations, use user XDG path
                else:
                    desktop_file_path = os.path.join(self.desktop_link_dir, desktop_filename)
            else:
                logger.warning("Cannot determine desktop file path: missing name_sanitized")
        
        info.update({
            'id': str(uuid.uuid4()), 
            'appimage_path': self.appimage_path, 
            'install_path': self.app_install_dir, 
            'executable_path': self.final_executable_path, 
            'management_type': config.MGMT_TYPE_INSTALLED if self.install_mode != config.MGMT_TYPE_REGISTERED else config.MGMT_TYPE_REGISTERED,
            'install_mode': self.install_mode, 
            'requires_root': self.requires_root, 
            'final_desktop_path': self.final_desktop_path, 
            'desktop_file_path': desktop_file_path, 
            'executable_symlink': self.bin_symlink_target, 
            'icon_path': None, 
            'install_date': datetime.datetime.now().isoformat()
        })
        return info

    def _ensure_temp_dir(self):
        """Ensures the temporary directory exists."""
        if not self.temp_dir:
            self.temp_dir = tempfile.mkdtemp(prefix="aim_")
            logger.debug(f"Created temporary directory: {self.temp_dir}")
            self.temp_files.append(self.temp_dir) 
            
    def cleanup(self):
        """Removes temporary files and directories created by this instance."""
        logger.debug(f"Starting cleanup for installer instance (Temp files/dirs: {len(self.temp_files)} items)")
        files_to_remove = [f for f in self.temp_files if os.path.isfile(f) or os.path.islink(f)]
        for f_path in files_to_remove:
            try:
                os.remove(f_path)
                logger.debug(f"Removed temp file: {f_path}")
            except OSError as e:
                logger.warning(f"Could not remove temp file {f_path}: {e}")
                 
        dirs_to_remove = [d for d in self.temp_files if os.path.isdir(d)]
        for d_path in reversed(dirs_to_remove): 
            try:
                if os.path.exists(d_path): 
                    shutil.rmtree(d_path)
                    logger.debug(f"Removed temp directory: {d_path}")
                else: 
                    logger.debug(f"Temp directory already removed: {d_path}")
            except OSError as e: 
                logger.warning(f"Could not remove temp directory {d_path}: {e}")
                 
        self.temp_files = [] 
        self.temp_dir = None
        self.extract_dir = None 
        self.temp_preview_icon_path = None 
        logger.debug("Cleanup finished.")

    def create_symlinks(self):
        """Creates desktop integration (symlinks, desktop file, icons) for non-root installs."""
        logger.debug(f"Entering create_symlinks. Bin Target: {self.bin_symlink_target}, Desktop Target Dir: {self.desktop_link_dir}")
        if self.requires_root:
            logger.error("create_symlinks called for a root-requiring installation. Integration skipped.")
            return False
        if not self.app_install_dir:
            logger.error("Cannot create integration: Final installation directory is not set.")
            return False
        if not self.final_executable_path:
            logger.error("Cannot create integration: Final executable path is not set.")
            return False
        if not self.bin_symlink_target:
            logger.error("Cannot create integration: Binary symlink target path is not set.")
            return False
            
        self.symlinks_created = [] 
        success = True

        try:
            logger.debug(f"Ensuring integration target directories exist: {self.bin_link_dir}, {self.desktop_link_dir}")
            os.makedirs(self.bin_link_dir, exist_ok=True)
            os.makedirs(self.desktop_link_dir, exist_ok=True)
            logger.debug("Target directories ensured/created.")
        except OSError as e:
            logger.error(f"Failed to create integration directories: {e}", exc_info=True) 
            return False
            
        icon_for_desktop = integration.copy_app_icons(
            self.final_icon_path, 
            self.app_install_dir, 
            self.app_info 
        )
        logger.debug(f"Icon copy result (icon_for_desktop): {icon_for_desktop}")

        link_name = self.bin_symlink_target
        link_target = self.final_executable_path
        try:
            if os.path.lexists(link_name):
                logger.debug(f"Removing existing symlink: {link_name}")
                os.remove(link_name)
            logger.debug(f"Creating executable symlink: {link_name} -> {link_target}")
            os.symlink(link_target, link_name)
            self.symlinks_created.append(link_name) 
            logger.info(f"Executable symlink created: {link_name} -> {link_target}")
        except (OSError, PermissionError) as e:
            logger.error(f"Failed to create executable symlink '{link_name}': {e}", exc_info=True) 
            success = False 

        if success:
            logger.debug(f"Calling create_desktop_entry: final_path={self.final_desktop_path}, target_dir={self.desktop_link_dir}, bin_target={self.bin_symlink_target}, icon={icon_for_desktop}")
            created_desktop_path_result = integration.create_desktop_entry(
                self.final_desktop_path, 
                self.desktop_link_dir, 
                self.bin_symlink_target, 
                icon_for_desktop,
                install_dir=self.app_install_dir  # For Qt detection
            )
            logger.debug(f"create_desktop_entry result: {created_desktop_path_result}")
            
            if created_desktop_path_result:
                self.final_copied_desktop_path = created_desktop_path_result 
            else:
                logger.error("Desktop entry creation failed.")
                success = False 
        else:
            logger.warning("Skipping desktop file creation due to previous symlink failure.")
            
        logger.debug(f"Exiting create_symlinks (success={success})")
        return success

    def get_install_commands(self):
        """Generates shell commands needed for root installation (rsync, mkdir, ln)."""
        if not self.requires_root:
            logger.debug("get_install_commands called for non-root install, returning empty list.")
            return [] 
            
        # --->>> Check app_install_dir and bin_symlink_target ONLY initially <<<---
        if not self.app_install_dir or not self.bin_symlink_target:
            logger.error("Cannot generate root commands: Missing required paths (install_dir or bin_symlink_target).")
            return []
         
        commands = []
        
        # --->>> Get relative executable path from app_info <<<---
        relative_exec = self.app_info.get('exec_relative')
        if not relative_exec:
            # Attempt to find it based on standard locations if not in app_info
            # This is less ideal but a fallback
            potential_execs = ["AppRun", "bin/AppRun"] # Add more common paths if needed
            if self.app_info.get('exec'): potential_execs.insert(0, self.app_info['exec']) 
            
            # We can't check os.path inside the non-existent target yet,
            # so we rely on the exec_relative being set correctly earlier,
            # or fallback to common names like AppRun.
            # For now, let's assume AppRun if exec_relative is missing.
            logger.warning("exec_relative not found in app_info, assuming 'AppRun' for command generation.")
            relative_exec = "AppRun" 
            
        if not relative_exec:
             logger.error("Cannot determine relative executable path for command generation.")
             return []
             
        # Calculate the final executable path WITHIN the target directory
        # This path might not exist *yet*, but the command assumes it will after rsync
        calculated_final_exec_path = os.path.join(self.app_install_dir, relative_exec)
        logger.debug(f"Calculated final executable path for command: {calculated_final_exec_path}")

        # --->>> Check extract_dir (still needed for rsync source) <<<---
        if not self.extract_dir or not os.path.isdir(self.extract_dir):
            logger.error("Cannot generate root commands: Missing source extraction directory.")
            return []

        # --- Generate Commands (Restored Original Logic) --- 
        base_dir_for_mkdir = os.path.dirname(self.app_install_dir.rstrip('/'))
        if base_dir_for_mkdir: 
            commands.append(f"mkdir -p \"{base_dir_for_mkdir}\"")
             
        source_dir = self.extract_dir
        if not source_dir.endswith('/'): source_dir += '/' 
        target_dir = self.app_install_dir
        commands.append(f"rsync -ah --exclude='.union' \"{source_dir}\" \"{target_dir}\"")
        
        marker_path = os.path.join(target_dir, ".aim_managed")
        marker_content = f"Installed by AppImage Manager (root) at {time.time()}"
        escaped_content = marker_content.replace('"', '\\"')
        commands.append(f'echo "{escaped_content}" > "{marker_path}"')

        bin_link_parent = os.path.dirname(self.bin_symlink_target.rstrip('/'))
        if bin_link_parent:
            commands.append(f"mkdir -p \"{bin_link_parent}\"")

        # --->>> Link for Executable <<<---
        commands.append(f"rm -f \"{self.bin_symlink_target}\"") 
        commands.append(f"ln -s \"{calculated_final_exec_path}\" \"{self.bin_symlink_target}\"")

        # --->>> Link for Desktop File <<<---
        if self.final_desktop_path and self.desktop_link_dir:
             app_name = self.app_info.get('name') or os.path.basename(self.appimage_path).replace('.AppImage','').replace('.appimage','')
             sanitized_app_name = sanitize_name(app_name)
             if sanitized_app_name:
                 desktop_filename = f"appimagekit_{sanitized_app_name}.desktop"
                 target_desktop_link_path = os.path.join(self.desktop_link_dir, desktop_filename)
                 desktop_link_parent = os.path.dirname(target_desktop_link_path.rstrip('/'))
                 if desktop_link_parent:
                     commands.append(f"mkdir -p \"{desktop_link_parent}\"")
                 commands.append(f"rm -f \"{target_desktop_link_path}\"")
                 commands.append(f"ln -s \"{self.final_desktop_path}\" \"{target_desktop_link_path}\"")
                 self.final_copied_desktop_path = target_desktop_link_path 
             else:
                 logger.warning("Could not generate sanitized name for desktop file link command.")
        else:
            logger.warning("Skipping desktop file link command generation: Missing final_desktop_path or desktop_link_dir.")

        logger.debug(f"Generated root commands: {commands}")
        return commands

    def read_metadata(self):
        """Reads metadata (desktop file, icon) from the AppImage, attempting efficient extraction first."""
        logger.debug(f"Entering read_metadata for {self.appimage_path}")
        logger.info(f"Reading metadata for {self.appimage_path}")
        self.app_info = {}
        self.extracted_desktop_path = None
        self.temp_preview_icon_path = None 

        if not os.access(self.appimage_path, os.X_OK):
            try:
                os.chmod(self.appimage_path, os.stat(self.appimage_path).st_mode | 0o111)
                logger.info(f"Made AppImage executable: {self.appimage_path}")
            except OSError as e:
                logger.error(f"Failed to make AppImage executable for metadata read: {e}")
                self._populate_fallback_metadata()
                self.app_install_dir = self._get_app_specific_install_dir()
                self._determine_final_paths_placeholder()
                return False, None 
                
        self._ensure_temp_dir()
        meta_extract_dir = os.path.join(self.temp_dir, "meta_read")
        if os.path.exists(meta_extract_dir): shutil.rmtree(meta_extract_dir)
        os.makedirs(meta_extract_dir)
        self.temp_files.append(meta_extract_dir) 
        
        squashfs_root = os.path.join(meta_extract_dir, "squashfs-root")
        found_desktop_file = None
        extraction_error = None
        
        # Create environment that prevents AppImage from launching GUI
        extract_env = os.environ.copy()
        extract_env["APPIMAGE_EXTRACT_AND_RUN"] = "0"
        extract_env["NO_CLEANUP"] = "1"
        extract_env.pop("DISPLAY", None)  # Remove DISPLAY to prevent GUI launch
        extract_env.pop("WAYLAND_DISPLAY", None)  # Also remove Wayland display
        
        try:
            logger.debug("Attempting selective desktop file extraction...")
            selective_extract_command = [self.appimage_path, f"--appimage-extract=*.desktop"]
            
            # Use non-blocking extraction to keep UI responsive
            return_code, stdout, stderr = _run_subprocess_non_blocking(
                selective_extract_command, 
                cwd=meta_extract_dir, 
                timeout=60,  # 60 seconds for selective extraction
                env=extract_env
            )
            
            if return_code is None:
                # Timeout or error
                logger.warning(f"Selective desktop extraction failed: {stderr}")
            else:
                logger.debug(f"Selective extract result code: {return_code}")
                if return_code == 0 and os.path.isdir(squashfs_root):
                    logger.debug("Selective desktop file extraction command succeeded.")
                    for root, _, files in os.walk(squashfs_root):
                        for file in files: 
                            if file.lower().endswith(".desktop"):
                                found_desktop_file = os.path.join(root, file)
                                logger.debug(f"Found desktop file via selective extract: {found_desktop_file}")
                                self.extracted_desktop_path = found_desktop_file
                                break # Inner loop
                        if found_desktop_file: break # Outer loop
                    if not found_desktop_file:
                        logger.warning("Selective extract command ok, but no .desktop file found inside.")
                else:
                    stderr_out = stderr.strip() if stderr else "(no stderr)"
                    logger.warning(f"Selective desktop extraction failed (Code: {return_code}). Stderr: {stderr_out}")
            
            if not found_desktop_file:
                logger.info("Selective desktop extraction insufficient, attempting full extract for metadata...")
                if os.path.exists(squashfs_root): shutil.rmtree(squashfs_root) 
                
                full_extract_command = [self.appimage_path, "--appimage-extract"]
                
                # Use non-blocking full extraction
                return_code_full, stdout_full, stderr_full = _run_subprocess_non_blocking(
                    full_extract_command, 
                    cwd=meta_extract_dir, 
                    timeout=300,  # 5 minutes for full extraction of large AppImages
                    env=extract_env
                )
                
                if return_code_full is None:
                    extraction_error = f"Full metadata extraction timed out or failed: {stderr_full}"
                    logger.error(extraction_error)
                elif return_code_full == 0 and os.path.isdir(squashfs_root):
                    logger.info("Full extract for metadata successful.")
                    for root, _, files in os.walk(squashfs_root):
                        for file in files: 
                            if file.lower().endswith(".desktop"):
                                found_desktop_file = os.path.join(root, file)
                                logger.debug(f"Found desktop file via full extract: {found_desktop_file}")
                                self.extracted_desktop_path = found_desktop_file
                                break # Inner loop
                        if found_desktop_file: break # Outer loop
                    if not found_desktop_file:
                        logger.warning("Full extract ok, but still no .desktop file found inside.")
                else: 
                    stderr_output = stderr_full.strip() if stderr_full else "(no stderr)"
                    log_msg = f"Full extract for metadata failed (Code: {return_code_full}): {stderr_output}"
                    logger.error(log_msg)
                    extraction_error = log_msg 

        except Exception as e:
            error_msg = f"Error during metadata extraction process: {e}"
            logger.error(error_msg, exc_info=True)
            extraction_error = error_msg
             
        if found_desktop_file and os.path.isfile(found_desktop_file):
            parsed_info = self._parse_desktop_file(found_desktop_file)
            self.app_info.update(parsed_info)
            logger.info(f"Successfully parsed metadata from extracted desktop file: {found_desktop_file}")

            icon_name = self.app_info.get("icon_name")
            found_icon_source_path = None

            # Check .DirIcon first (can be a file or symlink)
            potential_dir_icon = os.path.join(squashfs_root, ".DirIcon")
            if os.path.exists(potential_dir_icon):
                # Handle symlink - follow it to get the actual icon
                if os.path.islink(potential_dir_icon):
                    link_target = os.readlink(potential_dir_icon)
                    if not os.path.isabs(link_target):
                        link_target = os.path.join(squashfs_root, link_target)
                    if os.path.isfile(link_target):
                        found_icon_source_path = link_target
                        logger.debug(f"Found preview icon source: .DirIcon symlink -> {found_icon_source_path}")
                elif os.path.isfile(potential_dir_icon):
                    found_icon_source_path = potential_dir_icon
                    logger.debug(f"Found preview icon source: .DirIcon at {found_icon_source_path}")

            if not found_icon_source_path and icon_name:
                logger.debug(f"Searching for preview icon source matching name '{icon_name}' in {squashfs_root}")
                icon_exts = ['.png', '.svg', '.svgz', '.xpm', '.ico']
                # Extended search paths for icon locations
                common_dirs = [
                    "",  # Root of squashfs
                    # Standard XDG hicolor icon directories (256, 128, 64, 48, 32, scalable)
                    "usr/share/icons/hicolor/256x256/apps",
                    "usr/share/icons/hicolor/128x128/apps", 
                    "usr/share/icons/hicolor/64x64/apps",
                    "usr/share/icons/hicolor/48x48/apps",
                    "usr/share/icons/hicolor/32x32/apps",
                    "usr/share/icons/hicolor/scalable/apps",
                    "share/icons/hicolor/256x256/apps",
                    "share/icons/hicolor/128x128/apps",
                    "share/icons/hicolor/64x64/apps",
                    "share/icons/hicolor/48x48/apps",
                    "share/icons/hicolor/32x32/apps",
                    "share/icons/hicolor/scalable/apps",
                    # Pixmaps directories
                    "usr/share/pixmaps",
                    "share/pixmaps",
                    # Some apps use these non-standard locations
                    "usr/share/icons",
                    "share/icons",
                    "resources",
                    "assets",
                    "icons",
                ]
                
                # First check if icon_name is a path
                if '/' in icon_name:
                    potential_rel_path = os.path.join(squashfs_root, icon_name)
                    if os.path.isfile(potential_rel_path):
                        found_icon_source_path = potential_rel_path

                # Search in common directories
                if not found_icon_source_path:
                    for cdir in common_dirs:
                        # Try exact icon name match first
                        potential_base_path = os.path.join(squashfs_root, cdir, icon_name)
                        if os.path.isfile(potential_base_path):
                            found_icon_source_path = potential_base_path
                            break 
                        # Try with extensions
                        for ext in icon_exts:
                            potential_path = os.path.join(squashfs_root, cdir, f"{icon_name}{ext}")
                            if os.path.isfile(potential_path):
                                found_icon_source_path = potential_path
                                break 
                        if found_icon_source_path: 
                            break
                
                # Fallback: recursive search for icon file if not found
                if not found_icon_source_path:
                    logger.debug(f"Icon not found in common locations, attempting recursive search...")
                    for root, dirs, files in os.walk(squashfs_root):
                        for file in files:
                            file_lower = file.lower()
                            # Match icon name (with or without extension)
                            if file_lower.startswith(icon_name.lower()) and any(file_lower.endswith(ext) for ext in icon_exts):
                                found_icon_source_path = os.path.join(root, file)
                                logger.debug(f"Found icon via recursive search: {found_icon_source_path}")
                                break
                        if found_icon_source_path:
                            break

                if found_icon_source_path:
                    logger.debug(f"Found preview icon source by name: {found_icon_source_path}")

            if found_icon_source_path:
                self._ensure_temp_dir() 
                try:
                    # --->>> Direct Path Construction <<<---
                    original_ext = os.path.splitext(found_icon_source_path)[1].lower()
                    # --->>> Handle .DirIcon or missing extension <<<---
                    if not original_ext or found_icon_source_path.endswith('.DirIcon'):
                        logger.debug(f"Source icon '{os.path.basename(found_icon_source_path)}' has no/unconventional extension. Assuming PNG for temp copy.")
                        original_ext = ".png" # Assume PNG
                        
                    temp_icon_path_target = os.path.join(
                        self.temp_dir, 
                        f"preview_{uuid.uuid4().hex}{original_ext}"
                    )
                    
                    # Log the source and final target path
                    logger.debug(f"Preview Icon: Source='{found_icon_source_path}', Target='{temp_icon_path_target}'")
                    
                    shutil.copy2(found_icon_source_path, temp_icon_path_target)
                    self.temp_preview_icon_path = temp_icon_path_target 
                    self.temp_files.append(self.temp_preview_icon_path) 
                    logger.info(f"Copied preview icon to temporary path: {self.temp_preview_icon_path}")
                except Exception as e:
                    logger.error(f"Failed to copy preview icon {found_icon_source_path} to temp dir: {e}")
                    self.temp_preview_icon_path = None 
            else:
                logger.info(f"No suitable preview icon source found within {squashfs_root} for icon name '{icon_name}'.")

            logger.debug("Recalculating paths after successful metadata read...")
            self.app_install_dir = self._get_app_specific_install_dir()
            self._determine_final_paths_placeholder() 
            logger.debug(f"Updated Info: Name='{self.app_info.get('name')}', InstallDir='{self.app_install_dir}', BinLink='{self.bin_symlink_target}'")
            logger.debug(f"Final read metadata: {self.app_info}")
            extracted_icon_path = self.temp_preview_icon_path if self.temp_preview_icon_path else None
            logger.debug(f"read_metadata finished. Success: True. Icon path: {extracted_icon_path}")
            return True, extracted_icon_path

        else: 
            logger.warning(f"Could not find or extract .desktop file (Error: {extraction_error}). Using fallback metadata.")
            self._populate_fallback_metadata()
            logger.debug("Recalculating paths using fallback metadata...")
            self.app_install_dir = self._get_app_specific_install_dir()
            self._determine_final_paths_placeholder()
            logger.debug(f"Fallback Info: Name='{self.app_info.get('name')}', InstallDir='{self.app_install_dir}', BinLink='{self.bin_symlink_target}'")
            logger.debug("Exiting read_metadata (failed)")
            extracted_icon_path = None
            return False, extracted_icon_path
        
    def _populate_fallback_metadata(self):
        """Populates self.app_info with fallback data when metadata reading fails."""
        base_name = os.path.basename(self.appimage_path)
        if base_name.lower().endswith('.appimage'):
            base_name = base_name[:-len('.appimage')]
            
        # Create sanitized name first
        sanitized_name = sanitize_name(base_name)
        
        self.app_info = {
            'name': base_name, 
            'version': 'Unknown',
            'icon_name': sanitized_name, 
            'name_sanitized': sanitized_name,
            'exec': None,
            'exec_relative': None
        }
        logger.warning(f"Populated with fallback metadata: {self.app_info}") 