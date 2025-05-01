"""
AppImage Manager - Install Page UI
Provides the graphical interface for selecting and installing an AppImage.
"""

from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, 
                             QPushButton, QFileDialog, QGroupBox, QRadioButton, 
                             QProgressBar, QSpacerItem, QSizePolicy, QFormLayout,
                             QToolButton, QMenu, QListWidget, QListWidgetItem)
from PyQt6.QtCore import Qt, QTimer, QPoint, QEvent, QCoreApplication
import os
from PyQt6.QtGui import QIcon, QAction, QPixmap
# from PyQt6.QtWidgets import QGraphicsDropShadowEffect # Unused import
import uuid
import datetime
import shutil

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
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("installPage")
        
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
        self.install_button = QPushButton(translator.get_text("btn_install"))
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

                # 6. Call integration function using the COPIED path
                self.update_status(translator.get_text("Creating shortcuts..."))
                created_bin_link, created_desktop_file = integration.register_appimage_integration(
                    copied_appimage_path, # Use the path to the copy!
                    app_info, 
                    temp_icon_path
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
                        self.update_status(translator.get_text("Application added to library successfully!")) # New success message
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

            # 4. Install Files & Create Symlinks
            success = False
            if installer.requires_root:
                self.update_status(translator.get_text("Root privileges required. Requesting password..."))
                # QApplication.processEvents()
                commands = installer.get_install_commands()
                if not commands:
                     raise RuntimeError(translator.get_text("Failed to generate installation commands for root execution."))
                
                logger.debug(f"Executing commands with sudo: {commands}")
                # Execute commands with sudo helper
                success, output = sudo_helper.execute_commands_with_sudo(commands)
                if not success:
                    logger.error(f"Sudo command execution failed. Output: {output}")
                    raise RuntimeError(translator.get_text("Installation failed during command execution (requires root). Check logs for details."))
                else:
                     logger.info("Sudo commands executed successfully.")
                     self.progress_bar.setValue(80)

            else: # Non-root installation
                self.update_status(translator.get_text("Copying application files..."))
                # QApplication.processEvents()
                if not installer.install_files():
                     raise RuntimeError(translator.get_text("Failed to copy application files."))
                self.progress_bar.setValue(60)
                
                self.update_status(translator.get_text("Creating system integration (symlinks)..."))
                # QApplication.processEvents()
                if not installer.create_symlinks():
                    # Treat symlink failure as critical error
                    logger.error("Failed to create system integration links.")
                    raise RuntimeError(translator.get_text("Failed to create system integration links."))
                self.progress_bar.setValue(80)
                success = True # Assume success if file copy worked, symlinks are bonus
            
            # 5. Add to Database (if successful)
            if success:
                self.update_status(translator.get_text("Registering application..."))
                # QApplication.processEvents()
                app_info = installer.get_installation_info()
                # IMPORTANT: Explicitly set management type for installed apps
                app_info["management_type"] = config.MGMT_TYPE_INSTALLED 
                try:
                    db = DBManager()
                    if db.add_app(app_info):
                        logger.info(f"Application '{app_info.get('name')}' added to database.")
                        self.progress_bar.setValue(95)
                    else:
                        logger.error("Failed to add application to database.")
                        # Don't fail the whole install, but warn
                        self.update_status(translator.get_text("Installation completed, but failed to register in database."), warning=True)
                except Exception as db_err:
                     logger.error(f"Database error after installation: {db_err}")
                     self.update_status(translator.get_text("Installation completed, but database error occurred."), warning=True)

                self.progress_bar.setValue(100)
                self.update_status(translator.get_text("Installation successful!"))
            else:
                 # Should have been caught by exceptions earlier, but as a fallback
                 raise RuntimeError(translator.get_text("Installation failed for an unknown reason."))

        except Exception as e:
            logger.error(f"Installation failed: {e}", exc_info=True)
            self.update_status(f"{translator.get_text('Installation failed')}: {e}", error=True)
            self.progress_bar.setValue(0) # Reset progress on error
        finally:
            # 6. Cleanup (always attempt)
            if installer: # Check if installer object was created
                 logger.info("Performing cleanup...")
                 installer.cleanup()
            # Re-enable UI elements after a short delay to let user see final status
            QTimer.singleShot(1500, lambda: self.set_ui_installing(False))
            # Re-enable buttons even on failure
            # self.set_ui_installing(False)

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
    
    def update_status(self, message, error=False, warning=False):
        """Updates the status label text and style."""
        self.status_label.setText(message)
        if error:
            self.status_label.setStyleSheet("color: red;")
        elif warning:
            self.status_label.setStyleSheet("color: orange;")
        else:
            self.status_label.setStyleSheet("color: black;")
        self.status_label.setVisible(True)
        # QApplication.processEvents() # Ensure status update is visible

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
        self.install_button.setText(translator.get_text("btn_install"))
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