"""
AppImage Manager - Install Page UI
Provides the graphical interface for selecting and installing an AppImage.
"""

from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, 
                             QPushButton, QFileDialog, QGroupBox, QRadioButton, 
                             QProgressBar, QSpacerItem, QSizePolicy, QFormLayout)
from PyQt6.QtCore import Qt, QTimer
import os

import config
# from i18n import _ # Remove this import
from i18n import get_translator # Import the getter function
from appimage_utils import AppImageInstaller # ADD THIS IMPORT
from db_manager import DBManager # ADD THIS IMPORT
import sudo_helper # ADD THIS IMPORT

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
        self.select_file_button = QPushButton(translator.get_text("Select AppImage File..."))
        self.select_file_button.clicked.connect(self.select_file)
        self.selected_file_label = QLineEdit()
        self.selected_file_label.setPlaceholderText(translator.get_text("No file selected"))
        self.selected_file_label.setReadOnly(True)
        
        file_selection_layout.addWidget(QLabel(translator.get_text("AppImage File:")))
        file_selection_layout.addWidget(self.selected_file_label)
        file_selection_layout.addWidget(self.select_file_button)
        main_layout.addLayout(file_selection_layout)
        main_layout.addSpacing(15) # Add spacing after file selection

        # --- AppImage Information (Placeholders) ---
        self.info_group = QGroupBox(translator.get_text("AppImage Information"))
        info_layout = QFormLayout() # Use QFormLayout for better alignment
        info_layout.setContentsMargins(10, 15, 10, 10) # Add margins inside groupbox
        info_layout.setSpacing(10) # Spacing between rows
        self.app_name_label = QLabel("-") # Label text set by addRow
        self.app_version_label = QLabel("-") # Label text set by addRow
        self.app_icon_label = QLabel() # TODO: Add icon display later
        # Add more labels as needed (description, etc.)
        
        info_layout.addRow(translator.get_text("Name:"), self.app_name_label)
        info_layout.addRow(translator.get_text("Version:"), self.app_version_label)
        # info_layout.addWidget(self.app_icon_label) # Add icon later
        self.info_group.setLayout(info_layout)
        self.info_group.setVisible(False) # Initially hidden until file selected
        main_layout.addWidget(self.info_group)
        main_layout.addSpacing(15) # Add spacing after info group

        # --- Installation Options ---
        self.options_group = QGroupBox(translator.get_text("Installation Options"))
        options_layout = QVBoxLayout()
        options_layout.setContentsMargins(10, 15, 10, 10) # Add margins inside groupbox
        options_layout.setSpacing(10) # Spacing between elements
        
        # Install Mode
        mode_layout = QHBoxLayout()
        self.user_mode_radio = QRadioButton(translator.get_text("User Installation") + f" ({config.INSTALL_DESTINATIONS['user']['description']})")
        self.system_mode_radio = QRadioButton(translator.get_text("System Installation") + f" ({config.INSTALL_DESTINATIONS['system']['description']})")
        self.custom_mode_radio = QRadioButton(translator.get_text("Custom Location"))
        
        self.user_mode_radio.setChecked(config.DEFAULT_INSTALL_MODE == "user")
        self.system_mode_radio.setChecked(config.DEFAULT_INSTALL_MODE == "system")
        self.custom_mode_radio.setChecked(config.DEFAULT_INSTALL_MODE == "custom")

        mode_layout.addWidget(self.user_mode_radio)
        mode_layout.addWidget(self.system_mode_radio)
        mode_layout.addWidget(self.custom_mode_radio)
        options_layout.addLayout(mode_layout)
        
        # Custom Path (Initially hidden)
        self.custom_path_layout = QHBoxLayout()
        self.custom_path_input = QLineEdit()
        self.custom_path_button = QPushButton("...") # Browse button
        self.custom_path_input.setPlaceholderText(translator.get_text("Select custom installation directory"))
        self.custom_path_button.setFixedWidth(30)
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
        self.custom_path_button.clicked.connect(self.select_custom_path)

        self.options_group.setLayout(options_layout)
        self.options_group.setVisible(False) # Initially hidden
        main_layout.addWidget(self.options_group)
        main_layout.addSpacing(20) # Add spacing before install button

        # --- Install Button ---
        self.install_button = QPushButton(translator.get_text("Install"))
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
        try:
            # Create a temporary installer instance just to read initial metadata
            # We don't need a specific install_mode just for this.
            temp_installer = AppImageInstaller(file_path)
            app_info = temp_installer.app_info
            
            app_name = app_info.get("name", os.path.basename(file_path).replace(".AppImage", ""))
            app_version = app_info.get("version", translator.get_text("Unknown"))
            
            self.app_name_label.setText(app_name) 
            self.app_version_label.setText(app_version)
            logger.info(f"Extracted initial info: Name='{app_name}', Version='{app_version}'")
            # TODO: Add icon extraction/display if possible without full extract later
            
            # Enable install button now that we have basic info
            self.install_button.setEnabled(True)
            self.info_group.setVisible(True)
            self.options_group.setVisible(True)

        except Exception as e:
            logger.error(f"Error processing selected file '{file_path}': {e}")
            # Update UI to show error
            self.app_name_label.setText(translator.get_text("Error"))
            self.app_version_label.setText(translator.get_text("Could not read metadata"))
            self.install_button.setEnabled(False)
            self.info_group.setVisible(True) # Show info group even on error to display message
            self.options_group.setVisible(False)

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
        """Starts the actual installation process based on selected options."""
        appimage_path = self.selected_file_label.text()
        if not appimage_path or not os.path.exists(appimage_path):
            self.update_status(translator.get_text("Error: Please select a valid AppImage file first."), error=True)
            return

        # Determine selected install mode
        install_mode = "user" # Default
        custom_path = None
        if self.system_mode_radio.isChecked():
            install_mode = "system"
        elif self.custom_mode_radio.isChecked():
            install_mode = "custom"
            custom_path = self.custom_path_input.text()
            if not custom_path or not os.path.isdir(custom_path):
                self.update_status(translator.get_text("Error: Please select a valid custom installation directory."), error=True)
                return
        
        logger.info(f"Starting installation for '{appimage_path}' (Mode: {install_mode}, Custom Path: {custom_path})")
        self.set_ui_installing(True)
        self.update_status(translator.get_text("Initializing installation..."))
        self.progress_bar.setRange(0, 100) # Use range 0-100 for steps
        self.progress_bar.setValue(5)

        try:
            # 1. Create Installer Instance
            installer = AppImageInstaller(appimage_path, install_mode, custom_path)
            self.progress_bar.setValue(10)

            # 2. Prerequisite Check (Example - enhance later)
            prereqs = installer.check_prerequisites()
            if not prereqs.get("appimage_executable"):
                # Log a warning instead of raising an error, as extraction might still work
                logger.warning(f"AppImage file '{appimage_path}' is not executable. Attempting extraction anyway.")
                # Optionally show a non-critical warning to the user here if desired
                # self.update_status(translator.get_text("Warning: AppImage file is not executable."), warning=True)
            if not prereqs.get("libfuse_installed"):
                 logger.warning("libFUSE might be missing, continuing anyway...")
                 # self.update_status(translator.get_text("Warning: libFUSE missing, installation might fail."))
            # Root/permission checks are implicitly handled below
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
                     # This might not be critical, maybe just log a warning? 
                     logger.warning("Failed to create one or more symlinks.")
                     # For now, treat as success but log it.
                     # raise RuntimeError(translator.get_text("Failed to create system integration links."))
                self.progress_bar.setValue(80)
                success = True # Assume success if file copy worked, symlinks are bonus
            
            # 5. Add to Database (if successful)
            if success:
                self.update_status(translator.get_text("Registering application..."))
                # QApplication.processEvents()
                app_info = installer.get_installation_info()
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
            if 'installer' in locals(): # Check if installer was created
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

        # Update group box titles
        self.info_group.setTitle(translator.get_text("AppImage Information"))
        self.options_group.setTitle(translator.get_text("Installation Options"))

        # Update radio buttons
        self.user_mode_radio.setText(translator.get_text("User Installation") + f" ({config.INSTALL_DESTINATIONS['user']['description']})")
        self.system_mode_radio.setText(translator.get_text("System Installation") + f" ({config.INSTALL_DESTINATIONS['system']['description']})")
        self.custom_mode_radio.setText(translator.get_text("Custom Location"))

        # Update buttons
        self.select_file_button.setText(translator.get_text("Select AppImage File..."))
        self.custom_path_button.setText("...")
        self.install_button.setText(translator.get_text("Install"))

        # Update labels
        self.selected_file_label.setPlaceholderText(translator.get_text("No file selected"))
        self.custom_path_input.setPlaceholderText(translator.get_text("Select custom installation directory"))

        # FormLayout labels
        form_layout = self.info_group.layout()
        if form_layout:
            for i in range(form_layout.rowCount()):
                label_item = form_layout.itemAt(i, QFormLayout.ItemRole.LabelRole)
                if label_item and label_item.widget():
                    if i == 0:  # Name
                        label_item.widget().setText(translator.get_text("Name:"))
                    elif i == 1:  # Version
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