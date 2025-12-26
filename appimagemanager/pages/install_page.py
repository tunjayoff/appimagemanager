"""
AppImage Manager - Install Page UI
Provides the graphical interface for selecting and installing an AppImage.
"""

from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, 
                             QPushButton, QFileDialog, QGroupBox, QRadioButton, 
                             QProgressBar, QSpacerItem, QSizePolicy, QFormLayout,
                             QToolButton, QMenu, QListWidget, QListWidgetItem,
                             QApplication)
from PyQt6.QtCore import Qt, QTimer, QPoint, QEvent, QCoreApplication
import os
from PyQt6.QtGui import QIcon, QAction, QPixmap
# from PyQt6.QtWidgets import QGraphicsDropShadowEffect # Unused import
import uuid
import datetime
import shutil
import shlex
import tempfile

from .. import config
# from i18n import _ # Remove this import
from ..i18n import get_translator # Import the getter function
from ..utils import sanitize_name # <-- Import from utils
from ..db_manager import DBManager # ADD THIS IMPORT
from .. import sudo_helper # ADD THIS IMPORT
# from .. import appimage_utils # This might not be needed anymore if sanitize_name moved
from .. import integration # <-- ADD THIS IMPORT
from ..installer import AppImageInstaller # Import from the new installer module

# Get the translator instance
translator = get_translator()

