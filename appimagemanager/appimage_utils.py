"""
AppImage Yöneticisi - AppImage İşlemleri
AppImage dosyaları üzerinde işlemler yapmak için çeşitli yardımcı fonksiyonlar.
"""

import os
import subprocess
import shutil
import tempfile
import logging
import json
import configparser
import traceback
import re # Import re for sanitizing names
import uuid # Ensure uuid is imported if not already
from pathlib import Path

from . import config

logger = logging.getLogger(__name__)

# Helper function to sanitize app names for directory/file names
def sanitize_name(name):
    # Remove special characters, replace spaces with underscores
    name = re.sub(r'[^a-zA-Z0-9_\-\.]', '', name)
    name = name.replace(' ', '_')
    return name or "unknown_app"

class AppImageInstaller:
    """AppImage kurulumu için gerekli işlemleri gerçekleştirir (izole dizin + symlink yöntemi)."""
    
    def __init__(self, appimage_path, install_mode="user", custom_path=None):
        """AppImage kurulum işlemlerini hazırlar.
        
        Args:
            appimage_path (str): Kurulacak AppImage dosyasının yolu
            install_mode (str): Kurulum modu - "system" (/opt), "user" (~/.local) veya "custom"
            custom_path (str, optional): Özel ana kurulum yolu (install_mode="custom" için)
        """
        self.appimage_path = appimage_path
        self.install_mode_requested = install_mode # Store the original request
        self.custom_path_prefix = custom_path # Store original custom path if provided
        self.temp_dir = None
        self.extract_dir = None
        self.app_install_dir = None # Determined after metadata extraction
        self.extracted_desktop_path = None
        self.final_desktop_path = None
        self.final_executable_path = None
        self.final_icon_path = None
        self.symlinks_created = []
        self.app_id = None # Will be set by DBManager

        # --- Determine base path and link dirs based on mode ---
        self._set_paths_based_on_mode(install_mode, custom_path)

        # --- Initial metadata extraction (gets basic name) ---
        self.app_info = self._extract_initial_metadata()
        
        # --- Check root requirement based on paths ---
        # Note: This is an initial check. Actual copy/link might still fail.
        self.requires_root = self._check_if_root_required()
        
    def _set_paths_based_on_mode(self, install_mode, custom_path):
        """Sets base_install_prefix and link directories based on install mode."""
        if install_mode == "system":
            self.base_install_prefix = "/opt/appimage-manager" 
            self.bin_link_dir = "/usr/local/bin"
            self.desktop_link_dir = "/usr/local/share/applications"
            self.icon_link_base_dir = "/usr/local/share/icons"
            self.install_mode = "system"
        elif install_mode == "custom" and custom_path:
            self.base_install_prefix = os.path.join(custom_path, "appimage-manager") # App files here
            # Links go to standard user locations for integration
            self.bin_link_dir = os.path.join(config.USER_HOME, ".local", "bin")
            self.desktop_link_dir = os.path.join(config.USER_HOME, ".local", "share", "applications")
            self.icon_link_base_dir = os.path.join(config.USER_HOME, ".local", "share", "icons")
            self.install_mode = "custom"
            logger.info(f"Custom install path set to '{custom_path}', but symlinks will be created in user's standard ~/.local directories.")
        else: # Default to user mode
            self.base_install_prefix = os.path.join(config.USER_HOME, ".local", "share", "appimage-manager")
            self.bin_link_dir = os.path.join(config.USER_HOME, ".local", "bin")
            self.desktop_link_dir = os.path.join(config.USER_HOME, ".local", "share", "applications")
            self.icon_link_base_dir = os.path.join(config.USER_HOME, ".local", "share", "icons")
            self.install_mode = "user"
            
    def _get_app_specific_install_dir(self):
        """Uygulama adı veya ID'sine göre kurulum dizinini belirler."""
        app_dirname = sanitize_name(self.app_info.get("name", "unknown_app"))
        return os.path.join(self.base_install_prefix, app_dirname)

    def _check_if_root_required(self):
        """Kurulum veya link oluşturma için root yetkisi gerekip gerekmediğini kontrol eder."""
        dirs_to_check_write = [
            self.base_install_prefix,
            self.bin_link_dir,
            self.desktop_link_dir,
            self.icon_link_base_dir
        ]
        
        for target_dir in dirs_to_check_write:
            # Check parent first
            parent = os.path.dirname(target_dir)
            # Handle edge case where parent is root dir '/'
            if not parent:
                parent = '/'
                
            if not os.path.exists(parent): # If parent doesn't exist, we need to create it
                 # Check if we can write to the parent of the parent to create it
                 grandparent = os.path.dirname(parent)
                 if not grandparent:
                      grandparent = '/'
                 if not os.access(grandparent, os.W_OK):
                     logger.debug(f"Root gerekli: Dizin oluşturma izni yok ({parent})")
                     return True
            elif not os.access(parent, os.W_OK):
                 logger.debug(f"Root gerekli: Üst dizine yazma izni yok ({parent})")
                 return True
                 
            # If the target directory itself exists, check write permissions there too
            if os.path.exists(target_dir) and not os.access(target_dir, os.W_OK):
                 logger.debug(f"Root gerekli: Hedef dizine yazma izni yok ({target_dir})")
                 return True
                     
        return False
    
    def _extract_initial_metadata(self):
        """AppImage dosyasından ilk meta verileri (dosya adı) çıkarır."""
        app_name = os.path.basename(self.appimage_path).replace(".AppImage", "")
        app_name = re.sub(r'[-_]v?[\\d\\.]+(\\-x86_64|\\-amd64)?$', '', app_name, flags=re.IGNORECASE)
        return {
            "name": app_name or "UnknownApp", # Ensure name is not empty
            "appimage_path": self.appimage_path,
            "version": "unknown",
            "description": "",
            "icon_name": "", 
            "categories": [],
            "exec_relative": "", 
            "install_mode": self.install_mode # Use the determined mode
        }
    
    def check_prerequisites(self):
        """Kurulum için gerekli önkoşulları kontrol eder."""
        checks = {
            "appimage_exists": os.path.exists(self.appimage_path),
            "appimage_executable": os.access(self.appimage_path, os.X_OK),
            "libfuse_installed": self._check_libfuse_installed()
            # Removed rsync check as we use shutil now for file copy
        }
        
        if self.requires_root:
            checks["is_root"] = os.geteuid() == 0
        else:
            # Check if we have write access to target dirs even if not root
            checks["has_write_access"] = True # Assume true if root not required
        
        return checks
    
    def _check_libfuse_installed(self):
        """libfuse paketinin kurulu olup olmadığını kontrol eder."""
        try:
            result = subprocess.run(
                ["dpkg-query", "-W", "-f='${Status}'", config.LIBFUSE_PACKAGE], 
                capture_output=True, 
                text=True, 
                check=False
            )
            return "install ok installed" in result.stdout
        except Exception as e:
            logger.error(f"libfuse kontrol edilirken hata: {e}")
            return False

    def extract_appimage(self):
        """AppImage dosyasını geçici bir dizine çıkarır ve meta verileri günceller."""
        try:
            # --- Ensure AppImage is executable before trying to run it --- 
            try:
                current_mode = os.stat(self.appimage_path).st_mode
                # Check if execute bit is set for the owner (S_IXUSR)
                if not (current_mode & os.X_OK):
                    logger.warning(f"AppImage is not executable. Setting +x permission: {self.appimage_path}")
                    # Add execute permission for owner (read/write/exec), read/exec for others
                    os.chmod(self.appimage_path, current_mode | 0o111) # Add execute for owner, group, others
            except Exception as chmod_err:
                 logger.error(f"Failed to set execute permission on {self.appimage_path}: {chmod_err}")
                 # Decide if we should proceed or raise an error - let's try proceeding

            self.temp_dir = tempfile.mkdtemp(prefix="appimage_extract_")
            logger.info(f"Geçici dizin oluşturuldu: {self.temp_dir}")
            
            logger.info(f"AppImage içeriği çıkarılıyor: {self.appimage_path}")
            cmd = [self.appimage_path, "--appimage-extract"]
            env = os.environ.copy()
            env['HOME'] = self.temp_dir 
            result = subprocess.run(cmd, cwd=self.temp_dir, capture_output=True, text=True, env=env)
            
            if result.returncode != 0:
                logger.warning(f"AppImage çıkarma ilk denemede başarısız oldu (stderr: {result.stderr}), HOME olmadan tekrar deneniyor...")
                result = subprocess.run(cmd, cwd=self.temp_dir, capture_output=True, text=True)
                if result.returncode != 0:
                    logger.error(f"AppImage çıkarma başarısız: {result.stderr}")
                    self.cleanup()
                    return False
            
            self.extract_dir = os.path.join(self.temp_dir, "squashfs-root")
            if not os.path.isdir(self.extract_dir):
                logger.error(f'\'squashfs-root\' dizini bulunamadı: {self.temp_dir}')
                subdirs = [d for d in os.listdir(self.temp_dir) if os.path.isdir(os.path.join(self.temp_dir, d))]
                if len(subdirs) == 1:
                    logger.info(f"Alternatif çıkarılan dizin kullanılıyor: {subdirs[0]}")
                    self.extract_dir = os.path.join(self.temp_dir, subdirs[0])
                else:
                     logger.error(f"Çıkarılan dizin yapısı anlaşılamadı: {self.temp_dir}")
                     self.cleanup()
                     return False
            
            # Meta verileri güncelle
            self._update_metadata_from_desktop_file() 
            
            # Kurulum dizinini şimdi belirle (isim güncellenmiş olabilir)
            self.app_install_dir = self._get_app_specific_install_dir()
            logger.info(f"Uygulama kurulum dizini: {self.app_install_dir}")
            
            return True
        except Exception as e:
            logger.error(f"AppImage çıkarma sırasında hata: {e}")
            self.cleanup()
            return False
    
    def _update_metadata_from_desktop_file(self):
        """Çıkarılan desktop dosyasından meta verileri günceller.
           Uses configparser for more robust parsing.
        """
        if not self.extract_dir:
            return
            
        desktop_file_path = None
        # Prioritize finding .desktop file in standard locations
        potential_paths = [
            os.path.join(self.extract_dir, "usr", "share", "applications"),
            self.extract_dir
        ]
        
        for base_path in potential_paths:
             if os.path.isdir(base_path):
                 for item in os.listdir(base_path):
                     if item.lower().endswith(".desktop"):
                         desktop_file_path = os.path.join(base_path, item)
                         # Use the first one found in preferred locations
                         break
             if desktop_file_path:
                 break

        # Fallback: search entire extracted directory if not found above
        if not desktop_file_path:
             for root, _, files in os.walk(self.extract_dir):
                 for file in files:
                     if file.lower().endswith(".desktop"):
                         desktop_file_path = os.path.join(root, file)
                         break
                 if desktop_file_path:
                     break
                         
        if not desktop_file_path:
            logger.warning("Desktop dosyası bulunamadı.")
            return
            
        logger.info(f"Desktop dosyası bulundu: {desktop_file_path}")
        self.extracted_desktop_path = desktop_file_path # Store the path found - renamed for clarity
        
        # Parse using configparser
        parser = configparser.ConfigParser(interpolation=None)
        # Prevent lowercasing of keys
        parser.optionxform = str 
        try:
            # Read file, handling potential encoding issues if possible
            with open(desktop_file_path, 'r', encoding='utf-8') as f:
                parser.read_file(f)
                
            if "Desktop Entry" in parser:
                entry = parser["Desktop Entry"]
                self.app_info["name"] = entry.get("Name", self.app_info["name"]) # Keep fallback if missing
                self.app_info["description"] = entry.get("Comment", entry.get("GenericName", self.app_info["description"]))
                # Safely get icon name, provide empty string default
                self.app_info["icon_name"] = entry.get("Icon", "") 
                self.app_info["categories"] = [cat.strip() for cat in entry.get("Categories", "").split(';') if cat.strip()]
                
                # Handle Exec path carefully - store for later modification
                exec_val = entry.get("Exec", "")
                # Remove potential arguments like %U, %f, etc.
                exec_cmd_full = exec_val.split(' %')[0].strip()
                
                # Store the original Exec command - we'll modify the desktop file after copying
                self.app_info["original_exec"] = exec_cmd_full
                logger.debug(f"Original Exec command: {exec_cmd_full}")
                
                # --- Determine relative executable path --- 
                self.app_info["exec_relative"] = "" # Initialize
                if exec_cmd_full:
                     # If it starts with '/', it's likely absolute *within the extract dir* context, 
                     # but we need it relative to the extract_dir root or extract_dir/usr.
                     # Heuristic: Remove leading './' or assume relative if no leading '/' after initial check
                     if exec_cmd_full.startswith("./"):
                          self.app_info["exec_relative"] = exec_cmd_full[2:]
                     elif not exec_cmd_full.startswith("/"):
                          # Assume it's relative to a standard bin path or root
                          self.app_info["exec_relative"] = exec_cmd_full
                     else:
                          # It starts with '/', try to make it relative to expected roots
                          # This part is tricky as AppImages vary. Check common structures.
                          try:
                               if self.extract_dir:
                                   if exec_cmd_full.startswith(os.path.join(self.extract_dir, "usr")):
                                        rel_path = os.path.relpath(exec_cmd_full, os.path.join(self.extract_dir, "usr"))
                                        self.app_info["exec_relative"] = rel_path if rel_path != '.' else ""
                                   elif exec_cmd_full.startswith(self.extract_dir):
                                        rel_path = os.path.relpath(exec_cmd_full, self.extract_dir)
                                        self.app_info["exec_relative"] = rel_path if rel_path != '.' else ""
                                   else:
                                       # Fallback: Use the full command, hoping _determine_final_paths can find it
                                       logger.warning(f"Could not determine relative path for Exec='{exec_cmd_full}'. Using as is.")
                                       self.app_info["exec_relative"] = exec_cmd_full # Keep original if unsure
                          except Exception as rel_err:
                               logger.error(f"Error calculating relative exec path: {rel_err}")
                               self.app_info["exec_relative"] = exec_cmd_full # Fallback
                
                # Attempt to get version if available
                self.app_info["version"] = entry.get("Version", self.app_info["version"]) # Standard .desktop Version key is usually spec version, not app version
                # Sometimes X-AppImage-Version is used
                self.app_info["version"] = entry.get("X-AppImage-Version", self.app_info["version"])
                
                logger.debug(f"Desktop file parsed: Name={self.app_info['name']}, Icon={self.app_info['icon_name']}, Exec={self.app_info['exec_relative']}")
            else:
                 logger.warning(f"Desktop dosyasında [Desktop Entry] bölümü bulunamadı: {desktop_file_path}")

        except configparser.Error as e:
            logger.error(f"Desktop dosyası ayrıştırılırken hata ({desktop_file_path}): {e}")
        except Exception as e:
            logger.error(f"Desktop dosyası okunurken hata ({desktop_file_path}): {e}")
    
    def install_files(self):
        """Çıkarılan dosyaları uygulamaya özel dizine kopyalar."""
        if not self.extract_dir or not os.path.isdir(self.extract_dir):
            logger.error("Kurulum yapılacak çıkarılmış dizin yok")
            return False
        if not self.app_install_dir:
             logger.error("Uygulamaya özel kurulum dizini belirlenmedi.")
             return False
             
        source_dir = os.path.join(self.extract_dir, "usr")
        if not os.path.isdir(source_dir):
            source_dir = self.extract_dir 
            logger.info(f'\'usr\' dizini yok, \'{source_dir}\' kök dizini kopyalanacak.')
            
        target_dir = self.app_install_dir
        logger.info(f"Dosyalar \'{source_dir}\' dizininden \'{target_dir}\' altına kopyalanıyor (shutil.copytree)..." + (" (root gerekebilir)" if self.requires_root else ""))
        
        try:
            # --- Prepare Target Directory --- 
            # If the target directory exists from a previous attempt, remove it first for a clean copy
            # This only applies to non-root installs, as root installs use rsync via sudo
            if not self.requires_root and os.path.exists(target_dir):
                 logger.warning(f"Target directory '{target_dir}' already exists. Removing it before copying.")
                 try:
                     shutil.rmtree(target_dir)
                 except Exception as rmtree_err:
                      logger.error(f"Failed to remove existing target directory '{target_dir}': {rmtree_err}")
                      # Propagate error, as copytree would likely fail anyway
                      raise RuntimeError(f"Could not clear existing target directory: {target_dir}") from rmtree_err

            # --- Perform Copy (Non-root only) --- 
            # If root is required, the actual file copy needs to be done via sudo
            if not self.requires_root:
                # Ensure parent of target exists (makedirs handles this, but good practice)
                os.makedirs(os.path.dirname(target_dir), exist_ok=True)
                # Now copy cleanly
                shutil.copytree(source_dir, target_dir, dirs_exist_ok=True, symlinks=True)
                logger.info(f"Dosyalar başarıyla kopyalandı (non-root).")
                
                # Set final paths based on copied files
                self._determine_final_paths()
                
                # Now update the desktop file's Exec= line to point to the binary symlink
                if self.final_desktop_path and self.bin_symlink_target and os.path.exists(self.final_desktop_path):
                    self._update_desktop_file_exec()
                else:
                    logger.warning(f"Cannot update desktop file Exec line: final_desktop_path={self.final_desktop_path}, bin_symlink_target={self.bin_symlink_target}, exists={os.path.exists(self.final_desktop_path) if self.final_desktop_path else False}")
                
                return True
            else:
                # For root installs, the copy happens via sudo rsync later
                # We just need to determine the *potential* final paths now for symlink commands
                logger.info("Root kurulumu: Dosya kopyalama sudo rsync ile yapılacak.")
                self._determine_final_paths() # Determine paths based on expected structure
                return True # Return True, assuming sudo step will handle copy
            
        except Exception as e:
            logger.error(f"Dosya kopyalama/path belirleme sırasında hata: {e}")
            logger.error(traceback.format_exc())
            # Attempt to clean up partially created directory if non-root
            if not self.requires_root and os.path.isdir(target_dir):
                try:
                    shutil.rmtree(target_dir)
                except Exception as cleanup_err:
                    logger.error(f"Kısmi kurulum dizini temizlenemedi: {cleanup_err}")
            return False
            
    def _determine_final_paths(self):
         """Kopyalama işleminden sonra NİHAİ dosya yollarını belirler (app_install_dir içinde)."""
         if not self.app_install_dir:
             logger.error("Nihai yollar belirlenemedi: app_install_dir ayarlanmadı.")
             return
             
         # Final Desktop Path (within app_install_dir)
         self.final_desktop_path = None
         if self.extracted_desktop_path:
             try:
                 # Find relative path from extract_dir to calculate path within app_install_dir
                 base_extract = os.path.join(self.extract_dir, "usr") if os.path.exists(os.path.join(self.extract_dir, "usr")) else self.extract_dir
                 rel_desktop_path = os.path.relpath(self.extracted_desktop_path, base_extract)
                 self.final_desktop_path = os.path.join(self.app_install_dir, rel_desktop_path)
                 logger.debug(f"Calculated final desktop path: {self.final_desktop_path}")
             except ValueError as e:
                 logger.error(f"Göreli desktop yolu hesaplanırken hata: {e}")
                 self.final_desktop_path = None # Ensure it's None on error

         # Final Executable Path (within app_install_dir)
         self.final_executable_path = None
         exec_relative = self.app_info.get("exec_relative")
         if exec_relative:
             # Assume executable is relative to app_install_dir root or common subdirs
             potential_paths = [
                 os.path.join(self.app_install_dir, exec_relative),
                 os.path.join(self.app_install_dir, "bin", exec_relative),
                 os.path.join(self.app_install_dir, "usr", "bin", exec_relative)
             ]
             for path in potential_paths:
                 # Don't check os.exists for root yet, just construct the most likely path
                 # Check needs to happen after potential sudo rsync
                 # Heuristic: prefer path under bin if multiple could match
                 if "/bin/" in path:
                     self.final_executable_path = path
                     break
             
             # If not found with bin in path, use the first potential path
             if not self.final_executable_path and potential_paths:
                  self.final_executable_path = potential_paths[0]
             
             logger.debug(f"Calculated final executable path: {self.final_executable_path}")
         else:
             logger.warning("Could not determine final executable path: No relative path available")

         # Calculate binary symlink target path (for later desktop file modification)
         self.bin_symlink_target = None
         if self.app_info.get("name"):
             clean_name = sanitize_name(self.app_info["name"])
             self.bin_symlink_target = os.path.join(self.bin_link_dir, clean_name)
             logger.debug(f"Binary symlink target will be: {self.bin_symlink_target}")
         else:
             logger.warning("Could not determine binary symlink target: No app name")

         # Final Icon Path (within app_install_dir)
         self.final_icon_path = None
         icon_name = self.app_info.get("icon_name")
         if icon_name:
             # Search for the icon file in common locations within app_install_dir
             # Use a heuristic to find the largest/best icon
             search_bases = [
                 os.path.join(self.app_install_dir, "share", "icons"),
                 os.path.join(self.app_install_dir, "usr", "share", "icons"), 
                 self.app_install_dir 
             ]
             best_icon_path = None
             max_size = 0

             for base in search_bases:
                 if not os.path.isdir(base):
                     continue # This check might fail for root before rsync
                 
                 # Construct potential paths without os.path.exists for now
                 hicolor_path = os.path.join(base, "hicolor")
                 # Check common png/svg extensions
                 for ext in [".png", ".svg", ".svgz"]:
                     # Check base path directly
                     potential_icon = os.path.join(base, f"{icon_name}{ext}")
                     # Prioritize SVG, then largest PNG found so far
                     if ext.startswith(".svg"):
                          best_icon_path = potential_icon # Prefer SVG
                          break # Stop searching extensions if SVG found
                     elif not best_icon_path or ext == ".png": # Check PNG if no SVG or current best is PNG
                          if os.path.exists(potential_icon): # Check existence for non-hicolor PNG
                             best_icon_path = potential_icon
                             # Don't break, look for larger hicolor PNGs

                 # Search hicolor for PNGs (prefer larger)
                 if os.path.isdir(hicolor_path): # Check might fail for root
                     size_dirs = [d for d in os.listdir(hicolor_path) if d.endswith("x"+d.split('x')[0])] # Heuristic
                     for size_dir in sorted(size_dirs, key=lambda s: int(s.split('x')[0]), reverse=True):
                         try:
                              current_size = int(size_dir.split('x')[0])
                              if current_size < max_size: continue # Don't bother with smaller
                              
                              apps_path = os.path.join(hicolor_path, size_dir, "apps")
                              potential_icon_hicolor = os.path.join(apps_path, f"{icon_name}.png")
                              # Don't check os.path.exists yet for root
                              # Assume path structure is correct for now
                              # if os.path.exists(potential_icon_hicolor):
                              if current_size > max_size:
                                     max_size = current_size
                                     best_icon_path = potential_icon_hicolor
                         except (ValueError, IndexError, FileNotFoundError): # Handle potential errors
                              continue 
                 if best_icon_path and best_icon_path.endswith(".svg"): break # Stop searching bases if SVG found

             self.final_icon_path = best_icon_path
             if self.final_icon_path:
                 logger.info(f"Nihai ikon dosyası yolu belirlendi: {self.final_icon_path}")
             else:
                 logger.warning(f"İkon dosyası yolu belirlenemedi (İsim: '{icon_name}', Dizin: {self.app_install_dir})")

    def _update_desktop_file_exec(self):
        """Update the Exec= and Icon= lines in the final desktop file"""
        try:
            if not self.final_desktop_path or not os.path.exists(self.final_desktop_path):
                logger.error(f"Cannot update desktop file: {self.final_desktop_path} does not exist")
                return False
                
            if not self.bin_symlink_target:
                logger.error("Cannot update desktop file: No binary symlink target defined")
                return False
                
            logger.info(f"Updating desktop file at {self.final_desktop_path}")
            
            # Use configparser to read the desktop file
            parser = configparser.ConfigParser(interpolation=None)
            parser.optionxform = str  # Preserve case
            
            with open(self.final_desktop_path, 'r', encoding='utf-8') as f:
                parser.read_file(f)
                
            if "Desktop Entry" in parser:
                entry = parser["Desktop Entry"]
                
                # Update Exec line
                original_exec = entry.get("Exec", "")
                if original_exec:
                    parts = original_exec.split(' %')
                    if len(parts) > 1:
                        # Has arguments
                        new_exec = f"{self.bin_symlink_target} %{parts[1]}"
                    else:
                        # No arguments
                        new_exec = self.bin_symlink_target
                        
                    entry["Exec"] = new_exec
                    logger.debug(f"Updated Exec line: '{original_exec}' -> '{new_exec}'")
                else:
                    logger.warning("No Exec line found in desktop file")
                     
                # Update the Icon line - prefer system icon paths for better compatibility
                original_icon = entry.get("Icon", "")
                icon_name = self.app_info.get("icon_name", "")
                
                if hasattr(self, 'standard_icon_path') and self.standard_icon_path:
                    # If we've copied the icon to a standard location, use that path
                    entry["Icon"] = self.standard_icon_path
                    logger.debug(f"Updated Icon line to standard path: '{original_icon}' -> '{self.standard_icon_path}'")
                elif self.final_icon_path and os.path.exists(self.final_icon_path):
                    # Fallback to direct path to the icon in the installation directory
                    entry["Icon"] = self.final_icon_path
                    logger.debug(f"Updated Icon line to direct path: '{original_icon}' -> '{self.final_icon_path}'")
                elif icon_name:
                    # Keep original icon name as last resort, as it might be found in system paths
                    logger.debug(f"Keeping original icon name: '{original_icon}'")
                else:
                    logger.warning(f"Cannot update Icon: No suitable icon path or name found")
                
                # Write the updated desktop file
                with open(self.final_desktop_path, 'w', encoding='utf-8') as f:
                    parser.write(f)
                    
                logger.info(f"Successfully updated desktop file")
                return True
            else:
                logger.warning("No [Desktop Entry] section found in desktop file")
                
            return False
        except Exception as e:
            logger.error(f"Error updating desktop file: {e}")
            logger.error(traceback.format_exc())
            return False

    def create_symlinks(self):
        """Gerekli sembolik bağları oluşturur (root olmayan)."""
        if self.requires_root:
            logger.error("create_symlinks root olmayan kurulumlar için çağrıldı.")
            return False
        if not self.app_install_dir:
            logger.error("Symlink oluşturulamadı: Kurulum dizini yok.")
            return False
            
        self.symlinks_created = []
        success = True

        try:
            # Ensure target directories exist
            logger.debug(f"Creating symlink target directories: {self.bin_link_dir}, {self.desktop_link_dir}")
            os.makedirs(self.bin_link_dir, exist_ok=True)
            os.makedirs(self.desktop_link_dir, exist_ok=True)
            
            # Also create standard icon directories
            os.makedirs(os.path.join(config.USER_HOME, ".local/share/icons/hicolor/scalable/apps"), exist_ok=True)
            os.makedirs(os.path.join(config.USER_HOME, ".local/share/icons/hicolor/128x128/apps"), exist_ok=True)
        except OSError as e:
            logger.error(f"Symlink dizinleri oluşturulamadı: {e}")
            return False
            
        # --- Copy Icon to Standard Location ---
        if self.final_icon_path and os.path.exists(self.final_icon_path):
            icon_name = self.app_info.get("icon_name", "")
            if not icon_name:
                icon_name = sanitize_name(self.app_info.get("name", "unknown"))
                
            # Determine target based on file type
            icon_ext = os.path.splitext(self.final_icon_path)[1].lower()
            if icon_ext in ['.svg', '.svgz']:
                # SVG icons go to scalable directory
                target_icon_dir = os.path.join(config.USER_HOME, ".local/share/icons/hicolor/scalable/apps")
                target_icon_path = os.path.join(target_icon_dir, f"{icon_name}{icon_ext}")
            else:
                # PNG and other bitmap icons go to size-specific directory or 128x128 as fallback
                target_icon_dir = os.path.join(config.USER_HOME, ".local/share/icons/hicolor/128x128/apps")
                target_icon_path = os.path.join(target_icon_dir, f"{icon_name}{icon_ext}")
                
            try:
                # Copy icon to standard location
                logger.debug(f"Copying icon to system location: {self.final_icon_path} -> {target_icon_path}")
                shutil.copy2(self.final_icon_path, target_icon_path)
                logger.info(f"Icon copied to standard location: {target_icon_path}")
                
                # Save the standard icon path for desktop file update
                self.standard_icon_path = target_icon_path
                self.symlinks_created.append(target_icon_path)  # Track for potential cleanup
            except Exception as e:
                logger.error(f"Failed to copy icon to standard location: {e}")
                self.standard_icon_path = None
        else:
            logger.warning(f"Cannot copy icon: final_icon_path={self.final_icon_path}, exists={os.path.exists(self.final_icon_path) if self.final_icon_path else False}")
            self.standard_icon_path = None
            
        # --- Search for additional icons in the hicolor directory ---
        try:
            hicolor_dir = os.path.join(self.app_install_dir, "share/icons/hicolor")
            if not os.path.exists(hicolor_dir):
                hicolor_dir = os.path.join(self.app_install_dir, "usr/share/icons/hicolor")
                
            if os.path.exists(hicolor_dir):
                # Find all PNG icons in hicolor directory
                icon_name = self.app_info.get("icon_name", "")
                if icon_name:
                    logger.debug(f"Searching for additional icons in hicolor directory: {hicolor_dir}")
                    for size_dir in os.listdir(hicolor_dir):
                        size_path = os.path.join(hicolor_dir, size_dir)
                        if os.path.isdir(size_path) and size_dir.endswith("x" + size_dir.split("x")[0]):
                            # This is a size directory like "128x128"
                            apps_dir = os.path.join(size_path, "apps")
                            if os.path.isdir(apps_dir):
                                for icon_file in os.listdir(apps_dir):
                                    if icon_file.startswith(icon_name + ".") and icon_file.endswith((".png", ".svg", ".svgz")):
                                        src_icon = os.path.join(apps_dir, icon_file)
                                        # Create target path in user's hicolor directory
                                        target_icon_dir = os.path.join(config.USER_HOME, ".local/share/icons/hicolor", size_dir, "apps")
                                        os.makedirs(target_icon_dir, exist_ok=True)
                                        target_icon = os.path.join(target_icon_dir, icon_file)
                                        # Copy the icon
                                        shutil.copy2(src_icon, target_icon)
                                        logger.debug(f"Copied additional icon: {src_icon} -> {target_icon}")
                                        if not hasattr(self, 'standard_icon_path') or not self.standard_icon_path:
                                            self.standard_icon_path = target_icon
        except Exception as e:
            logger.error(f"Error searching for additional icons: {e}")

        # --- Executable Symlink --- 
        if self.final_executable_path and self.bin_symlink_target:
            link_name = self.bin_symlink_target
            try:
                if os.path.lexists(link_name):
                     logger.debug(f"Removing existing symlink: {link_name}")
                     os.remove(link_name)
                logger.debug(f"Creating executable symlink: {link_name} -> {self.final_executable_path}")
                os.symlink(self.final_executable_path, link_name)
                self.symlinks_created.append(link_name)
                logger.info(f"Çalıştırılabilir symlink oluşturuldu: {link_name} -> {self.final_executable_path}")
            except (OSError, PermissionError) as e:
                 logger.error(f"Çalıştırılabilir symlink oluşturulamadı: {e}")
                 success = False
        else:
             logger.warning("Çalıştırılabilir symlink oluşturulamadı: Nihai yol bulunamadı.")
             logger.debug(f"final_executable_path={self.final_executable_path}, bin_symlink_target={self.bin_symlink_target}")

        # --- Desktop File Symlink --- 
        desktop_link_path = None
        if self.final_desktop_path:
            desktop_filename = os.path.basename(self.final_desktop_path)
            desktop_link_path = os.path.join(self.desktop_link_dir, desktop_filename)
            try:
                if os.path.lexists(desktop_link_path):
                     logger.debug(f"Removing existing desktop symlink: {desktop_link_path}")
                     os.remove(desktop_link_path)
                logger.debug(f"Creating desktop symlink: {desktop_link_path} -> {self.final_desktop_path}")
                os.symlink(self.final_desktop_path, desktop_link_path)
                self.symlinks_created.append(desktop_link_path)
                logger.info(f"Desktop symlink oluşturuldu: {desktop_link_path} -> {self.final_desktop_path}")
                
                # Update the desktop file AFTER creating the symlink
                # This is important because we need to update the symlink target
                self._update_desktop_link_file(desktop_link_path)
                
                self._update_desktop_database()
            except (OSError, PermissionError) as e:
                 logger.error(f"Desktop symlink oluşturulamadı: {e}")
                 success = False
        else:
            logger.warning("Desktop symlink oluşturulamadı: Nihai yol bulunamadı.")
            
        # Update icon cache
        if shutil.which("gtk-update-icon-cache"):
            try:
                subprocess.run(["gtk-update-icon-cache", "-f", "-t", 
                               os.path.join(config.USER_HOME, ".local/share/icons/hicolor")], 
                              check=False, capture_output=True)
                logger.info("Icon cache updated")
            except Exception as e:
                logger.warning(f"Failed to update icon cache: {e}")
            
        return success

    def _update_desktop_link_file(self, desktop_link_path):
        """Update the Exec= and Icon= lines in the symlinked desktop file (not the original)"""
        if not desktop_link_path or not os.path.exists(desktop_link_path):
            logger.error(f"Cannot update desktop link file: {desktop_link_path} does not exist")
            return False
            
        try:
            logger.info(f"Updating desktop link file at {desktop_link_path}")
            
            # Read the file directly instead of using configparser to preserve formatting
            with open(desktop_link_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
                
            with open(desktop_link_path, 'w', encoding='utf-8') as f:
                for line in lines:
                    # Update Exec line
                    if line.strip().startswith("Exec="):
                        new_line = f"Exec={self.bin_symlink_target}\n"
                        f.write(new_line)
                        logger.debug(f"Updated Exec line: '{line.strip()}' -> '{new_line.strip()}'")
                    # Update Icon line
                    elif line.strip().startswith("Icon="):
                        if hasattr(self, 'standard_icon_path') and self.standard_icon_path:
                            new_line = f"Icon={self.standard_icon_path}\n"
                        elif self.final_icon_path:
                            new_line = f"Icon={self.final_icon_path}\n"
                        else:
                            # Keep original line if no icon found
                            new_line = line
                        f.write(new_line)
                        logger.debug(f"Updated Icon line: '{line.strip()}' -> '{new_line.strip()}'")
                    else:
                        # Keep other lines as is
                        f.write(line)
                        
            logger.info(f"Successfully updated desktop link file")
            return True
        except Exception as e:
            logger.error(f"Error updating desktop link file: {e}")
            logger.error(traceback.format_exc())
            return False

    def _update_desktop_database(self):
        """Masaüstü veritabanını günceller (eğer komut varsa)."""
        if shutil.which("update-desktop-database"): 
            try:
                subprocess.run(["update-desktop-database", self.desktop_link_dir], check=False, capture_output=True)
                logger.info(f"Masaüstü veritabanı güncellendi: {self.desktop_link_dir}")
            except Exception as e:
                 logger.warning(f"'update-desktop-database' çalıştırılırken hata: {e}")
        else:
             logger.warning("'update-desktop-database' komutu bulunamadı, veritabanı güncellenmedi.")

    def get_install_commands(self):
        """Root yetkisiyle çalıştırılması GEREKEN kurulum komutlarını döndürür.\n           (Dosya kopyalama için rsync ve symlink oluşturma)."""
        if not self.requires_root:
            return [] # Non-root uses install_files + create_symlinks directly
            
        commands = []
        
        # 1. Ensure base install directory exists 
        commands.append(f"mkdir -p \"{self.base_install_prefix}\"")
        # 2. Ensure app install directory exists 
        if self.app_install_dir:
             commands.append(f"mkdir -p \"{self.app_install_dir}\"")
        else:
             logger.error("Root komutları oluşturulamıyor: app_install_dir ayarlanmadı")
             return []
             
        # 3. Copy files using rsync
        source_dir = os.path.join(self.extract_dir, "usr")
        if not os.path.isdir(source_dir):
            source_dir = self.extract_dir
        if not source_dir.endswith('/'): source_dir += '/'
        target_dir = self.app_install_dir
        if not target_dir.endswith('/'): target_dir += '/'
        commands.append(f"rsync -a --exclude='.union' --exclude='.DirIcon' \"{source_dir}\" \"{target_dir}\"")
        
        # 4. Ensure link and icon directories exist 
        commands.append(f"mkdir -p \"{self.bin_link_dir}\"")
        commands.append(f"mkdir -p \"{self.desktop_link_dir}\"")
        commands.append(f"mkdir -p \"{os.path.join(config.USER_HOME, '.local/share/icons/hicolor/scalable/apps')}\"")
        commands.append(f"mkdir -p \"{os.path.join(config.USER_HOME, '.local/share/icons/hicolor/128x128/apps')}\"")

        # 5. Copy icon to standard location for system installs
        if self.final_icon_path:
            icon_name = self.app_info.get("icon_name", "")
            if not icon_name:
                icon_name = sanitize_name(self.app_info.get("name", "unknown"))
                
            # Determine target based on expected file type
            icon_ext = os.path.splitext(self.final_icon_path)[1].lower()
            if icon_ext in ['.svg', '.svgz']:
                target_icon_dir = os.path.join(config.USER_HOME, ".local/share/icons/hicolor/scalable/apps")
            else:
                target_icon_dir = os.path.join(config.USER_HOME, ".local/share/icons/hicolor/128x128/apps")
                
            target_icon_path = os.path.join(target_icon_dir, f"{icon_name}{icon_ext}")
            commands.append(f"if [ -f \"{self.final_icon_path}\" ]; then cp \"{self.final_icon_path}\" \"{target_icon_path}\"; fi")
            self.standard_icon_path = target_icon_path
            logger.debug(f"Added command to copy icon: {self.final_icon_path} -> {target_icon_path}")
        
        # 6. Update desktop file Exec line and Icon line after files are copied
        if self.final_desktop_path and self.bin_symlink_target:
            # Update Exec line
            commands.append(f"if [ -f \"{self.final_desktop_path}\" ]; then sed -i 's|^Exec=.*|Exec={self.bin_symlink_target}|g' \"{self.final_desktop_path}\"; fi")
            logger.debug(f"Added command to update desktop file Exec line: {self.final_desktop_path} -> {self.bin_symlink_target}")
            
            # Update Icon line if we have a standard icon path
            if hasattr(self, 'standard_icon_path') and self.standard_icon_path:
                commands.append(f"if [ -f \"{self.final_desktop_path}\" ]; then sed -i 's|^Icon=.*|Icon={self.standard_icon_path}|g' \"{self.final_desktop_path}\"; fi")
                logger.debug(f"Added command to update desktop file Icon line: {self.final_desktop_path} -> {self.standard_icon_path}")
            elif self.final_icon_path:
                commands.append(f"if [ -f \"{self.final_desktop_path}\" ]; then sed -i 's|^Icon=.*|Icon={self.final_icon_path}|g' \"{self.final_desktop_path}\"; fi")
                logger.debug(f"Added command to update desktop file Icon line: {self.final_desktop_path} -> {self.final_icon_path}")
        else:
            logger.warning(f"Cannot add desktop file update command: final_desktop_path={self.final_desktop_path}, bin_symlink_target={self.bin_symlink_target}")

        # 7. Symlink commands 
        # Executable
        if self.final_executable_path and self.bin_symlink_target: # Path determined before calling this
            commands.append(f"ln -sf \"{self.final_executable_path}\" \"{self.bin_symlink_target}\"")
            # Add link to list *before* potentially failing sudo command
            self.symlinks_created.append(self.bin_symlink_target)
            logger.debug(f"Added command to create executable symlink: {self.bin_symlink_target} -> {self.final_executable_path}")
        else:
             logger.warning("Root için çalıştırılabilir symlink komutu oluşturulamadı: Nihai yol yok.")
             logger.debug(f"final_executable_path={self.final_executable_path}, bin_symlink_target={self.bin_symlink_target}")
            
        # Desktop File
        if self.final_desktop_path: # Path determined before calling this
            desktop_filename = os.path.basename(self.final_desktop_path)
            link_name = os.path.join(self.desktop_link_dir, desktop_filename)
            commands.append(f"ln -sf \"{self.final_desktop_path}\" \"{link_name}\"")
            self.symlinks_created.append(link_name)
            logger.debug(f"Added command to create desktop symlink: {link_name} -> {self.final_desktop_path}")
        else:
             logger.warning("Root için desktop symlink komutu oluşturulamadı: Nihai yol yok.")

        # 8. Update desktop database and icon cache
        if self.final_desktop_path and shutil.which("update-desktop-database"): # Check if link was created
            commands.append(f"update-desktop-database \"{self.desktop_link_dir}\"")
        
        # Update icon cache if any icons were copied
        if hasattr(self, 'standard_icon_path') and self.standard_icon_path and shutil.which("gtk-update-icon-cache"):
            commands.append(f"gtk-update-icon-cache -f -t \"{os.path.join(config.USER_HOME, '.local/share/icons/hicolor')}\"")
            
        logger.info(f"Oluşturulan root kurulum komutları: {len(commands)} adet")
        return commands

    def cleanup(self):
        """Geçici dosyaları temizler."""
        try:
            if self.temp_dir and os.path.isdir(self.temp_dir):
                logger.info(f"Geçici dizin temizleniyor: {self.temp_dir}")
                shutil.rmtree(self.temp_dir)
                self.temp_dir = None
                self.extract_dir = None
                return True
        except Exception as e:
            logger.error(f"Temizlik sırasında hata: {e}")
            return False
        return True # Return True if already cleaned or nothing to clean
    
    def get_installation_info(self):
        """Kurulum sonrası veritabanına kaydedilecek bilgileri döndürür."""
        info = self.app_info.copy()
        # Generate ID here before returning? Or expect it to be added by DBManager?
        # Let's assume DBManager adds it for consistency.
        # info["id"] = str(uuid.uuid4()) 
        info["app_install_dir"] = self.app_install_dir
        info["symlinks_created"] = self.symlinks_created
        
        # Executable symlink path (where user launches from)
        if self.symlinks_created and self.bin_link_dir in self.symlinks_created[0]:
             info["executable_path"] = self.symlinks_created[0]
        elif self.final_executable_path: # Fallback if symlink failed? Unlikely needed.
             info["executable_path"] = self.final_executable_path # This is inside app dir
        else: 
             info["executable_path"] = None
             
        # Desktop file symlink path
        desktop_link = None
        for link in self.symlinks_created:
             if link.startswith(self.desktop_link_dir):
                 desktop_link = link
                 break
        info["desktop_file"] = desktop_link

        # Icon path (within the app_install_dir)
        info["icon_path"] = self.final_icon_path 
        
        # Add determined version if not unknown
        if self.app_info.get("version") == "unknown":
             info.pop("version", None)
             
        # Remove fields not needed in DB
        info.pop("exec_relative", None)
        info.pop("icon_name", None)
        
        return info


class AppImageUninstaller:
    """Kurulu bir AppImage uygulamasını kaldırır."""
    
    def __init__(self, app_info):
        """Kaldırma işlemi için başlangıç.
        
        Args:
            app_info (dict): Kaldırılacak uygulamanın bilgilerini içeren sözlük
        """
        self.app_info = app_info
        # Determine paths from app_info
        self.app_install_dir = self.app_info.get("app_install_dir")
        self.symlinks = self.app_info.get("symlinks_created", [])
        self.install_mode = self.app_info.get("install_mode", "user") # Default to user if missing
        
        self.requires_root = self._check_if_root_required()
    
    def _check_if_root_required(self):
        """Kaldırma işlemi için root yetkisi gerekip gerekmediğini kontrol eder."""
        # If install mode was system, root is required
        if self.install_mode == "system":
            return True
            
        # Check write access for app_install_dir parent
        if self.app_install_dir and not self._can_write_to_parent(self.app_install_dir):
             logger.debug(f"Root required to remove install directory: {self.app_install_dir}")
             return True
             
        # Check write access for symlink parent directories
        for link in self.symlinks:
            if not self._can_write_to_parent(link):
                 logger.debug(f"Root required to remove symlink: {link}")
                 return True
                 
        return False # Assume user mode or custom path with write access

    def _can_write_to_parent(self, path):
        """Check if the parent directory of a path is writable."""
        if not path: return False
        parent = os.path.dirname(path)
        if not parent: parent = '/' # Handle root case
        return os.path.exists(parent) and os.access(parent, os.W_OK)

    def uninstall(self):
        """Uygulamayı kaldırır (root olmayan). Eğer root gerekiyorsa False döndürür.
           Root gerektiren kaldırma işlemleri için get_uninstall_commands kullanılmalıdır.
        """
        if self.requires_root:
            logger.error("Uninstall called directly but root privileges are required. Use get_uninstall_commands.")
            return False # Indicate failure or need for sudo commands
            
        logger.info(f"Uninstalling '{self.app_info.get('name', 'Unknown App')}' (non-root)...")
        success = True
        removed_items = []

        try:
            # 1. Remove symlinks
            for link_path in self.symlinks:
                if os.path.lexists(link_path): # Use lexists for symlinks
                    try:
                        os.remove(link_path)
                        logger.info(f"Symlink silindi: {link_path}")
                        removed_items.append(link_path)
                    except (PermissionError, OSError) as e:
                        logger.warning(f"Symlink silinemedi: {link_path}, {e}")
                        success = False # Mark as partially failed but continue
                else:
                    logger.debug(f"Symlink bulunamadı (zaten silinmiş olabilir): {link_path}")

            # 2. Remove installation directory
            if self.app_install_dir and os.path.exists(self.app_install_dir):
                try:
                    shutil.rmtree(self.app_install_dir)
                    logger.info(f"Kurulum dizini silindi: {self.app_install_dir}")
                    removed_items.append(self.app_install_dir)
                except (PermissionError, OSError) as e:
                    logger.error(f"Kurulum dizini silinemedi: {self.app_install_dir}, {e}")
                    success = False
            elif self.app_install_dir:
                 logger.debug(f"Kurulum dizini bulunamadı (zaten silinmiş olabilir): {self.app_install_dir}")

            # 3. Update desktop database and icon cache (best effort)
            if any(link.endswith(".desktop") for link in removed_items):
                self._update_desktop_database()
            if any(".local/share/icons" in item for item in removed_items):
                self._update_icon_cache()

            logger.info(f"Kaldırma tamamlandı: {len(removed_items)} öğe silindi.")
            return success
        except Exception as e:
            logger.error(f"Kaldırma sırasında beklenmedik hata: {e}")
            logger.error(traceback.format_exc())
            return False

    def get_uninstall_commands(self):
        """Root yetkisiyle çalıştırılması GEREKEN kaldırma komutlarını döndürür."""
        if not self.requires_root:
            logger.warning("get_uninstall_commands called but root is not required.")
            return []
            
        logger.info(f"Generating uninstall commands for '{self.app_info.get('name', 'Unknown App')}' (root required)...")
        commands = []

        # 1. Remove symlinks command (use rm -f)
        for link_path in self.symlinks:
            commands.append(f"rm -f \"{link_path}\"")
            
        # 2. Remove installation directory command (use rm -rf)
        if self.app_install_dir:
            commands.append(f"rm -rf \"{self.app_install_dir}\"")
            
        # 3. Update desktop database and icon cache commands (if applicable)
        desktop_link_dir = None
        icon_cache_dir = None
        for link_path in self.symlinks:
            if link_path.endswith(".desktop"):
                 desktop_link_dir = os.path.dirname(link_path)
            if "/icons/" in link_path:
                 # Find the base icon directory (e.g., /usr/local/share/icons/hicolor)
                 # This is a heuristic, might need refinement
                 parts = link_path.split('/icons/')
                 if len(parts) > 1:
                     icon_base = os.path.dirname(parts[0] + '/icons/')
                     # Look for hicolor specifically
                     if os.path.basename(icon_base) == "icons":
                         icon_cache_dir = os.path.join(icon_base, "hicolor")
                     else:
                         icon_cache_dir = icon_base # Fallback
                 break # Assume one icon cache dir is enough
                
        if desktop_link_dir and shutil.which("update-desktop-database"): 
            commands.append(f"update-desktop-database \"{desktop_link_dir}\"")
        
        if icon_cache_dir and shutil.which("gtk-update-icon-cache"):
            commands.append(f"gtk-update-icon-cache -f -t \"{icon_cache_dir}\"")

        logger.info(f"Oluşturulan root kaldırma komutları: {len(commands)} adet")
        return commands

    def _update_desktop_database(self):
        """Masaüstü veritabanını günceller (root olmayan)."""
        desktop_link_dir = None
        for link in self.symlinks:
            if link.endswith(".desktop"):
                 # Assume user mode path
                 desktop_link_dir = os.path.dirname(link)
                 break
        
        if desktop_link_dir and shutil.which("update-desktop-database"): 
            try:
                subprocess.run(["update-desktop-database", desktop_link_dir], check=False, capture_output=True)
                logger.info(f"Masaüstü veritabanı güncellendi: {desktop_link_dir}")
            except Exception as e:
                 logger.warning(f"'update-desktop-database' çalıştırılırken hata: {e}")
        else:
             logger.debug("'update-desktop-database' komutu bulunamadı veya desktop link yok.")
            
    def _update_icon_cache(self):
        """İkon önbelleğini günceller (root olmayan)."""
        icon_cache_dir = None
        for link in self.symlinks:
            if ".local/share/icons" in link:
                # Heuristic to find the hicolor dir
                if "/hicolor/" in link:
                    icon_cache_dir = link.split('/hicolor/')[0] + '/hicolor'
                else: # Fallback: Use the parent dir containing .local/share/icons
                    icon_cache_dir = os.path.dirname(link.split('.local/share/icons')[0] + '.local/share/icons')
                break # Assume one dir is enough
        
        if icon_cache_dir and shutil.which("gtk-update-icon-cache"):
            try:
                # Update the specific hicolor directory or the base .local/share/icons
                target_dir = icon_cache_dir
                if not target_dir.endswith("hicolor"): # If we didn't find hicolor specifically
                     hicolor_check = os.path.join(target_dir, "hicolor")
                     if os.path.isdir(hicolor_check):
                         target_dir = hicolor_check
                        
                logger.info(f"Updating icon cache for directory: {target_dir}")
                subprocess.run(["gtk-update-icon-cache", "-f", "-t", target_dir], 
                              check=False, capture_output=True)
                logger.info("Icon cache updated")
            except Exception as e:
                logger.warning(f"Failed to update icon cache: {e}")
        else:
            logger.debug("Icon cache update skipped (command not found or no icons removed).")

def check_system_compatibility():
    """Sistem uyumluluğunu kontrol eder."""
    checks = {
        "is_ubuntu": False,
        "ubuntu_version": None,
        "libfuse_installed": False,
        "rsync_installed": False,
        "pkexec_installed": False # Check for pkexec for sudo helper
    }
    
    # Ubuntu'yu kontrol et
    try:
        result = subprocess.run(["lsb_release", "-d"], capture_output=True, text=True, check=False)
        if "Ubuntu" in result.stdout:
            checks["is_ubuntu"] = True
            
            # Sürümü kontrol et
            version_result = subprocess.run(["lsb_release", "-sr"], capture_output=True, text=True, check=False)
            checks["ubuntu_version"] = version_result.stdout.strip()
    except Exception:
        pass
    
    # libfuse'u kontrol et
    try:
        result = subprocess.run(
            ["dpkg-query", "-W", "-f='${Status}'", config.LIBFUSE_PACKAGE], 
            capture_output=True, 
            text=True, 
            check=False
        )
        checks["libfuse_installed"] = "install ok installed" in result.stdout
    except Exception:
        pass
    
    # rsync'i kontrol et
    try:
        result = subprocess.run(["which", "rsync"], capture_output=True, check=False)
        checks["rsync_installed"] = result.returncode == 0
    except Exception:
        pass
    
    # pkexec kontrol et (sudo_helper için önemli olabilir)
    try:
         checks["pkexec_installed"] = shutil.which("pkexec") is not None
    except Exception:
         pass
        
    return checks 

# --- Leftover File Management ---

def find_leftovers(app_name):
    """Find potential leftover files and directories for a given app name."""
    if not app_name:
        return []
        
    logger.info(f"Searching for potential leftovers for: {app_name}")
    potential_leftovers = []
    search_dirs = [
        os.path.join(config.USER_HOME, ".config"),
        os.path.join(config.USER_HOME, ".cache"),
        os.path.join(config.USER_HOME, ".local", "share")
    ]
    
    # Normalize app name for searching (lowercase, maybe sanitized?)
    # Using lowercase for case-insensitive comparison
    normalized_app_name = app_name.lower()
    # Also consider the sanitized version if different
    sanitized_app_name = sanitize_name(app_name).lower()
    search_terms = {normalized_app_name}
    if sanitized_app_name != normalized_app_name:
        search_terms.add(sanitized_app_name)
        
    logger.debug(f"Searching for terms: {search_terms} in dirs: {search_dirs}")

    for base_dir in search_dirs:
        if not os.path.isdir(base_dir):
            continue
            
        try:
            # Use os.scandir for potentially better performance than os.listdir+os.path
            for entry in os.scandir(base_dir):
                entry_name_lower = entry.name.lower()
                # Check if any search term is present in the entry name
                if any(term in entry_name_lower for term in search_terms):
                    # Heuristic: Avoid matching very common short names or system files
                    # Example: avoid matching 'qt' if app name is 'qtcreator' in ~/.config/qt* files
                    # This needs careful tuning to avoid false positives/negatives.
                    # For now, let's include if the app name is a distinct part.
                    # Simple check: if the found name is exactly one of the search terms
                    is_exact_match = entry_name_lower in search_terms
                    # Or if it starts with one of the search terms + common separators like -, _
                    starts_with_match = any(entry_name_lower.startswith(term + sep) for term in search_terms for sep in ["", "-", "_"])
                    
                    # Add path if it seems relevant (exact match or starts with app name)
                    if is_exact_match or starts_with_match:
                        if entry.path not in potential_leftovers: # Avoid duplicates
                           logger.debug(f"Found potential leftover: {entry.path}")
                           potential_leftovers.append(entry.path)
                       
                    # Potential Improvement: Walk deeper? Only if necessary, increases complexity/risk.
                    # if entry.is_dir():
                    #    # Recursively search inside? Might be too broad.
                    #    pass 
        except OSError as e:
            logger.warning(f"Could not scan directory {base_dir}: {e}")
            
    logger.info(f"Found {len(potential_leftovers)} potential leftover item(s).")
    return potential_leftovers

def remove_selected_leftovers(paths):
    """Remove the selected leftover files and directories."""
    if not paths:
        return True, 0
        
    logger.info(f"Removing selected leftover items: {len(paths)}")
    removed_count = 0
    errors = []

    for path in paths:
        try:
            if os.path.isfile(path) or os.path.islink(path):
                os.remove(path)
                logger.info(f"Removed leftover file/link: {path}")
                removed_count += 1
            elif os.path.isdir(path):
                shutil.rmtree(path)
                logger.info(f"Removed leftover directory: {path}")
                removed_count += 1
            else:
                logger.warning(f"Skipping leftover item (not file/dir/link or already removed): {path}")
        except (PermissionError, OSError) as e:
            logger.error(f"Failed to remove leftover item: {path}, Error: {e}")
            errors.append(f"{path}: {e}")
        except Exception as e:
            logger.error(f"Unexpected error removing leftover item: {path}, Error: {e}")
            logger.error(traceback.format_exc())
            errors.append(f"{path}: Unexpected error")
            
    if errors:
        logger.error(f"Errors occurred during leftover removal: {len(errors)} item(s)")
        # It might be useful to return the error details to the UI
        return False, removed_count # Indicate partial or full failure
    else:
        logger.info(f"Successfully removed {removed_count} leftover item(s).")
        return True, removed_count # Indicate success 

# --- Helper function for finding desktop file ---
def _find_desktop_file(extract_dir):
    """Finds the main .desktop file within an extracted directory."""
    desktop_file_path = None
    # Prioritize finding .desktop file in standard locations
    potential_paths = [
        os.path.join(extract_dir, "usr", "share", "applications"),
        extract_dir
    ]
    for base_path in potential_paths:
        if os.path.isdir(base_path):
            for item in os.listdir(base_path):
                if item.lower().endswith(".desktop"):
                    # Heuristic: Avoid entries like mimeinfo.cache
                    if 'mimeinfo' not in item.lower():
                        desktop_file_path = os.path.join(base_path, item)
                        break
        if desktop_file_path:
            break

    # Fallback: search entire extracted directory if not found above
    if not desktop_file_path:
        for root, _, files in os.walk(extract_dir):
            for file in files:
                if file.lower().endswith(".desktop") and 'mimeinfo' not in file.lower():
                    desktop_file_path = os.path.join(root, file)
                    break
            if desktop_file_path:
                break
                
    if desktop_file_path:
        logger.debug(f"Found desktop file in extracted dir: {desktop_file_path}")
    else:
        logger.warning(f"Could not find .desktop file in extracted dir: {extract_dir}")
    return desktop_file_path

# --- Helper function for parsing desktop file metadata ---
def _parse_metadata_from_desktop(desktop_file_path):
    """Parses essential metadata from a .desktop file."""
    metadata = {
        "name": None, "version": "unknown", "description": "", 
        "icon_name": "", "categories": [], "exec_val": ""
    }
    if not desktop_file_path or not os.path.exists(desktop_file_path):
        return metadata

    parser = configparser.ConfigParser(interpolation=None)
    parser.optionxform = str 
    try:
        with open(desktop_file_path, 'r', encoding='utf-8') as f:
            parser.read_file(f)
            
        if "Desktop Entry" in parser:
            entry = parser["Desktop Entry"]
            metadata["name"] = entry.get("Name")
            metadata["description"] = entry.get("Comment", entry.get("GenericName", ""))
            metadata["icon_name"] = entry.get("Icon", "")
            metadata["categories"] = [cat.strip() for cat in entry.get("Categories", "").split(';') if cat.strip()]
            metadata["exec_val"] = entry.get("Exec", "")
            metadata["version"] = entry.get("X-AppImage-Version", entry.get("Version", "unknown"))
            logger.debug(f"Parsed metadata: Name={metadata['name']}, Icon={metadata['icon_name']}")
        else:
             logger.warning(f"Desktop file missing [Desktop Entry]: {desktop_file_path}")
    except Exception as e:
        logger.error(f"Error parsing desktop file {desktop_file_path}: {e}")
        
    # Fallback name if parsing failed or Name key missing
    if not metadata["name"]:
         metadata["name"] = os.path.basename(desktop_file_path).replace(".desktop", "")
         logger.warning(f"Using fallback name from filename: {metadata['name']}")

    return metadata

# --- Helper function for finding icon file ---
def _find_icon_in_extracted(extract_dir, icon_name):
    """Finds the best icon file path within the extracted directory."""
    if not icon_name:
        return None

    search_bases = [
        os.path.join(extract_dir, "usr", "share", "icons"), 
        extract_dir 
    ]
    best_icon_path = None
    max_size = 0

    for base in search_bases:
        if not os.path.isdir(base): continue
        
        hicolor_path = os.path.join(base, "hicolor")
        # Check common png/svg extensions directly in base or base/pixmaps
        pixmap_path = os.path.join(base, "pixmaps")
        icon_search_paths = [base]
        if os.path.isdir(pixmap_path):
            icon_search_paths.append(pixmap_path)
            
        for search_path in icon_search_paths:
            for ext in [".svg", ".svgz", ".png", ".xpm"]:
                potential_icon = os.path.join(search_path, f"{icon_name}{ext}")
                if os.path.exists(potential_icon):
                    if ext.startswith(".svg"): # Prefer SVG
                        best_icon_path = potential_icon
                        break # Stop searching paths/extensions if SVG found
                    elif not best_icon_path or ext == ".png": # Found PNG
                         best_icon_path = potential_icon
                         # Don't break PNG, look for bigger ones
                    elif not best_icon_path and ext == ".xpm": # Fallback to XPM
                         best_icon_path = potential_icon

            if best_icon_path and best_icon_path.endswith((".svg", ".svgz")): break
        if best_icon_path and best_icon_path.endswith((".svg", ".svgz")): break

        # Search hicolor for PNGs (prefer larger) if no SVG found yet
        if os.path.isdir(hicolor_path) and (not best_icon_path or best_icon_path.endswith(".png")):
             try: # scandir might fail due to permissions
                size_dirs = [d.name for d in os.scandir(hicolor_path) if d.is_dir() and 'x' in d.name]
                for size_dir in sorted(size_dirs, key=lambda s: int(s.split('x')[0]) if s.split('x')[0].isdigit() else 0, reverse=True):
                    try:
                         current_size = int(size_dir.split('x')[0])
                         if current_size < max_size: continue
                         apps_path = os.path.join(hicolor_path, size_dir, "apps")
                         potential_icon_hicolor = os.path.join(apps_path, f"{icon_name}.png")
                         if os.path.exists(potential_icon_hicolor):
                             if current_size > max_size:
                                 max_size = current_size
                                 best_icon_path = potential_icon_hicolor
                    except (ValueError, IndexError, FileNotFoundError):
                         continue
             except OSError as e:
                  logger.warning(f"Could not scan hicolor directory {hicolor_path}: {e}")

    if best_icon_path:
        logger.debug(f"Found best icon in extracted dir: {best_icon_path}")
    else:
        logger.warning(f"Could not find icon '{icon_name}' in extracted dir: {extract_dir}")
    return best_icon_path

# --- Helper function to copy icon to user location ---
def _copy_icon_to_user_location(source_icon_path, app_name):
    """Copies the icon to the user's standard hicolor directory, returns target path or None."""
    if not source_icon_path or not os.path.exists(source_icon_path) or not app_name:
        return None
        
    icon_filename = os.path.basename(source_icon_path)
    # Use sanitized app name for the target filename to avoid issues
    sanitized_app_name = sanitize_name(app_name)
    icon_ext = os.path.splitext(icon_filename)[1].lower()
    target_filename = f"{sanitized_app_name}{icon_ext}"

    target_icon_dir_base = os.path.join(config.USER_HOME, ".local/share/icons/hicolor")
    target_icon_subdir = ""
    
    if icon_ext in ['.svg', '.svgz']:
        target_icon_subdir = os.path.join(target_icon_dir_base, "scalable", "apps")
    elif icon_ext == ".png":
        # Try to guess size from path, otherwise use fallback
        size = "128x128" # Default fallback size
        parts = source_icon_path.split(os.sep)
        for i, part in enumerate(reversed(parts)):
            if 'x' in part and part.split('x')[0].isdigit() and i < 3: # Heuristic: size is usually close to filename
                size = part
                break
        target_icon_subdir = os.path.join(target_icon_dir_base, size, "apps")
    else:
        # Fallback for other types like xpm, put in a generic size dir
        target_icon_subdir = os.path.join(target_icon_dir_base, "48x48", "apps") # Arbitrary choice

    try:
        os.makedirs(target_icon_subdir, exist_ok=True)
        target_icon_path = os.path.join(target_icon_subdir, target_filename)
        shutil.copy2(source_icon_path, target_icon_path)
        logger.info(f"Icon copied to user location: {target_icon_path}")
        # Return the *sanitized name* which should be used in the .desktop file
        # or the full path depending on desktop spec recommendations? Usually name is preferred.
        return sanitized_app_name # Return name for .desktop file
    except Exception as e:
        logger.error(f"Failed to copy icon {source_icon_path} to {target_icon_subdir}: {e}")
        return None

# --- Helper function to create .desktop file ---
def _create_registered_desktop_file(appimage_path, metadata, registered_icon_name_or_path):
    """Creates a .desktop file for a registered AppImage."""
    if not metadata.get("name") or not appimage_path:
        logger.error("Cannot create .desktop file: Missing name or AppImage path.")
        return None

    desktop_dir = os.path.join(config.USER_HOME, ".local", "share", "applications")
    os.makedirs(desktop_dir, exist_ok=True)

    # Use sanitized name for the desktop file name
    desktop_filename = f"appimagekit_{sanitize_name(metadata['name'])}.desktop"
    desktop_file_path = os.path.join(desktop_dir, desktop_filename)

    logger.info(f"Creating .desktop file: {desktop_file_path}")
    try:
        with open(desktop_file_path, 'w', encoding='utf-8') as f:
            f.write("[Desktop Entry]\n")
            f.write(f"Name={metadata['name']}\n")
            if metadata.get("description"):
                f.write(f"Comment={metadata['description']}\n")
            # IMPORTANT: Exec points directly to the original AppImage path
            # Quote the path to handle spaces etc.
            f.write(f"Exec=\"{appimage_path}\" %U\n") # Add %U for file manager integration
            # Use the registered icon name/path
            if registered_icon_name_or_path:
                f.write(f"Icon={registered_icon_name_or_path}\n")
            else:
                 # Fallback to generic icon if copy failed
                 f.write(f"Icon=application-x-appimage\n")
            f.write("Terminal=false\n")
            f.write("Type=Application\n")
            if metadata.get("categories"):
                f.write(f"Categories={';'.join(metadata['categories'])};\n")
            else:
                 f.write(f"Categories=Utility;\n") # Default category
            # Add AppImage specific keys?
            f.write(f"X-AppImage-Path={appimage_path}\n")
            f.write(f"X-AppImage-Managed-By=appimagemanager\n")
            
        # Update desktop database
        if shutil.which("update-desktop-database"):
            try:
                subprocess.run(["update-desktop-database", desktop_dir], check=False, capture_output=True)
                logger.info(f"Masaüstü veritabanı güncellendi: {desktop_dir}")
            except Exception as e:
                logger.warning(f"'update-desktop-database' çalıştırılırken hata: {e}")
        
        return desktop_file_path
    except Exception as e:
        logger.error(f"Failed to create .desktop file {desktop_file_path}: {e}")
        return None

# --- Main function for registering an AppImage ---
def register_appimage(appimage_path):
    """Registers an AppImage by extracting metadata, copying icon, creating desktop file."""
    if not os.path.exists(appimage_path):
        logger.error(f"Cannot register AppImage: File not found at {appimage_path}")
        return None
        
    logger.info(f"Registering AppImage: {appimage_path}")
    temp_dir = None
    extract_dir = None
    db_info = None

    try:
        # 1. Extract AppImage temporarily
        temp_dir = tempfile.mkdtemp(prefix="appimage_register_")
        logger.debug(f"Temporary directory created: {temp_dir}")
        # Ensure executable permission
        try:
            os.chmod(appimage_path, os.stat(appimage_path).st_mode | 0o111)
        except Exception as chmod_err:
            logger.warning(f"Could not set executable permission on {appimage_path}: {chmod_err}")
            
        extract_cmd = [appimage_path, "--appimage-extract"]
        result = subprocess.run(extract_cmd, cwd=temp_dir, capture_output=True, text=True, check=False)
        
        if result.returncode != 0:
             logger.warning(f"AppImage extraction failed (RC={result.returncode}), trying again without HOME env var... stderr: {result.stderr}")
             result = subprocess.run(extract_cmd, cwd=temp_dir, capture_output=True, text=True, env={})
             if result.returncode != 0:
                  logger.error(f"AppImage extraction failed definitively. stderr: {result.stderr}")
                  raise RuntimeError("Failed to extract AppImage metadata.")

        extract_dir = os.path.join(temp_dir, "squashfs-root")
        if not os.path.isdir(extract_dir):
            subdirs = [d for d in os.listdir(temp_dir) if os.path.isdir(os.path.join(temp_dir, d))]
            if len(subdirs) == 1:
                extract_dir = os.path.join(temp_dir, subdirs[0])
            else:
                 logger.error(f"Could not find extracted directory structure in {temp_dir}")
                 raise RuntimeError("Unknown extracted AppImage structure.")
        logger.info(f"AppImage extracted temporarily to: {extract_dir}")

        # 2. Find and parse .desktop file
        desktop_file = _find_desktop_file(extract_dir)
        if not desktop_file:
             # Use fallback metadata if no desktop file found
             app_name = os.path.basename(appimage_path).replace(".AppImage", "")
             metadata = {"name": app_name, "version": "unknown", "icon_name": "", "categories": [], "description": ""}
             logger.warning("Using fallback metadata due to missing .desktop file.")
        else:
             metadata = _parse_metadata_from_desktop(desktop_file)

        # Ensure we have a name
        if not metadata.get("name"):
             metadata["name"] = os.path.basename(appimage_path).replace(".AppImage", "")
             logger.warning(f"Using fallback name from AppImage filename: {metadata['name']}")

        # 3. Find and copy icon
        source_icon_path = _find_icon_in_extracted(extract_dir, metadata.get("icon_name"))
        registered_icon_name = None
        if source_icon_path:
            registered_icon_name = _copy_icon_to_user_location(source_icon_path, metadata['name']) # Use app name for target file

        # 4. Create .desktop file pointing to original AppImage
        created_desktop_path = _create_registered_desktop_file(appimage_path, metadata, registered_icon_name)

        # 5. Prepare info for DBManager
        db_info = {
            "name": metadata['name'],
            "version": metadata.get("version", "unknown"),
            "description": metadata.get("description", ""),
            "categories": metadata.get("categories", []),
            "appimage_path": appimage_path, # Store original path
            "desktop_file": created_desktop_path, # Path to the created .desktop file
            "icon_path": registered_icon_name, # Use the *name* used for registration, not the source path
            "management_type": config.MGMT_TYPE_REGISTERED,
            # These fields are not applicable for registered type
            "app_install_dir": None,
            "symlinks_created": [], 
            "executable_path": appimage_path # Executable is the original file itself
        }
        logger.info(f"Prepared registration info for DB: {metadata['name']}")

    except Exception as e:
        logger.error(f"Error during AppImage registration for {appimage_path}: {e}", exc_info=True)
        db_info = None # Ensure we return None on error
    finally:
        # 6. Cleanup temporary directory
        if temp_dir and os.path.isdir(temp_dir):
            try:
                shutil.rmtree(temp_dir)
                logger.debug(f"Temporary directory cleaned up: {temp_dir}")
            except Exception as cleanup_err:
                logger.error(f"Failed to clean up temporary directory {temp_dir}: {cleanup_err}")
                
    return db_info # Return the dict or None if failed

# --- Function to remove registered app artifacts --- 
def remove_registered_app_artifacts(app_info):
    """Removes .desktop file and copied icons for a registered app."""
    if not app_info or app_info.get("management_type") != config.MGMT_TYPE_REGISTERED:
        logger.warning("Skipping artifact removal: Invalid app_info or not a registered app.")
        return False
        
    app_name = app_info.get("name", "unknown")
    logger.info(f"Removing registered artifacts for {app_name}...")
    success = True
    
    # 1. Remove .desktop file
    desktop_file = app_info.get("desktop_file")
    if desktop_file and os.path.exists(desktop_file):
        try:
            os.remove(desktop_file)
            logger.info(f"Removed .desktop file: {desktop_file}")
            # Update desktop database after removing file
            desktop_dir = os.path.dirname(desktop_file)
            if shutil.which("update-desktop-database"):
                try:
                    subprocess.run(["update-desktop-database", desktop_dir], check=False, capture_output=True)
                    logger.info(f"Masaüstü veritabanı güncellendi: {desktop_dir}")
                except Exception as e:
                    logger.warning(f"'update-desktop-database' çalıştırılırken hata: {e}")
        except OSError as e:
            logger.error(f"Failed to remove .desktop file {desktop_file}: {e}")
            success = False
    elif desktop_file:
        logger.debug(f".desktop file not found (already removed?): {desktop_file}")

    # 2. Remove copied icon(s)
    # We stored the *name* used for the icon file (sanitized), not the full path.
    # We need to search for this name in standard user icon locations.
    icon_name_registered = app_info.get("icon_path") 
    if icon_name_registered: 
        icon_removed = False
        logger.info(f"Attempting to remove icons matching base name: {icon_name_registered}")
        # Standard sizes and locations to check
        icon_sizes = ["16x16", "22x22", "24x24", "32x32", "48x48", "64x64", "128x128", "256x256", "512x512", "scalable"]
        icon_exts = [".png", ".svg", ".svgz", ".xpm"]
        icon_dir_base = os.path.join(config.USER_HOME, ".local/share/icons/hicolor")
        
        for size in icon_sizes:
            size_dir = os.path.join(icon_dir_base, size, "apps")
            if not os.path.isdir(size_dir):
                continue
            for ext in icon_exts:
                icon_path_to_remove = os.path.join(size_dir, f"{icon_name_registered}{ext}")
                if os.path.exists(icon_path_to_remove):
                    try:
                        os.remove(icon_path_to_remove)
                        logger.info(f"Removed registered icon: {icon_path_to_remove}")
                        icon_removed = True
                    except OSError as e:
                        logger.error(f"Failed to remove icon {icon_path_to_remove}: {e}")
                        success = False
                        
        # Update icon cache if we removed any icons
        if icon_removed and shutil.which("gtk-update-icon-cache"):
            try:
                subprocess.run(["gtk-update-icon-cache", "-f", "-t", icon_dir_base], check=False, capture_output=True)
                logger.info(f"Updated icon cache: {icon_dir_base}")
            except Exception as e:
                logger.warning(f"Failed to update icon cache: {e}")
    else:
        logger.debug("No registered icon name found in app_info, skipping icon removal.")

    return success

# ... (check_system_compatibility and other existing functions) ...
# ... (find_leftovers and remove_selected_leftovers) ...

