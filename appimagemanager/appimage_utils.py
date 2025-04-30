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
            checks["has_write_access"] = self._check_write_permissions()
        
        return checks
    
    def _check_write_permissions(self):
        """Check write permissions for non-root install/link locations."""
        # This is essentially the same logic as _check_if_root_required 
        # but intended for non-root scenarios to give specific feedback
        # Reuse the logic for clarity
        return not self._check_if_root_required()
    
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
                logger.error(f"\'squashfs-root\' dizini bulunamadı: {self.temp_dir}")
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
            logger.info(f"\'usr\' dizini yok, \'{source_dir}\' kök dizini kopyalanacak.")
            
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
                 logger.warning(f"\'update-desktop-database\' çalıştırılırken hata: {e}")
        else:
             logger.warning("\'update-desktop-database\' komutu bulunamadı, veritabanı güncellenmedi.")

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
        self.requires_root = self._check_if_root_required()
    
    def _check_if_root_required(self):
        """Kaldırma işlemi için root yetkisi gerekip gerekmediğini kontrol eder."""
        install_mode = self.app_info.get("install_mode", "system")
        install_path = self.app_info.get("install_path", "")
        
        if install_mode == "system":
            return True
        elif install_mode == "user":
            return False
        elif install_mode == "custom" and install_path:
            # Yolun yazılabilir olup olmadığını kontrol et
            try:
                parent_dir = os.path.dirname(install_path)
                test_path = os.path.join(parent_dir, ".write_test")
                with open(test_path, 'w') as f:
                    f.write("test")
                os.remove(test_path)
                return False
            except (PermissionError, OSError):
                return True
        
        return True  # Varsayılan olarak güvenli tarafta kalmak için
    
    def uninstall(self):
        """Uygulamayı kaldırır."""
        try:
            # Kurulu dosyaları tek tek sil
            files_to_remove = self.app_info.get("extracted_files", [])
            
            # Önce desktop dosyasını sil
            desktop_file = self.app_info.get("desktop_file", "")
            if desktop_file and os.path.exists(desktop_file):
                logger.info(f"Desktop dosyası siliniyor: {desktop_file}")
                os.remove(desktop_file)
            
            # Diğer dosyaları sil
            removed_files = []
            for file_path in files_to_remove:
                if os.path.exists(file_path):
                    try:
                        os.remove(file_path)
                        removed_files.append(file_path)
                    except (IsADirectoryError, PermissionError, OSError) as e:
                        # Dizin veya silinemez dosya
                        logger.warning(f"Dosya silinemedi: {file_path}, {e}")
            
            logger.info(f"Kaldırma tamamlandı: {len(removed_files)}/{len(files_to_remove)} dosya silindi.")
            return True
        except Exception as e:
            logger.error(f"Kaldırma sırasında hata: {e}")
            return False


def check_system_compatibility():
    """Sistem uyumluluğunu kontrol eder."""
    checks = {
        "is_ubuntu": False,
        "ubuntu_version": None,
        "libfuse_installed": False,
        "rsync_installed": False
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
    
    return checks 