class InstallPage(QWidget):
    """UI elements for the AppImage installation page."""
    def __init__(self, parent=None, db_manager=None, main_window=None):
        super().__init__(parent)
        self.setObjectName("installPage")
        self.main_window = main_window # Store main window reference
        if not db_manager:
             # If not passed, create a default instance (less ideal but works)
             logger.warning("DBManager not passed to InstallPage, creating default instance.")
             self.db_manager = DBManager()
        else:
             self.db_manager = db_manager
        
        # --- Main Layout ---
        main_layout = QVBoxLayout(self)
        main_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        # --- File Selection ---
        file_selection_layout = QHBoxLayout()
        # File selection label
        self.file_label = QLabel(translator.get_text("lbl_app_file"))
        self.select_file_button = QPushButton(translator.get_text("btn_select_appimage"))
        self.select_file_button.clicked.connect(self.select_file)
        self.selected_file_label = QLineEdit()
        self.selected_file_label.setPlaceholderText(translator.get_text("lbl_no_file_selected"))
        self.selected_file_label.setReadOnly(True)
        
        file_selection_layout.addWidget(self.file_label)
        file_selection_layout.addWidget(self.selected_file_label)
        file_selection_layout.addWidget(self.select_file_button)
        main_layout.addLayout(file_selection_layout)
        main_layout.addSpacing(15) # Add spacing after file selection

        # --- Recent AppImages popup for quick selection ---
        home = os.path.expanduser("~")
        recent_paths = []
        for sub in ["Downloads", "Desktop"]:
            dir_path = os.path.join(home, sub)
            if os.path.isdir(dir_path):
                for fname in os.listdir(dir_path):
                    if fname.lower().endswith(('.appimage', '.AppImage')):
                        recent_paths.append(os.path.join(dir_path, fname))
        if recent_paths:
            self.recent_button = QPushButton(translator.get_text("Recent AppImages"))
            self.recent_button.setIcon(QIcon.fromTheme("view-list"))
            self.recent_button.clicked.connect(self.show_recent_popup)
            self._recent_paths = recent_paths
            self._recent_popup = None
            file_selection_layout.addWidget(self.recent_button)

        # --- AppImage Information (Placeholders) ---
        self.info_group = QGroupBox(translator.get_text("lbl_app_info"))
        info_layout = QFormLayout() # Use QFormLayout for better alignment
        info_layout.setContentsMargins(10, 15, 10, 10) # Add margins inside groupbox
        info_layout.setSpacing(10) # Spacing between rows
        self.app_name_label = QLabel("-") # Label text set by addRow
        self.app_version_label = QLabel("-") # Label text set by addRow
        self.app_icon_label = QLabel() # Label for the icon
        self.app_icon_label.setMinimumSize(64, 64) # Give it a reasonable minimum size
        self.app_icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.app_icon_label.setStyleSheet("border: 1px solid #ccc; border-radius: 5px; background-color: #f0f0f0;") # Basic styling
        # Add more labels as needed (description, etc.)
        
        # Add icon label to the form layout
        icon_layout = QHBoxLayout()
        icon_layout.addSpacerItem(QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum))
        icon_layout.addWidget(self.app_icon_label)
        icon_layout.addSpacerItem(QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum))
        info_layout.addRow(translator.get_text("Icon:"), icon_layout) # Add icon row
        
        # Ensure correct labels are used
        info_layout.addRow(translator.get_text("Name:"), self.app_name_label)
        info_layout.addRow(translator.get_text("Version:"), self.app_version_label)
        
        self.info_group.setLayout(info_layout)
        self.info_group.setVisible(False) # Initially hidden until file selected
        main_layout.addWidget(self.info_group)
        main_layout.addSpacing(15) # Add spacing after info group

        # --- Installation Options ---
        self.options_group = QGroupBox(translator.get_text("grp_installation_options"))
        options_layout = QVBoxLayout()
        options_layout.setContentsMargins(10, 15, 10, 10) # Add margins inside groupbox
        options_layout.setSpacing(10) # Spacing between elements
        
        # Install Mode
        mode_layout = QHBoxLayout()
        self.user_mode_radio = QRadioButton(translator.get_text("install_mode_user"))
        self.system_mode_radio = QRadioButton(translator.get_text("install_mode_system"))
        self.custom_mode_radio = QRadioButton(translator.get_text("install_mode_custom"))
        self.add_to_library_radio = QRadioButton(translator.get_text("install_mode_add_to_library"))
        
        # Determine default check state based on config (or default to user)
        default_mode = config.get_setting("default_install_mode", "user")
        self.user_mode_radio.setChecked(default_mode == "user")
        self.system_mode_radio.setChecked(default_mode == "system")
        self.custom_mode_radio.setChecked(default_mode == "custom")
        # Register mode cannot be the default install mode from config usually
        # If somehow it was set, default to user instead.
        if default_mode == config.MGMT_TYPE_REGISTERED:
            self.user_mode_radio.setChecked(True)
        else:
            self.add_to_library_radio.setChecked(False) # Explicitly uncheck

        mode_layout.addWidget(self.user_mode_radio)
        mode_layout.addWidget(self.system_mode_radio)
        mode_layout.addWidget(self.custom_mode_radio)
        mode_layout.addWidget(self.add_to_library_radio)
        options_layout.addLayout(mode_layout)
        
        # Custom Path (Initially hidden)
        self.custom_path_layout = QHBoxLayout()
        self.custom_path_input = QLineEdit()
        # Browse button for custom installation directory
        self.custom_path_button = QPushButton(translator.get_text("btn_browse"))
        self.custom_path_button.setIcon(QIcon.fromTheme("folder-open"))
        self.custom_path_input.setPlaceholderText(translator.get_text("Select custom installation directory"))
        # Adjust button size
        self.custom_path_button.setMinimumWidth(80)
        self.custom_path_layout.addWidget(QLabel(translator.get_text("Path:")))
        self.custom_path_layout.addWidget(self.custom_path_input)
        self.custom_path_layout.addWidget(self.custom_path_button)
        
        self.custom_path_widget = QWidget() # Wrap layout in a widget to hide/show easily
        self.custom_path_widget.setLayout(self.custom_path_layout)
        self.custom_path_widget.setVisible(self.custom_mode_radio.isChecked())
        options_layout.addWidget(self.custom_path_widget)
        
        # Connect radio buttons to toggle custom path visibility
        self.user_mode_radio.toggled.connect(self.toggle_custom_path)
        self.system_mode_radio.toggled.connect(self.toggle_custom_path)
        self.custom_mode_radio.toggled.connect(self.toggle_custom_path)
        self.add_to_library_radio.toggled.connect(self.toggle_custom_path)
        self.custom_path_button.clicked.connect(self.select_custom_path)

        self.options_group.setLayout(options_layout)
        self.options_group.setVisible(False) # Initially hidden
        main_layout.addWidget(self.options_group)
        main_layout.addSpacing(20) # Add spacing before install button

        # --- Install Button ---
        self.install_button = QPushButton(translator.get_text("install_button"))
        self.install_button.setEnabled(False) # Disabled until file selected
        self.install_button.clicked.connect(self.start_installation) # Connect to placeholder
        main_layout.addWidget(self.install_button, alignment=Qt.AlignmentFlag.AlignRight)

        # --- Progress Bar and Status ---
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False) # Initially hidden
        main_layout.addWidget(self.progress_bar)
        main_layout.addSpacing(5) # Add small spacing
        
        self.status_label = QLabel("")
        self.status_label.setVisible(False) # Initially hidden
        main_layout.addWidget(self.status_label)

        # --- Spacer to push content up ---
        main_layout.addSpacerItem(QSpacerItem(20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding))

    def select_file(self):
        """Opens a file dialog to select an AppImage."""
        file_path, _ = QFileDialog.getOpenFileName(
            self, 
            translator.get_text("Select AppImage"), 
            os.path.expanduser("~"), # Start in home directory
            translator.get_text("AppImage Files (*.AppImage *.appimage)")
        )
        if file_path:
            self.selected_file_label.setText(file_path)
            self.process_selected_file(file_path) # Placeholder for processing
            self.install_button.setEnabled(True)
            self.info_group.setVisible(True)
            self.options_group.setVisible(True)
            self.status_label.setVisible(False) # Hide status on new selection
            self.progress_bar.setVisible(False)
            logger.info(f"AppImage selected: {file_path}") # Requires logger setup
        else:
            # Optionally clear fields if dialog is cancelled
            # self.selected_file_label.clear()
            # self.install_button.setEnabled(False)
            # self.info_group.setVisible(False) 
            # self.options_group.setVisible(False)
            pass

    def process_selected_file(self, file_path):
        """Extracts info from the selected AppImage and updates the UI."""
        # Clear previous info and icon
        self.app_name_label.setText("-")
        self.app_version_label.setText("-")
        self.app_icon_label.clear()
        self.app_icon_label.setText(translator.get_text("Loading...")) 
        self.install_button.setEnabled(False) # Disable install button initially
        self.info_group.setVisible(True) # Keep info group visible
        self.options_group.setVisible(False) # Hide options until metadata read
        
        temp_installer = None # Define outside try for cleanup
        try:
            # Create a temporary installer instance
            temp_installer = AppImageInstaller(file_path)
            
            # --- Read Metadata --- 
            if temp_installer.read_metadata():
                 # Metadata read successfully
                 app_info = temp_installer.app_info
                 app_name = app_info.get("name", "Unknown") # Use Unknown as fallback here too
                 app_version = app_info.get("version", "Unknown")
                 self.app_name_label.setText(app_name) 
                 self.app_version_label.setText(app_version)
                 logger.info(f"Successfully read metadata: Name='{app_name}', Version='{app_version}'")
                 self.options_group.setVisible(True) # Show options
                 self.install_button.setEnabled(True) # Enable install
                 
                 # --- Try to extract and display icon --- 
                 icon_path = temp_installer.temp_preview_icon_path # Use the path prepared by read_metadata
                 if icon_path:
                     pixmap = QPixmap(icon_path)
                     if not pixmap.isNull():
                         scaled_pixmap = pixmap.scaled(self.app_icon_label.size(), 
                                                       Qt.AspectRatioMode.KeepAspectRatio, 
                                                       Qt.TransformationMode.SmoothTransformation)
                         self.app_icon_label.setPixmap(scaled_pixmap)
                         logger.info(f"Displayed icon from: {icon_path}")
                     else:
                         logger.warning(f"Failed to load QPixmap from extracted icon: {icon_path}")
                         self.app_icon_label.setText(translator.get_text("No Icon"))
                 else:
                      logger.info("No icon could be extracted for display.")
                      self.app_icon_label.setText(translator.get_text("No Icon"))
            else:
                 # read_metadata failed (error logged within method), show error state
                 logger.error("read_metadata failed, showing error in UI.")
                 self.app_name_label.setText(translator.get_text("Error"))
                 self.app_version_label.setText(translator.get_text("Could not read metadata"))
                 self.app_icon_label.setText(translator.get_text("Error"))
                 # Keep install button disabled

        except FileNotFoundError as e: # Catch specific error from __init__
            logger.error(f"Error creating AppImageInstaller: {e}")
            self.app_name_label.setText(translator.get_text("Error"))
            self.app_version_label.setText(f"{translator.get_text('File Error')}: {e}") # Show file error
            self.app_icon_label.setText(translator.get_text("Error"))
        except Exception as e:
            logger.error(f"Error processing selected file '{file_path}': {e}", exc_info=True)
            # General error update
            self.app_name_label.setText(translator.get_text("Error"))
            self.app_version_label.setText(translator.get_text("Could not read metadata"))
            self.app_icon_label.setText(translator.get_text("Error"))
        finally:
             # Cleanup temporary files created by this instance
             if temp_installer:
                  temp_installer.cleanup()

    def toggle_custom_path(self):
        """Shows/hides the custom path input based on radio button selection."""
        self.custom_path_widget.setVisible(self.custom_mode_radio.isChecked())

    def select_custom_path(self):
        """Opens a directory dialog to select a custom installation path."""
        dir_path = QFileDialog.getExistingDirectory(
            self,
            translator.get_text("Select Custom Installation Directory"),
            self.custom_path_input.text() or os.path.expanduser("~")
        )
        if dir_path:
            self.custom_path_input.setText(dir_path)
            logger.info(f"Custom installation path selected: {dir_path}")

    def start_installation(self):
        """Starts the actual installation or registration process based on selected options."""
        appimage_path = self.selected_file_label.text()
        if not appimage_path or not os.path.exists(appimage_path):
            self.update_status(translator.get_text("Error: Please select a valid AppImage file first."), error=True)
            return

        # Temporary directories to clean up
        self.temp_dirs = []
        
        # --- Determine selected mode --- 
        management_type = config.MGMT_TYPE_INSTALLED # Default to installed unless register is checked
        install_mode = "user" # Default install mode if installed type
        custom_path = None
        
        # Check if Add to Library (Copy) mode is selected
        if self.add_to_library_radio.isChecked():
            # Keep management type as registered internally for now
            management_type = config.MGMT_TYPE_REGISTERED
            logger.info(f"Starting Add to Library process for '{appimage_path}'")
            self.set_ui_installing(True)
            self.update_status(translator.get_text("Adding AppImage to library..."))
            self.progress_bar.setRange(0, 100) # Use progress for copy
            self.progress_bar.setValue(5)
            
            created_bin_link = None
            created_desktop_file = None
            copied_appimage_path = None # Path to the *copied* file
            temp_installer = None # For metadata reading
            try:
                # 1. Ensure managed directory exists
                managed_dir = config.MANAGED_APPIMAGES_DIR
                logger.debug(f"Ensuring managed AppImage directory exists: {managed_dir}")
                os.makedirs(managed_dir, exist_ok=True)
                self.progress_bar.setValue(10)

                # 2. Read metadata (using temporary installer) BEFORE copying
                logger.debug("Reading metadata before copy...")
                temp_installer = AppImageInstaller(appimage_path)
                read_success, temp_icon_path = temp_installer.read_metadata()
                if not read_success:
                    raise RuntimeError(translator.get_text("Failed to read AppImage metadata."))
                app_info = temp_installer.app_info
                logger.debug("Metadata read successfully.")
                self.progress_bar.setValue(25)
                
                # 3. Determine target filename (use original)
                target_filename = os.path.basename(appimage_path)
                copied_appimage_path = os.path.join(managed_dir, target_filename)
                logger.debug(f"Target path for copied AppImage: {copied_appimage_path}")

                # 4. Check for existing file (optional: overwrite or rename?)
                if os.path.exists(copied_appimage_path):
                    # Simple approach: Overwrite existing file
                    logger.warning(f"AppImage already exists in library, overwriting: {copied_appimage_path}")
                    # TODO: Add option to cancel or rename?
                    try: 
                         os.remove(copied_appimage_path)
                    except OSError as rm_err:
                         raise RuntimeError(f"Could not overwrite existing file in library: {rm_err}")
                
                # 5. Copy the AppImage file
                self.update_status(translator.get_text("Copying AppImage to library..."))
                logger.info(f"Copying {appimage_path} to {copied_appimage_path}")
                # TODO: Implement progress reporting for large files
                shutil.copy2(appimage_path, copied_appimage_path)
                logger.info("AppImage copied successfully.")
                self.progress_bar.setValue(75)

                # Get the extract directory for Qt detection
                extract_dir_for_qt = None
                if temp_installer and hasattr(temp_installer, 'temp_dir') and temp_installer.temp_dir:
                    potential_squashfs = os.path.join(temp_installer.temp_dir, "meta_read", "squashfs-root")
                    if os.path.isdir(potential_squashfs):
                        extract_dir_for_qt = potential_squashfs
                
                # 6. Call integration function using the COPIED path
                self.update_status(translator.get_text("Creating shortcuts..."))
                created_bin_link, created_desktop_file = integration.register_appimage_integration(
                    copied_appimage_path, # Use the path to the copy!
                    app_info, 
                    temp_icon_path,
                    extract_dir=extract_dir_for_qt  # For Qt detection
                )
                
                # Cleanup the temp installer AFTER integration call (icon needed)
                if temp_installer: temp_installer.cleanup()

                if not created_bin_link or not created_desktop_file:
                     raise RuntimeError(translator.get_text("Failed to create integration files (link/desktop)."))
                logger.info(f"Integration files created: Link={created_bin_link}, Desktop={created_desktop_file}")
                self.progress_bar.setValue(90)
                
                # 7. Gather info for database (using COPIED path)
                app_name_used = app_info.get('name') or os.path.basename(copied_appimage_path).replace('.AppImage','').replace('.appimage','')
                icon_name_used = app_info.get('icon_name') or sanitize_name(app_name_used)
                reg_info = {
                    'id': str(uuid.uuid4()),
                    'name': app_name_used,
                    'version': app_info.get('version', 'N/A'),
                    'install_path': copied_appimage_path, # Store path to the COPY
                    'executable_path': copied_appimage_path, # Store path to the COPY
                    'icon_name': icon_name_used,
                    'management_type': config.MGMT_TYPE_REGISTERED, # Still use registered type
                    'date_added': datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    'desktop_file_path': created_desktop_file,
                    'executable_symlink': created_bin_link
                }

                # 8. Add to database
                try:
                    db = DBManager()
                    if db.add_app(reg_info):
                        logger.info("Copied application added to database.")
                        self.progress_bar.setValue(100)
                        self.update_status(translator.get_text("Application added to library successfully!"), is_success=True)
                    else:
                        logger.error("Failed to add copied application to database.")
                        integration.unregister_appimage_integration(created_bin_link, created_desktop_file)
                        if copied_appimage_path and os.path.exists(copied_appimage_path): os.remove(copied_appimage_path)
                        raise RuntimeError(translator.get_text("Failed to register in database."))
                except Exception as db_err:
                    logger.error(f"Database error during library add: {db_err}")
                    integration.unregister_appimage_integration(created_bin_link, created_desktop_file)
                    if copied_appimage_path and os.path.exists(copied_appimage_path): os.remove(copied_appimage_path)
                    raise RuntimeError(f"{translator.get_text('Database error')}: {db_err}")
                
            except Exception as e:
                logger.error(f"Add to Library failed: {e}", exc_info=True)
                # Attempt cleanup
                if temp_installer: temp_installer.cleanup() # Ensure temp installer cleaned
                integration.unregister_appimage_integration(created_bin_link, created_desktop_file)
                if copied_appimage_path and os.path.exists(copied_appimage_path): 
                    try: 
                        os.remove(copied_appimage_path)
                    except OSError: 
                        logger.error(f"Failed cleanup: Could not remove copied file {copied_appimage_path}")
                self.update_status(f"{translator.get_text('Add to Library failed')}: {e}", error=True) # New error message
                self.progress_bar.setRange(0, 1) 
                self.progress_bar.setValue(0)
            finally:
                if temp_installer: temp_installer.cleanup() # Extra cleanup just in case
                QTimer.singleShot(1500, lambda: self.set_ui_installing(False))
            
            return # Stop here for this mode

        # --- Installation Mode Logic (User, System, Custom) --- 
        elif self.system_mode_radio.isChecked():
            install_mode = "system"
        elif self.custom_mode_radio.isChecked():
            install_mode = "custom"
            custom_path = self.custom_path_input.text()
            if not custom_path or not os.path.isdir(custom_path):
                self.update_status(translator.get_text("Error: Please select a valid custom installation directory."), error=True)
                return
        # else: install_mode remains "user"
        
        logger.info(f"Starting installation for '{appimage_path}' (Mode: {install_mode}, Custom Path: {custom_path})")
        self.set_ui_installing(True)
        self.update_status(translator.get_text("Initializing installation..."))
        self.progress_bar.setRange(0, 100) # Use range 0-100 for steps
        self.progress_bar.setValue(5)
        
        installer = None # Define installer outside try block for finally clause
        try:
            # 1. Create Installer Instance
            installer = AppImageInstaller(appimage_path, install_mode, custom_path)
            self.progress_bar.setValue(10)

            # 2. Prerequisite Check Section Removed
            self.progress_bar.setValue(15)

            # 3. Extract AppImage (Can take time)
            self.update_status(translator.get_text("Extracting AppImage contents..."))
            # QApplication.processEvents() # Keep UI responsive
            if not installer.extract_appimage():
                raise RuntimeError(translator.get_text("Failed to extract AppImage."))
            self.progress_bar.setValue(40)

            # Default success value for all installation types
            success = False

            # System Install
            if self.system_mode_radio.isChecked():
                logger.info("Starting root installation...")
                self.update_status(translator.get_text("Starting root installation..."))

                root_commands = []
                bin_link_target = installer.bin_symlink_target
                install_dir = installer.app_install_dir
                source_dir = installer.extract_dir # The temp dir where extraction happened
                desktop_link_dir = installer.desktop_link_dir
                # Get the CALCULATED final path *within* the install dir (source for link)
                final_installed_exec_path = installer.final_executable_path
                # Get the CALCULATED final desktop path *within* the install dir (source for link)
                desktop_source_in_install_dir = installer.final_desktop_path

                if not install_dir:
                    logger.error("System install failed: Target installation directory not determined.")
                    self.update_status(translator.get_text("Error: Target directory unknown."), error=True)
                    return
                if not source_dir or not os.path.isdir(source_dir):
                    logger.error("System install failed: Temporary source directory invalid.")
                    self.update_status(translator.get_text("Error: Extraction source invalid."), error=True)
                    return

                # 1. Ensure base installation directory exists
                root_commands.append(["mkdir", "-p", os.path.dirname(install_dir)])
                # 2. Ensure target installation directory is clean (or exists)
                root_commands.append(["mkdir", "-p", install_dir]) # Ensure it exists first
                # 3. Copy files from temp extraction dir to final install dir
                # Use rsync -ah --delete? No, --delete might remove unrelated files if dir reused.
                # Safer: remove target dir first if exists, then mkdir, then rsync
                # Even safer: Use rsync -ah with trailing slashes for content sync
                root_commands.append(["rsync", "-ah", "--delete", source_dir + "/", install_dir + "/"])

                # 4. Create Binary Symlink
                target_bin_link_path = None
                if bin_link_target and final_installed_exec_path:
                    target_bin_link_path = bin_link_target # Already determined by installer
                    root_commands.append(["mkdir", "-p", os.path.dirname(target_bin_link_path)])
                    root_commands.append(["rm", "-f", target_bin_link_path])
                    
                    # Make sure the target file is executable
                    root_commands.append(["chmod", "+x", final_installed_exec_path])
                    
                    # Check if we need to create a wrapper script that handles AppImage environment setup
                    # First check if AppRun exists and if we should use its environment setup
                    apprun_path = os.path.join(installer.app_install_dir, "AppRun")
                    
                    if os.path.exists(apprun_path):
                        # Create a wrapper script that uses AppRun's environment setup but directly calls the executable
                        # This preserves the AppImage's environment configuration while making it accessible from PATH
                        wrapper_content = f"""#!/bin/bash
# Wrapper script for {installer.app_info.get('name', 'AppImage')}
# This script maintains the AppImage environment but makes it accessible from PATH

# Use the AppImage's directory for consistency
cd "{installer.app_install_dir}"

# Set environment variables from AppRun if possible
if [ -f "{apprun_path}" ]; then
    # Source the environment setup functions without executing AppRun itself
    # This is done by creating a temporary script that extracts the environment setup
    TEMP_ENV_SCRIPT=$(mktemp)
    grep -v "^exec " "{apprun_path}" > "$TEMP_ENV_SCRIPT"
    # Add a statement to export all variables to the environment
    echo 'export PATH LD_LIBRARY_PATH MAGICK_HOME GS_LIB GS_FONTPATH GS_OPTIONS QT_PLUGIN_PATH XDG_DATA_DIRS QT_QPA_PLATFORM_PLUGIN_PATH' >> "$TEMP_ENV_SCRIPT"
    # Source the environment script
    source "$TEMP_ENV_SCRIPT"
    rm -f "$TEMP_ENV_SCRIPT"
fi

# Execute the actual binary with all arguments
exec "{final_installed_exec_path}" "$@"
"""
                    else:
                        # Simpler wrapper when AppRun isn't available or for simpler AppImages
                        wrapper_content = f"""#!/bin/bash
# Wrapper script for {installer.app_info.get('name', 'AppImage')}
export DESKTOPINTEGRATION=1
exec "{final_installed_exec_path}" "$@"
"""
                    
                    # Create wrapper in temp directory first
                    temp_dir = tempfile.mkdtemp(prefix="aim_wrapper_")
                    self.temp_dirs.append(temp_dir)  # Store for cleanup
                    temp_wrapper_path = os.path.join(temp_dir, f"{os.path.basename(target_bin_link_path)}.wrapper")
                    with open(temp_wrapper_path, 'w') as f:
                        f.write(wrapper_content)
                    
                    # Then create command to move it to the target location with root privileges
                    # Use cp instead of cat with redirection which doesn't work in subprocess
                    root_commands.append(["cp", temp_wrapper_path, target_bin_link_path])
                    root_commands.append(["chmod", "+x", target_bin_link_path])
                else:
                    logger.warning("Binary symlink target or source path not determined, skipping binary link creation.")

                # 5. Create Desktop File Symlink
                target_desktop_link_path = None
                if desktop_link_dir and installer.app_info.get('name_sanitized'):
                    # Create desktop filename using the sanitized name
                    desktop_link_filename = f"appimagekit_{installer.app_info['name_sanitized']}.desktop"
                    target_desktop_link_path = os.path.join(desktop_link_dir, desktop_link_filename)

                    # Ensure destination directory exists
                    root_commands.append(["mkdir", "-p", desktop_link_dir])
                    root_commands.append(["rm", "-f", target_desktop_link_path])
                    
                    # Try to locate desktop file in extract dir
                    extract_desktop = None
                    if hasattr(installer, 'extract_dir') and installer.extract_dir and os.path.isdir(installer.extract_dir):
                        # Look recursively for desktop files in extract_dir
                        for root, _, files in os.walk(installer.extract_dir):
                            for file in files:
                                if file.endswith(".desktop"):
                                    extract_desktop = os.path.join(root, file)
                                    logger.debug(f"Found desktop file: {extract_desktop}")
                                    break
                            if extract_desktop:
                                break
                                
                    if extract_desktop:
                        # Copy the desktop file to target
                        root_commands.append(["cp", extract_desktop, target_desktop_link_path])
                        
                        # Update Exec and Icon entries in the desktop file
                        if bin_link_target:
                            root_commands.append(["sed", "-i", f"s|^Exec=.*|Exec={bin_link_target} %U|g", target_desktop_link_path])
                        
                        # Set icon name and copy icon files if available
                        icon_name = installer.app_info.get('icon_name')
                        if icon_name:
                            # Set the icon name in desktop file
                            root_commands.append(["sed", "-i", f's|^Icon=.*|Icon={icon_name}|g', target_desktop_link_path])
                            
                            # Try to find icon files for system-wide installation
                            if hasattr(installer, 'extract_dir') and installer.extract_dir:
                                # Common icon locations in AppImage structure
                                icon_locations = [
                                    # Root .DirIcon (common in AppImages)
                                    os.path.join(installer.extract_dir, ".DirIcon"),
                                    # Icon with exact name (common for desktop integration)
                                    os.path.join(installer.extract_dir, f"{icon_name}.png"),
                                    # Standard XDG locations
                                    os.path.join(installer.extract_dir, "usr/share/icons/hicolor/128x128/apps", f"{icon_name}.png"),
                                    os.path.join(installer.extract_dir, "usr/share/icons/hicolor/256x256/apps", f"{icon_name}.png"),
                                    os.path.join(installer.extract_dir, "usr/share/icons/hicolor/scalable/apps", f"{icon_name}.svg")
                                ]
                                
                                # Check all potential icon locations
                                for icon_path in icon_locations:
                                    if os.path.exists(icon_path) and os.path.isfile(icon_path):
                                        # Create system-wide icon directories if needed
                                        if icon_path.endswith(".svg"):
                                            # SVG goes to scalable directory
                                            icon_install_dir = "/usr/share/icons/hicolor/scalable/apps"
                                            root_commands.append(["mkdir", "-p", icon_install_dir])
                                            root_commands.append(["cp", icon_path, os.path.join(icon_install_dir, f"{icon_name}.svg")])
                                        else:
                                            # PNG goes to appropriate size directory
                                            # Default to 128x128 for unknown sizes
                                            icon_install_dir = "/usr/share/icons/hicolor/128x128/apps"
                                            root_commands.append(["mkdir", "-p", icon_install_dir])
                                            root_commands.append(["cp", icon_path, os.path.join(icon_install_dir, f"{icon_name}.png")])
                                        
                                        # Update icon cache
                                        root_commands.append(["gtk-update-icon-cache", "-f", "-t", "/usr/share/icons/hicolor"])
                                        break
                        
                        # Update desktop database
                        root_commands.append(["update-desktop-database", desktop_link_dir])
                        
                        # Store the final path for database registration
                        installer.final_copied_desktop_path = target_desktop_link_path
                    else:
                        logger.warning("No desktop file found in extracted directory")
                else:
                    logger.warning("Desktop file integration skipped: Missing target directory or sanitized name")

                self.update_status(translator.get_text("Executing installation steps with root privileges..."))
                QApplication.processEvents() # Update UI
                
                # Use the batch script helper to run all commands at once (requires only one sudo password)
                pkexec_success, pkexec_output = sudo_helper.run_commands_with_pkexec_script(root_commands)
                if not pkexec_success:
                    error_msg = translator.get_text("Root installation failed:") + f"\nOutput: {pkexec_output}"
                    logger.error(error_msg)
                    self.update_status(error_msg, is_error=True)
                    success = False
                else:
                    success = True
                    logger.info("Root installation commands completed successfully.")
                    if target_desktop_link_path:
                        # Make sure the desktop file path is set in installer object for database
                        logger.debug(f"Setting final_copied_desktop_path to {target_desktop_link_path}")
                        installer.final_copied_desktop_path = target_desktop_link_path

            # User or Custom Install (both use installer.install_files() and non-root approach)
            elif self.user_mode_radio.isChecked() or self.custom_mode_radio.isChecked():
                mode_name = "user" if self.user_mode_radio.isChecked() else "custom"
                logger.info(f"Starting {mode_name} installation...")
                self.update_status(translator.get_text(f"Starting {mode_name} installation..."))
                
                # Perform non-root installation
                if installer.install_files():
                    logger.info(f"Files copied successfully for {mode_name} installation.")
                    self.progress_bar.setValue(60)
                    
                    # Create symlinks (desktop integration)
                    self.update_status(translator.get_text("Creating shortcuts..."))
                    if installer.create_symlinks():
                        logger.info(f"Symlinks created successfully for {mode_name} installation.")
                        self.progress_bar.setValue(80)
                        success = True
                        # Store desktop file path for database
                        if hasattr(installer, 'final_copied_desktop_path'):
                            target_desktop_link_path = installer.final_copied_desktop_path
                    else:
                        logger.error(f"Failed to create symlinks for {mode_name} installation.")
                        self.update_status(translator.get_text("Error: Failed to create shortcuts."), error=True)
                        # Installation partially succeeded, but integration failed
                        success = False
                else:
                    logger.error(f"Failed to copy files for {mode_name} installation.")
                    self.update_status(translator.get_text("Error: Failed to copy AppImage files."), error=True)
                    success = False

            # 5. Add to Database (if successful)
            if success:
                # Update DB with installation info
                # For root installation, restore the desktop path handling
                if self.system_mode_radio.isChecked() and 'target_desktop_link_path' in locals():
                    installer.final_copied_desktop_path = target_desktop_link_path
                installation_data = installer.get_installation_info()
                if installation_data:
                    db_success = self.db_manager.add_app(installation_data)
                    if db_success:
                        logger.info(f"Application '{installer.app_info.get('name')}' added to database.")
                        self.update_status(translator.get_text("Installation complete and registered."), is_success=True)
                        self.progress_bar.setValue(100)
                        # Navigate to manage page using the direct main_window reference
                        try:
                            if self.main_window and hasattr(self.main_window, 'select_sidebar_item_by_index'):
                                self.main_window.select_sidebar_item_by_index(1) 
                            else:
                                logger.warning("Could not navigate: main_window reference or method missing.")
                        except Exception as nav_e: # Catch any unexpected error during navigation
                            logger.error(f"Error navigating to Manage page: {nav_e}", exc_info=True)
                    else:
                        logger.error("Installation completed, but failed to register in database.")
                        self.update_status(translator.get_text("Installation finished, but DB registration failed."), is_error=True)
                else:
                     logger.error("Could not retrieve installation info after successful installation steps.")
                     self.update_status(translator.get_text("Installation steps succeeded, but failed to get info for DB."), is_error=True)
            elif installer.requires_root: # Only show this if root install failed
                 logger.error("Root installation failed, not adding to database.")
                 # Status already updated in the loop on failure
            else: # User/Custom mode install failed earlier
                 logger.error(f"{install_mode} installation failed, not adding to database.")
                 # Status should have been updated in the install blocks

        except Exception as e:
            logger.error(f"Installation failed: {e}", exc_info=True)
            self.update_status(f"{translator.get_text('Installation failed:')} {e}", is_error=True)
        finally:
            self.progress_bar.setVisible(False)
            self.install_button.setEnabled(True)
            self.user_mode_radio.setEnabled(True)
            self.system_mode_radio.setEnabled(True)
            self.custom_mode_radio.setEnabled(True)
            self.custom_path_input.setEnabled(True)
            self.custom_path_button.setEnabled(True)
            
            # Clean up temporary directories
            for temp_dir in self.temp_dirs:
                try:
                    if os.path.exists(temp_dir):
                        shutil.rmtree(temp_dir)
                        logger.debug(f"Removed temporary directory: {temp_dir}")
                except Exception as e:
                    logger.warning(f"Could not remove temporary directory {temp_dir}: {e}")
            
            # --- Script cleanup is no longer needed ---

    def set_ui_installing(self, installing):
         """Enable/disable UI elements during installation."""
         self.install_button.setEnabled(not installing)
         self.select_file_button.setEnabled(not installing)
         self.user_mode_radio.setEnabled(not installing)
         self.system_mode_radio.setEnabled(not installing)
         self.custom_mode_radio.setEnabled(not installing)
         self.custom_path_input.setEnabled(not installing)
         self.custom_path_button.setEnabled(not installing)
         self.progress_bar.setVisible(installing)
         self.status_label.setVisible(installing)
    
    def update_status(self, message, is_error=False, is_success=False, warning=False):
        """Updates the status label text and style."""
        self.status_label.setText(message)
        style = "color: black;" # Default style
        if is_error:             # Use is_error
            style = "color: red;"
        elif warning:
            style = "color: orange;" # Keep warning for now
        elif is_success:         # Use is_success
            style = "color: green;" # Add green for success
        
        self.status_label.setStyleSheet(style) # Apply the determined style
        self.status_label.setVisible(True)
        QApplication.processEvents() # Ensure status update is visible (moved here)

    def set_file_path(self, file_path):
        """Sets the file path and processes the file - used for drag and drop"""
        if file_path and os.path.exists(file_path):
            self.selected_file_label.setText(file_path)
            self.process_selected_file(file_path)
            self.install_button.setEnabled(True)
            self.info_group.setVisible(True)
            self.options_group.setVisible(True)
            self.status_label.setVisible(False)
            self.progress_bar.setVisible(False)
            logger.info(f"AppImage set via drag-drop: {file_path}")
            # If the file is set via drag and drop, ensure the page is visible and active
            # This is needed if we're dragging onto the main window which might have a different page selected
            if self.parentWidget() and hasattr(self.parentWidget(), 'sidebar'):
                self.parentWidget().select_sidebar_item_by_index(0)  # Select the Install page

    def retranslateUi(self):
        """Update all UI texts for language changes"""
        translator = get_translator()  # Get fresh translator
        # Retranslate file selection controls
        self.file_label.setText(translator.get_text("lbl_app_file"))
        self.selected_file_label.setPlaceholderText(translator.get_text("lbl_no_file_selected"))
        self.select_file_button.setText(translator.get_text("btn_select_appimage"))
        # Retranslate info and options group titles
        self.info_group.setTitle(translator.get_text("lbl_app_info"))
        self.options_group.setTitle(translator.get_text("grp_installation_options"))
        # Retranslate installation mode options
        self.user_mode_radio.setText(translator.get_text("install_mode_user"))
        self.system_mode_radio.setText(translator.get_text("install_mode_system"))
        self.custom_mode_radio.setText(translator.get_text("install_mode_custom"))
        self.add_to_library_radio.setText(translator.get_text("install_mode_add_to_library"))

        # Update group box titles
        self.info_group.setTitle(translator.get_text("lbl_app_info"))
        self.options_group.setTitle(translator.get_text("grp_installation_options"))

        # Update buttons
        self.custom_path_button.setText(translator.get_text("btn_browse"))
        self.install_button.setText(translator.get_text("install_button"))
        # Retranslate recent button if it exists
        if hasattr(self, 'recent_button'):
            self.recent_button.setText(translator.get_text("Recent AppImages"))

        # Update labels
        self.custom_path_input.setPlaceholderText(translator.get_text("Select custom installation directory"))

        # FormLayout labels
        form_layout = self.info_group.layout()
        if form_layout:
            for i in range(form_layout.rowCount()):
                label_item = form_layout.itemAt(i, QFormLayout.ItemRole.LabelRole)
                if label_item and label_item.widget():
                    if i == 1:  # Name row
                        label_item.widget().setText(translator.get_text("Name:"))
                    elif i == 2:  # Version row
                        label_item.widget().setText(translator.get_text("Version:"))

        # Update status text if visible
        if self.status_label.isVisible():
            current_status = self.status_label.text()
            # Here you could implement a more sophisticated way to translate
            # existing status messages, but this is simplified
            if "Error" in current_status:
                self.status_label.setText(translator.get_text("Error"))
            elif "Installing" in current_status:
                self.status_label.setText(translator.get_text("Installing..."))
            else:
                self.status_label.setText(translator.get_text("Ready"))

    def show_recent_popup(self):
        """Show recent AppImages via a styled QMenu that auto-closes on click-away and selection."""
        from PyQt6.QtCore import QPoint, Qt
        from PyQt6.QtWidgets import QMenu
        from PyQt6.QtGui import QAction
        # Build the menu
        menu = QMenu(self)
        # Make it a Popup and delete on close so clicking away hides it
        menu.setWindowFlags(menu.windowFlags() | Qt.WindowType.Popup)
        menu.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose, True)
        for path in self._recent_paths:
            act = QAction(QIcon.fromTheme("application-x-appimage"), os.path.basename(path), menu)
            act.setData(path)
            menu.addAction(act)

        # Apply theme-aware styling
        dark = getattr(self.window(), 'dark_mode', False)
        bg = '#333333' if dark else '#ffffff'
        text = '#ffffff' if dark else '#000000'
        border = '#555555' if dark else '#cccccc'
        # Use stronger semi-transparent white hover in dark for better contrast, light gray in light
        hover = 'rgba(255, 255, 255, 0.3)' if dark else '#e0e0e0'
        style = f"""
QMenu {{
    background-color: {bg};
    color: {text};
    border: 1px solid {border};
    border-radius: 8px;
}}
QMenu::item {{
    padding: 8px;
    margin: 2px;
    border-radius: 4px;
}}
/* highlight on hover or selection */
QMenu::item:selected,
QMenu::item:hover {{
    background-color: {hover};
}}
"""
        menu.setStyleSheet(style)

        # Execute menu; exec() blocks and auto-closes on click-away
        pos = self.recent_button.mapToGlobal(QPoint(0, self.recent_button.height()))
        selected_action = menu.exec(pos)
        if selected_action:
            path = selected_action.data()
            self.selected_file_label.setText(path)
            self.process_selected_file(path)
            self.install_button.setEnabled(True)
            self.info_group.setVisible(True)
            self.options_group.setVisible(True)
            self.status_label.setVisible(False)
            self.progress_bar.setVisible(False)

# --- Logger Setup (Example - Adapt as needed) ---
# Needs to be configured properly, potentially passed in or using a global setup
import logging
logger = logging.getLogger(__name__)
if not logger.hasHandlers():
    # Add basic handler if none exist, prevents 'No handlers could be found' error
    handler = logging.StreamHandler()
    formatter = logging.Formatter('%(levelname)s: %(name)s: %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.setLevel(logging.INFO) 