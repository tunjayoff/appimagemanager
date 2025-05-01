import time
from pathlib import Path
import os
import shutil
import logging
import tempfile
import subprocess
import configparser
import uuid

from . import config
from . import integration
from .utils import sanitize_name

logger = logging.getLogger(__name__)

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
            result = subprocess.run(extract_command, cwd=extract_meta_dir, check=False, capture_output=True, text=True, timeout=15)

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
                logger.debug(f"Parsed desktop entry: Name='{data['name']}', Version='{data['version']}', Icon='{data['icon_name']}', Exec='{data['exec']}', ExecRel='{data['exec_relative']}'")
            else:
                logger.warning(f"Could not find [Desktop Entry] section in {desktop_file_path}")
        except Exception as e:
            logger.error(f"Error parsing desktop file {desktop_file_path}: {e}")
        return data

    def _get_app_specific_install_dir(self):
        """Determines the specific installation directory based on app name."""
        app_name = self.app_info.get('name')
        if not app_name:
            logger.error("Cannot determine app-specific dir: App name is missing from app_info.")
            return None 

        sanitized = sanitize_name(app_name)
        version_raw = self.app_info.get('version')
        version = sanitize_name(version_raw) if version_raw else 'Unknown'
        
        dir_name = f"{sanitized}_{version}" if version and version.lower() != 'unknown' else sanitized
        
        if not self.base_install_prefix:
            logger.error("Cannot determine app-specific dir: base_install_prefix not set.")
            return None
            
        return os.path.join(self.base_install_prefix, dir_name)
         
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
        """Determines final paths for executable, desktop file, icon AFTER install/copy."""
        self.final_executable_path = None
        self.final_desktop_path = None
        self.final_icon_path = None

        if not self.app_install_dir or not os.path.isdir(self.app_install_dir):
            logger.error("Cannot determine final paths: Install directory not set or does not exist.")
            return
            
        logger.debug(f"Determining final paths within install dir: {self.app_install_dir}")

        # Find Final Desktop Path
        found_desktop = None
        if self.extracted_desktop_path:
            try: 
                if self.extract_dir and self.extracted_desktop_path.startswith(self.extract_dir):
                    relative_desktop_path = os.path.relpath(self.extracted_desktop_path, self.extract_dir) 
                    potential_final_path = os.path.join(self.app_install_dir, relative_desktop_path)
                    if os.path.isfile(potential_final_path):
                        found_desktop = potential_final_path
                    else: 
                        logger.debug(f"Expected desktop path {potential_final_path} not found based on temp extract, scanning install dir...")
                else:
                    logger.warning("Cannot determine relative desktop path (extracted path issue), scanning install dir.")
            except ValueError as e: 
                logger.warning(f"Could not calculate relative path for desktop file, scanning install dir. Error: {e}")

        if not found_desktop:
            for root, _, files in os.walk(self.app_install_dir):
                for file in files:
                    if file.lower().endswith(".desktop"):
                        found_desktop = os.path.join(root, file)
                        logger.debug(f"Found desktop file by scanning: {found_desktop}")
                        break # Inner loop
                if found_desktop: break # Outer loop
        
        self.final_desktop_path = found_desktop
        if not self.final_desktop_path: logger.warning("Could not find final .desktop file path.")
        else: logger.debug(f"Final desktop path: {self.final_desktop_path}")

        # Find Final Executable Path
        exec_relative = self.app_info.get("exec_relative")
        found_exec = None
        if exec_relative:
            potential_paths = [
                os.path.join(self.app_install_dir, exec_relative),
                os.path.join(self.app_install_dir, "bin", exec_relative),
                os.path.join(self.app_install_dir, "usr/bin", exec_relative)
            ]
            for path in potential_paths:
                if os.path.isfile(path) and os.access(path, os.X_OK):
                    found_exec = path
                    break # Found it
        
        if not found_exec:
            apprun_path = os.path.join(self.app_install_dir, "AppRun")
            if os.path.isfile(apprun_path) and os.access(apprun_path, os.X_OK):
                found_exec = apprun_path
                logger.debug("Using AppRun as executable.")
                
        self.final_executable_path = found_exec
        if not self.final_executable_path: logger.warning("Could not find final executable file path.")
        else: logger.debug(f"Final executable path: {self.final_executable_path}")

        # Find Final Icon Path
        icon_name = self.app_info.get("icon_name")
        found_icon = None
        
        dir_icon_path = os.path.join(self.app_install_dir, ".DirIcon")
        if os.path.isfile(dir_icon_path):
            found_icon = dir_icon_path
            logger.debug("Using .DirIcon as final icon path.")

        if not found_icon and icon_name:
            icon_exts = ['.png', '.svg', '.svgz', '.xpm', '.ico']
            common_dirs = [
                "", 
                "share/icons/hicolor/scalable/apps",
                "usr/share/icons/hicolor/scalable/apps",
                "share/icons/hicolor/128x128/apps", 
                "usr/share/icons/hicolor/128x128/apps",
                "share/icons/hicolor/64x64/apps", 
                "usr/share/icons/hicolor/64x64/apps",
                "share/pixmaps",
                "usr/share/pixmaps",
            ]
            if '/' in icon_name:
                potential_rel_path = os.path.join(self.app_install_dir, icon_name)
                if os.path.isfile(potential_rel_path):
                    found_icon = potential_rel_path
                
            if not found_icon:
                for cdir in common_dirs:
                    potential_base_path = os.path.join(self.app_install_dir, cdir, icon_name)
                    if os.path.isfile(potential_base_path):
                        found_icon = potential_base_path
                        break # Inner loop (dirs)
                    for ext in icon_exts:
                        potential_path = os.path.join(self.app_install_dir, cdir, f"{icon_name}{ext}")
                        if os.path.isfile(potential_path):
                            found_icon = potential_path
                            break # Inner loop (exts)
                    if found_icon: break # Outer loop (dirs)
                    
        self.final_icon_path = found_icon
        if not self.final_icon_path: logger.debug("Could not determine final icon path.") 
        else: logger.debug(f"Final icon path: {self.final_icon_path}")
              
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
            result = subprocess.run(extract_command, cwd=self.temp_dir, check=True, capture_output=True, text=True, timeout=120)
            
            if not os.path.isdir(self.extract_dir):
                logger.error(f"Extraction command succeeded but expected directory '{self.extract_dir}' not found.")
                return False
                 
            logger.info(f"Full extraction completed. RC={result.returncode}")
            logger.debug("Updating metadata and final paths after full extraction...")
            self._update_metadata_from_desktop_file()
            self.app_install_dir = self._get_app_specific_install_dir()
            self._determine_final_paths()
            self._determine_final_paths_placeholder()
            logger.debug(f"Post-extraction Info: Name='{self.app_info.get('name')}', InstallDir='{self.app_install_dir}', BinLink='{self.bin_symlink_target}', FinalExec='{self.final_executable_path}'")
            return True
            
        except FileNotFoundError:
            logger.error(f"Extraction failed: AppImage file not found at {self.appimage_path}")
            return False 
        except subprocess.CalledProcessError as e:
            stderr_output = e.stderr.strip() if e.stderr else "(no stderr)"
            logger.error(f"Extraction failed (Return Code: {e.returncode}): {stderr_output}", exc_info=False) 
            return False 
        except subprocess.TimeoutExpired:
            logger.error("Extraction failed: Timeout expired.", exc_info=True)
            return False 
        except Exception as e:
            logger.error(f"Extraction failed with unexpected error: {e}", exc_info=True)
            return False 
    
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
        info.update({
            'id': str(uuid.uuid4()), 
            'appimage_path': self.appimage_path, 
            'install_path': self.app_install_dir, 
            'executable_path': self.final_executable_path, 
            'management_type': config.MGMT_TYPE_INSTALLED if self.install_mode != config.MGMT_TYPE_REGISTERED else config.MGMT_TYPE_REGISTERED,
            'install_mode': self.install_mode, 
            'requires_root': self.requires_root, 
            'extracted_desktop_path': self.extracted_desktop_path, 
            'final_desktop_path': self.final_desktop_path, 
            'desktop_file_path': self.final_copied_desktop_path, 
            'executable_symlink': self.bin_symlink_target, 
            'icon_path': self.final_icon_path 
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
                icon_for_desktop 
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
            
        if not self.app_install_dir or not self.final_executable_path or not self.bin_symlink_target:
            logger.error("Cannot generate root commands: Missing required paths (install_dir, final_executable_path, or bin_symlink_target). Did extraction succeed?")
            return []
             
        commands = []
        
        base_dir_for_mkdir = os.path.dirname(self.app_install_dir.rstrip('/'))
        if base_dir_for_mkdir: 
            commands.append(f"mkdir -p \"{base_dir_for_mkdir}\"")
             
        if not self.extract_dir or not os.path.isdir(self.extract_dir):
            logger.error("Cannot generate root commands: Missing source extraction directory.")
            return []
             
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

        link_target = self.final_executable_path
        link_name = self.bin_symlink_target
        commands.append(f"rm -f \"{link_name}\"") 
        commands.append(f"ln -sf \"{link_target}\" \"{link_name}\"")
        logger.debug(f"Added command to create executable symlink: {link_name} -> {link_target}")
            
        logger.info(f"Generated {len(commands)} root installation commands.")
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
        
        try:
            logger.debug("Attempting selective desktop file extraction...")
            selective_extract_command = [self.appimage_path, f"--appimage-extract=*.desktop"]
            result_selective = subprocess.run(selective_extract_command, cwd=meta_extract_dir, check=False, capture_output=True, text=True, timeout=20)
            
            logger.debug(f"Selective extract result code: {result_selective.returncode}")
            if result_selective.returncode == 0 and os.path.isdir(squashfs_root):
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
                stderr_out = result_selective.stderr.strip() if result_selective.stderr else "(no stderr)"
                logger.warning(f"Selective desktop extraction failed (Code: {result_selective.returncode}). Stderr: {stderr_out}")
            
            if not found_desktop_file:
                logger.info("Selective desktop extraction insufficient, attempting full extract for metadata...")
                if os.path.exists(squashfs_root): shutil.rmtree(squashfs_root) 
                
                full_extract_command = [self.appimage_path, "--appimage-extract"]
                result_full = subprocess.run(full_extract_command, cwd=meta_extract_dir, check=False, capture_output=True, text=True, timeout=90)
                 
                if result_full.returncode == 0 and os.path.isdir(squashfs_root):
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
                    stderr_output = result_full.stderr.strip() if result_full.stderr else "(no stderr)"
                    log_msg = f"Full extract for metadata failed (Code: {result_full.returncode}): {stderr_output}"
                    logger.error(log_msg)
                    extraction_error = log_msg 

        except subprocess.TimeoutExpired as e:
            error_msg = f"Metadata extraction timed out ({e.cmd})."
            logger.error(error_msg)
            extraction_error = error_msg
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

            potential_dir_icon = os.path.join(squashfs_root, ".DirIcon")
            if os.path.isfile(potential_dir_icon):
                found_icon_source_path = potential_dir_icon
                logger.debug(f"Found preview icon source: .DirIcon at {found_icon_source_path}")

            if not found_icon_source_path and icon_name:
                logger.debug(f"Searching for preview icon source matching name '{icon_name}' in {squashfs_root}")
                icon_exts = ['.png', '.svg', '.svgz', '.xpm', '.ico']
                common_dirs = [
                    "", 
                    "share/icons/hicolor/scalable/apps",
                    "usr/share/icons/hicolor/scalable/apps",
                    "share/icons/hicolor/128x128/apps", 
                    "usr/share/icons/hicolor/128x128/apps",
                    "share/icons/hicolor/64x64/apps",
                    "usr/share/icons/hicolor/64x64/apps",
                    "share/pixmaps",
                    "usr/share/pixmaps",
                ]
                if '/' in icon_name:
                    potential_rel_path = os.path.join(squashfs_root, icon_name)
                    if os.path.isfile(potential_rel_path):
                        found_icon_source_path = potential_rel_path

                if not found_icon_source_path:
                    for cdir in common_dirs:
                        potential_base_path = os.path.join(squashfs_root, cdir, icon_name)
                        if os.path.isfile(potential_base_path):
                            found_icon_source_path = potential_base_path
                            break 
                        for ext in icon_exts:
                            potential_path = os.path.join(squashfs_root, cdir, f"{icon_name}{ext}")
                            if os.path.isfile(potential_path):
                                found_icon_source_path = potential_path
                                break 
                        if found_icon_source_path: break 

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
            
        self.app_info = {
            'name': base_name, 
            'version': 'Unknown',
            'icon_name': sanitize_name(base_name), 
            'exec': None,
            'exec_relative': None
        }
        logger.warning(f"Populated with fallback metadata: {self.app_info}") 