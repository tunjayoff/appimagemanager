"""
AppImage Manager - Manage Page UI
Provides the graphical interface for listing and managing installed AppImages.
"""

from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                             QPushButton, QTableWidget, QTableWidgetItem, 
                             QAbstractItemView, QHeaderView, QMessageBox,
                             QProgressBar, QApplication, QToolButton, QSizePolicy,
                             QLineEdit, QDialog, QListWidget, QCheckBox, 
                             QDialogButtonBox, QListWidgetItem)
from PyQt6.QtGui import QIcon, QColor, QPixmap
from PyQt6.QtCore import Qt, QTimer, QSize, QPoint, QEvent
import os
import logging
import shutil # Import shutil for rmtree and which

logger = logging.getLogger(__name__)
import subprocess # For running applications

from .. import config
from ..i18n import get_translator
from ..db_manager import DBManager # To interact with the database
from .. import sudo_helper # ADD THIS IMPORT
from .. import appimage_utils # Import appimage_utils for leftover functions
from .. import uninstaller # Import the new uninstaller module
# Import other necessary modules like appimage_utils or sudo_helper later

# Get the translator instance
translator = get_translator()

class ManagePage(QWidget):
    """UI elements for managing installed AppImages."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("managePage")
        
        # --- Main Layout ---
        main_layout = QVBoxLayout(self)

        # --- Search Box ---
        search_layout = QHBoxLayout()
        search_label = QLabel(translator.get_text("Search:"))
        self.search_box = QLineEdit()
        self.search_box.setPlaceholderText(translator.get_text("Search by name, version..."))
        self.search_box.setClearButtonEnabled(True)
        search_layout.addWidget(search_label)
        search_layout.addWidget(self.search_box)
        main_layout.addLayout(search_layout)

        # --- Toolbar ---
        toolbar_layout = QHBoxLayout()
        self.refresh_button = QPushButton(QIcon.fromTheme("view-refresh"), translator.get_text("Refresh List"))
        self.scan_leftovers_button = QPushButton(QIcon.fromTheme("edit-find"), translator.get_text("Scan for Leftovers"))
        self.clean_orphans_button = QPushButton(QIcon.fromTheme("edit-clear"), translator.get_text("Clean Orphaned Files"))
        self.uninstall_button = QPushButton(QIcon.fromTheme("edit-delete"), translator.get_text("Uninstall Selected"))
        self.run_button = QPushButton(QIcon.fromTheme("media-playback-start"), translator.get_text("Run Application"))
        self.run_button.setEnabled(False) # Disable initially
        self.uninstall_button.setEnabled(False) # Disable initially
        
        toolbar_layout.addWidget(self.refresh_button)
        toolbar_layout.addWidget(self.scan_leftovers_button)
        toolbar_layout.addWidget(self.clean_orphans_button)
        toolbar_layout.addStretch(1)
        toolbar_layout.addWidget(self.run_button)
        toolbar_layout.addWidget(self.uninstall_button)
        main_layout.addLayout(toolbar_layout)

        # --- Application Table ---
        self.app_table = QTableWidget()
        self.app_table.setColumnCount(5) # Icon, Name, Version, Path, Status
        self.app_table.setHorizontalHeaderLabels([
            "", # Icon column
            translator.get_text("Application Name"), 
            translator.get_text("Version"), 
            translator.get_text("Installation Path"),
            translator.get_text("Status")
        ])
        # Table visual settings
        self.app_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.app_table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.app_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers) # Read-only
        self.app_table.verticalHeader().setVisible(False) # Hide row numbers
        self.app_table.horizontalHeader().setStretchLastSection(True)
        # Adjust column widths (Icon column narrow, Name wider)
        self.app_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.app_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Interactive)
        self.app_table.setColumnWidth(1, 250) # Initial width for Name
        self.app_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.app_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch) # Path stretches
        self.app_table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents) # Status column fits content
        # Set bigger icon size
        self.app_table.setIconSize(QSize(32, 32))

        main_layout.addWidget(self.app_table)
        
        # --- Status Bar ---
        status_layout = QHBoxLayout()
        
        # Status label
        self.status_label = QLabel(translator.get_text("Ready"))
        
        # Progress bar (hidden initially)
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 0)  # Indeterminate progress
        self.progress_bar.setVisible(False)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setMaximumHeight(10)  # Make it less obtrusive
        
        status_layout.addWidget(self.status_label)
        status_layout.addWidget(self.progress_bar)
        status_layout.setStretch(0, 1)  # Give the label more space
        
        main_layout.addLayout(status_layout)

        # --- Connect Signals ---
        self.refresh_button.clicked.connect(self.refresh_app_list)
        self.scan_leftovers_button.clicked.connect(self.scan_for_leftover_installs)
        self.clean_orphans_button.clicked.connect(self.scan_for_orphaned_files)
        self.uninstall_button.clicked.connect(self.uninstall_selected_app)
        self.run_button.clicked.connect(self.run_selected_app)
        self.app_table.itemSelectionChanged.connect(self.update_button_states)
        self.app_table.doubleClicked.connect(self.handle_table_double_click)
        self.search_box.textChanged.connect(self.filter_apps)

        # --- Initial Population ---
        self.refresh_app_list() # Load list on startup
        
    def show_loading(self, is_loading=True, message=None):
        """Show or hide loading indicator and set status message"""
        if is_loading:
            self.progress_bar.setVisible(True)
            self.refresh_button.setEnabled(False)
            self.run_button.setEnabled(False)
            self.uninstall_button.setEnabled(False)
            if message:
                self.status_label.setText(message)
            QApplication.processEvents()  # Force UI update
        else:
            self.progress_bar.setVisible(False)
            self.refresh_button.setEnabled(True)
            self.update_button_states()  # Re-check if buttons should be enabled
            if message:
                self.status_label.setText(message)
            QApplication.processEvents()  # Force UI update

    def refresh_app_list(self):
        """Loads installed applications from the database and populates the table."""
        logger.info("Refreshing installed app list...")
        self.show_loading(True, translator.get_text("Loading applications..."))
        
        self.app_table.setRowCount(0) # Clear existing rows
        try:
            db = DBManager()
            apps = db.get_all_apps()
            
            self.app_table.setRowCount(len(apps))
            for row, app_data in enumerate(apps):
                is_missing = False # Flag to track if files are missing
                install_path = app_data.get("install_path")
                if not install_path or not os.path.exists(install_path):
                    # For registered apps, install_path might be the AppImage path itself
                    if app_data.get('management_type') == config.MGMT_TYPE_REGISTERED:
                         if not os.path.exists(app_data.get("appimage_path", "")):
                             is_missing = True
                             logger.warning(f"Registered AppImage path not found: {app_data.get('appimage_path')}")
                         # Don't consider registered apps 'missing' just because install_path is empty
                    else:
                         is_missing = True
                         logger.warning(f"Installation path not found for app '{app_data.get('name')}': {install_path}")
                
                # Check executable link for non-registered
                exec_link = app_data.get("executable_symlink")
                if app_data.get('management_type') != config.MGMT_TYPE_REGISTERED and (not exec_link or not os.path.exists(exec_link)):
                    is_missing = True
                    logger.warning(f"Executable symlink missing for '{app_data.get('name')}': {exec_link}")
                
                # Check desktop file link
                desktop_link = app_data.get("desktop_file_path")
                if not desktop_link or not os.path.exists(desktop_link):
                    is_missing = True
                    logger.warning(f"Desktop file link missing for '{app_data.get('name')}': {desktop_link}")
                
                # --- Icon --- 
                icon_item = QTableWidgetItem()
                icon = QIcon.fromTheme("application-x-appimage") # Default icon
                
                # Try different sources for the icon
                icon_found = False
                
                # 1. Try icon_path from database
                if app_data.get("icon_path") and os.path.exists(app_data["icon_path"]):
                    icon = QIcon(app_data["icon_path"])
                    icon_found = True
                
                # 2. Try standard icon locations with app_name
                if not icon_found and app_data.get("name"):
                    app_name = app_data.get("name").lower()
                    # Check in standard user icon locations
                    icon_dirs = [
                        os.path.join(config.USER_HOME, ".local/share/icons/hicolor"),
                        "/usr/share/icons/hicolor"
                    ]
                    for icon_dir in icon_dirs:
                        if os.path.exists(icon_dir):
                            # Check common sizes in reverse order (prefer larger)
                            for size in ["128x128", "64x64", "48x48", "32x32"]:
                                for ext in [".png", ".svg"]:
                                    icon_path = os.path.join(icon_dir, size, "apps", f"{app_name}{ext}")
                                    if os.path.exists(icon_path):
                                        icon = QIcon(icon_path)
                                        icon_found = True
                                        break
                                if icon_found:
                                    break
                        if icon_found:
                            break
                            
                # Set the icon and make it bigger
                icon_item.setIcon(icon)
                self.app_table.setItem(row, 0, icon_item)

                # --- Name --- 
                name_item = QTableWidgetItem(app_data.get("name", translator.get_text("Unknown")))
                self.app_table.setItem(row, 1, name_item)

                # --- Version --- 
                version_item = QTableWidgetItem(app_data.get("version", "-"))
                self.app_table.setItem(row, 2, version_item)

                # --- Path --- 
                display_path = app_data.get("install_path", translator.get_text("N/A")) 
                path_item = QTableWidgetItem(display_path)
                self.app_table.setItem(row, 3, path_item)

                # --- Status --- 
                status_text = translator.get_text("OK") if not is_missing else translator.get_text("Missing")
                status_item = QTableWidgetItem(status_text)
                self.app_table.setItem(row, 4, status_item)

                # Store the entire app_data dictionary for later retrieval
                name_item.setData(Qt.ItemDataRole.UserRole, app_data) # <-- Store the whole dict
                # Store the missing status as well
                name_item.setData(Qt.ItemDataRole.UserRole + 1, is_missing)
                # Store the executable path (No longer needed here, as it's in app_data)
                # name_item.setData(Qt.ItemDataRole.UserRole + 2, app_data.get("executable_path"))
                # Log the ID being set for debugging
                logger.debug(f"Setting data for row {row}: AppData keys: {list(app_data.keys()) if app_data else None}, Missing={is_missing}") # Log keys instead of just ID

                # --- Apply visual style if missing --- 
                if is_missing:
                    missing_color = QColor(Qt.GlobalColor.gray)
                    icon_item.setForeground(missing_color)
                    name_item.setForeground(missing_color)
                    version_item.setForeground(missing_color)
                    path_item.setForeground(missing_color)
                    status_item.setForeground(QColor("orange")) # Make status stand out

            logger.info(f"Loaded {len(apps)} applications into the table.")
            self.show_loading(False, translator.get_text("Ready"))
        except Exception as e:
            logger.error(f"Failed to load application list: {e}", exc_info=True)
            self.show_loading(False, translator.get_text("Error loading applications"))
            QMessageBox.warning(self, translator.get_text("Error"), 
                                translator.get_text("Could not load the list of installed applications. Check logs for details."))
        finally:
            self.update_button_states() # Ensure button state is correct after refresh
            
    def handle_table_double_click(self, index):
        """Handle double-clicking on a table row - run the app if not missing"""
        # Get the selected row
        row = index.row()
        name_item = self.app_table.item(row, 1)
        if not name_item:
            return
            
        # Check if app is missing
        is_missing = name_item.data(Qt.ItemDataRole.UserRole + 1)
        if is_missing:
            QMessageBox.information(self, 
                translator.get_text("Cannot Run"), 
                translator.get_text("This application is missing its files and cannot be run."))
            return
            
        # If not missing, run the app
        self.run_selected_app()

    def update_button_states(self):
        """Enables or disables buttons based on table selection."""
        selected_items = self.app_table.selectedItems()
        has_selection = len(selected_items) > 0
        
        self.uninstall_button.setEnabled(has_selection)
        
        # Only enable Run button if the app is not missing
        if has_selection:
            selected_row = self.app_table.currentRow()
            name_item = self.app_table.item(selected_row, 1)
            if name_item:
                is_missing = name_item.data(Qt.ItemDataRole.UserRole + 1)
                self.run_button.setEnabled(not is_missing)
            else:
                self.run_button.setEnabled(False)
        else:
            self.run_button.setEnabled(False)
            
    def run_selected_app(self):
        """Run the selected application"""
        # logger.debug("Run button clicked!") # Remove print
        # print("--- DEBUG: run_selected_app CALLED ---")
        selected_items = self.app_table.selectedItems()
        # print(f"--- DEBUG: selected_items count: {len(selected_items)} ---")
        if not selected_items:
            # print("--- DEBUG: Exiting run_selected_app (no selected items) ---")
            return
            
        selected_row = self.app_table.currentRow()
        name_item = self.app_table.item(selected_row, 1)
        # print(f"--- DEBUG: selected_row: {selected_row}, name_item exists: {name_item is not None} ---")
        if not name_item:
            # print("--- DEBUG: Exiting run_selected_app (no name item) ---")
            return
            
        app_data = name_item.data(Qt.ItemDataRole.UserRole) # This will now be the dictionary
        # print(f"--- DEBUG: app_data exists: {app_data is not None} ---")
        if not app_data or not isinstance(app_data, dict): # Add type check for safety
            # print("--- DEBUG: Exiting run_selected_app (app_data is None or not a dict) ---")
            logger.error(f"Retrieved invalid app_data for row {selected_row}. Type: {type(app_data)}")
            return
        
        # --- Extract exec_path (remove print)
        exec_path = app_data.get("executable_symlink") # Default
        management_type = app_data.get('management_type')
        if management_type == config.MGMT_TYPE_REGISTERED:
             # Use the key that was actually saved during registration
             exec_path = app_data.get("executable_path") 
             
        # --- Check for FUSE before attempting to run ---
        found_fusermount = shutil.which('fusermount')
        found_fusermount3 = shutil.which('fusermount3')
        logger.debug(f"FUSE Check: fusermount found at: {found_fusermount}, fusermount3 found at: {found_fusermount3}")
        fuse_found = found_fusermount or found_fusermount3
        if not fuse_found:
            logger.warning("FUSE (fusermount/fusermount3) command not found in PATH. AppImage might fail to run.")
            QMessageBox.warning(self, 
                                translator.get_text("FUSE Missing"), 
                                translator.get_text("FUSE libraries (libfuse2 or fuse3) might be required to run this AppImage, but the 'fusermount' command was not found.\n\nPlease try installing FUSE using your package manager. For Debian/Ubuntu:\n\nsudo apt update && sudo apt install libfuse2"))
            return # Stop execution if FUSE seems missing
        
        if exec_path and os.path.exists(exec_path):
            app_name = app_data.get("name", "Application")
            logger.info(f"Attempting to run '{app_name}' from: {exec_path}")
            try:
                # Make executable if needed
                home_dir = os.path.expanduser("~") 
                if not os.access(exec_path, os.X_OK):
                    os.chmod(exec_path, os.stat(exec_path).st_mode | 0o111)
                    logger.info(f"Made '{exec_path}' executable.")
                
                # --->>> Run Popen capturing stderr <<<---
                process = subprocess.Popen(
                    [exec_path],
                    cwd=home_dir,
                    stdout=subprocess.PIPE, # Keep stdout captured (or DEVNULL if not needed)
                    stderr=subprocess.PIPE, # Capture stderr
                    text=True
                )
                
                # Try to read stderr quickly, but don't block forever
                stderr_output = ""
                try:
                    # Communicate might block, use poll/read or shorter timeout if problematic
                    _, stderr_output = process.communicate(timeout=2) 
                except subprocess.TimeoutExpired:
                    logger.warning(f"AppImage process '{app_name}' running in background, stderr not captured immediately.")
                    # Process continues in background
                except Exception as comm_err:
                    logger.error(f"Error during process communication for '{app_name}': {comm_err}")
                    
                if stderr_output:
                     logger.warning(f"stderr output from '{app_name}' process: {stderr_output.strip()}")
                     # Optional: Show stderr in a pop-up if it contains relevant keywords?
                     if "fuse" in stderr_output.lower() or "mount" in stderr_output.lower():
                           QMessageBox.warning(self, 
                                translator.get_text("AppImage Runtime Error"),
                                translator.get_text("The application reported an error, possibly related to FUSE:\n\n{error}\n\nEnsure FUSE libraries (e.g., libfuse2) are installed.").format(error=stderr_output.strip()))
                
                logger.info(f"Successfully launched '{app_name}'.")
            except Exception as e:
                logger.error(f"Failed to run '{app_name}' from {exec_path}: {e}", exc_info=True)
        else:
             # logger.error(f"Cannot run selected application: Executable path not found or invalid: {exec_path}")
             # print(f"--- DEBUG: Cannot run, exec_path invalid: {exec_path} ---")
             logger.error(f"Cannot run selected application: Executable path not found or invalid: {exec_path}") # Revert log
             QMessageBox.warning(self, translator.get_text("Error"), 
                                 translator.get_text("Cannot run application: Executable not found."))

    def uninstall_selected_app(self):
        """Starts the uninstallation process for the selected app, handling missing files."""
        selected_rows = self.app_table.selectionModel().selectedRows()
        if not selected_rows:
            return

        selected_row_index = selected_rows[0].row()
        name_item = self.app_table.item(selected_row_index, 1)
        if not name_item:
            logger.error("Could not get name item from selected row.")
            return

        # Retrieve the app_data dictionary and the missing status
        app_data_dict = name_item.data(Qt.ItemDataRole.UserRole) 
        is_missing = name_item.data(Qt.ItemDataRole.UserRole + 1)
        app_name = name_item.text() # Get app name for messages

        # Correctly extract the app_id from the dictionary
        app_id = None
        if isinstance(app_data_dict, dict):
            app_id = app_data_dict.get("id")
        else:
            # This case might occur if data is corrupted or old format
            logger.warning(f"Retrieved non-dict data for row {selected_row_index}. Type: {type(app_data_dict)}")
            # We might still have the ID if it was stored directly in an old version
            if isinstance(app_data_dict, (str, int)): # Check if it looks like an ID
                 app_id = app_data_dict 
                 logger.warning(f"Attempting to use retrieved value directly as ID: {app_id}")
            app_data_dict = None # Ensure app_info fetch below uses the ID

        # Handle case where App ID could not be determined
        if not app_id and not is_missing:
            logger.error(f"Corrupted entry for '{app_name}': Could not determine ID and files reported as present.")
            QMessageBox.critical(self, translator.get_text("Data Error"), 
                                 translator.get_text("The database entry for '{app_name}' is inconsistent (missing ID). Cannot proceed with uninstall.").format(app_name=app_name))
            return

        logger.info(f"Uninstall requested for App ID: {app_id} (Name: '{app_name}', Missing Files: {is_missing})")

        # 1. Ask for confirmation
        confirm_text = translator.get_text("Are you sure you want to uninstall '{app_name}'?").format(app_name=app_name)
        if is_missing:
            if app_id:
                confirm_text = translator.get_text("The files for '{app_name}' seem to be missing. Remove the database entry anyway?").format(app_name=app_name)
            else:
                confirm_text = translator.get_text("The files for '{app_name}' seem to be missing and it has no ID. Remove the corrupt database entry?").format(app_name=app_name)
        
        reply = QMessageBox.question(self, translator.get_text("Confirm Uninstall"), confirm_text,
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, 
                                     QMessageBox.StandardButton.No)

        if reply == QMessageBox.StandardButton.No:
            logger.info("Uninstall cancelled by user.")
            return

        # --- Start Uninstallation --- 
        self.show_loading(True, translator.get_text("Uninstalling {app_name}...").format(app_name=app_name))
        uninstallation_successful = False # Flag to track overall success for leftover check
        db_removal_done = False # Flag to track if DB part is done
        
        try:
            db = DBManager()
            # Fetch app_info using the correctly extracted app_id
            # If we started with a dict, use that directly for efficiency, otherwise fetch by ID
            app_info = app_data_dict if app_data_dict else db.get_app(app_id) 
            
            # --- Handle missing entry cases (slightly adapted logic) ---
            if not app_info and app_id:
                 # Stale entry with ID
                 logger.error(f"App info not found in DB for ID: {app_id}. Removing stale entry.")
                 if db.remove_app(app_id):
                      QMessageBox.information(self, translator.get_text("Stale Entry Removed"), translator.get_text("Removed stale database entry for '{app_name}'.").format(app_name=app_name))
                      uninstallation_successful = True # Consider this a success for potential leftover check
                      db_removal_done = True
                 else:
                      QMessageBox.warning(self, translator.get_text("Error"), translator.get_text("Could not remove stale database entry."))
                 # No files to remove here, proceed to finally block
                 
            elif not app_info and not app_id and is_missing:
                 # Corrupt entry without ID, files missing
                 logger.warning(f"Attempting to remove corrupt entry for '{app_name}' (no ID, files missing).")
                 all_apps = db.get_all_apps()
                 original_count = len(all_apps)
                 apps_to_keep = [app for app in all_apps 
                                 if not (app.get('name') == app_name and app.get('id') is None)]
                 
                 if len(apps_to_keep) < original_count:
                     db.data['installed_apps'] = apps_to_keep
                     if db._save_db():
                         logger.info(f"Successfully removed corrupt entry for '{app_name}'.")
                         # No actual files removed, but consider DB cleaned
                         uninstallation_successful = True 
                         db_removal_done = True
                         QMessageBox.information(self, translator.get_text("Entry Removed"), 
                                                 translator.get_text("Removed corrupt database entry for '{app_name}'.").format(app_name=app_name))
                     else:
                         logger.error(f"Failed to save database after removing corrupt entry for '{app_name}'.")
                         QMessageBox.critical(self, translator.get_text("Database Error"), translator.get_text("Failed to save the database after removing the entry."))
                 else:
                     logger.error(f"Could not find the corrupt entry for '{app_name}' to remove.")
                     QMessageBox.warning(self, translator.get_text("Error"), translator.get_text("Could not find the database entry to remove."))
                 # Proceed to finally block
                 
            elif app_info: # App found in DB (normal case or missing files case with ID)
                # --- File/Symlink Removal --- 
                files_removed_successfully = False
                uninstaller_instance = uninstaller.AppImageUninstaller(app_info) # Use the uninstaller class from the correct module
                
                if not is_missing:
                    logger.info("Attempting to remove application files and symlinks...")
                    if uninstaller_instance.requires_root:
                        commands = uninstaller_instance.get_uninstall_commands()
                        if commands:
                             logger.debug(f"Executing uninstall commands with sudo: {commands}")
                             # Make sure sudo_helper is imported and works
                             try:
                                 sudo_success, output = sudo_helper.run_commands_with_pkexec_script(commands)
                                 if sudo_success:
                                     logger.info("Sudo uninstall commands executed successfully.")
                                     files_removed_successfully = True
                                 else:
                                     logger.error(f"Sudo uninstall commands failed. Output: {output}")
                                     QMessageBox.critical(self, translator.get_text("Uninstall Error"), translator.get_text("Failed to remove application files/links (requires root). Check logs."))
                             except Exception as sudo_err:
                                  logger.error(f"Error executing sudo commands: {sudo_err}", exc_info=True)
                                  QMessageBox.critical(self, translator.get_text("Sudo Error"), translator.get_text("An error occurred while trying to run commands with root privileges."))
                        else:
                             logger.warning("Root required, but no uninstall commands generated.")
                             # Maybe some files were already gone? Treat as success for DB removal.
                             files_removed_successfully = True 
                    else: # Non-root uninstall
                        if uninstaller_instance.uninstall(): # Call the direct uninstall method
                            logger.info("Non-root uninstallation successful.")
                            files_removed_successfully = True
                        else:
                            logger.error("Non-root uninstallation failed or partially failed.")
                            QMessageBox.warning(self, translator.get_text("Uninstall Warning"), translator.get_text("Could not remove some files/links. Please check logs or filesystem manually."))
                            # Even if partial failure, proceed to DB removal
                            files_removed_successfully = True # Allow DB removal attempt
                else:
                     logger.info("Files marked as missing, skipping file/symlink removal.")
                     files_removed_successfully = True # Treat as success for DB removal step

                # --- Remove from Database --- 
                if files_removed_successfully:
                     logger.info(f"Removing application '{app_name}' from database...")
                     if app_id and db.remove_app(app_id):
                         logger.info("Successfully removed app from database.")
                         # Mark overall success for leftover check
                         uninstallation_successful = True 
                         db_removal_done = True
                         # Don't show final message yet, check for leftovers first
                         # QMessageBox.information(self, translator.get_text("Uninstall Successful"), ...) 
                     else:
                         logger.error(f"Removed files (or skipped), but failed to remove app from database (ID: {app_id})")
                         QMessageBox.critical(self, translator.get_text("Database Error"), translator.get_text("Removed application files, but failed to update the database. Please refresh."))
                else:
                     # Error message shown during file removal failure
                     logger.warning("Skipping database removal because file/symlink removal failed.")

            # --- Check for Leftovers (if uninstallation including DB removal was successful) ---
            if uninstallation_successful and db_removal_done:
                 logger.info(f"Checking for potential leftovers for '{app_name}'...")
                 try:
                     potential_leftovers = appimage_utils.find_leftovers(app_name)
                     if potential_leftovers:
                          logger.info(f"Found {len(potential_leftovers)} potential leftover items.")
                          dialog = LeftoverDialog(potential_leftovers, self)
                          if dialog.exec() == QDialog.DialogCode.Accepted:
                               selected_to_remove = dialog.get_selected_paths()
                               if selected_to_remove:
                                   logger.info(f"User chose to remove {len(selected_to_remove)} leftover items.")
                                   success, removed_count = appimage_utils.remove_selected_leftovers(selected_to_remove)
                                   if success:
                                       QMessageBox.information(self, translator.get_text("Leftovers Removed"),
                                                               translator.get_text("{count} leftover items removed successfully.").format(count=removed_count))
                                   else:
                                       QMessageBox.warning(self, translator.get_text("Leftover Removal Error"),
                                                           translator.get_text("Failed to remove some or all selected leftover items. Check logs."))
                               else:
                                   logger.info("User did not select any leftovers to remove.")
                          else:
                               logger.info("User cancelled leftover removal.")
                               
                          # Show final success message AFTER leftover check
                          self.show_loading(False, translator.get_text("Uninstallation of {app_name} completed").format(app_name=app_name))
                          QMessageBox.information(self, translator.get_text("Uninstall Successful"), 
                                                  translator.get_text("'{app_name}' has been successfully uninstalled.").format(app_name=app_name))
                     else:
                          logger.info("No potential leftovers found.")
                          # Show final success message if no leftovers found
                          self.show_loading(False, translator.get_text("Uninstallation of {app_name} completed").format(app_name=app_name))
                          QMessageBox.information(self, translator.get_text("Uninstall Successful"), 
                                                  translator.get_text("'{app_name}' has been successfully uninstalled.").format(app_name=app_name))
                 except Exception as leftover_err:
                      logger.error(f"Error during leftover check/removal: {leftover_err}", exc_info=True)
                      QMessageBox.warning(self, translator.get_text("Leftover Check Error"),
                                          translator.get_text("An error occurred while checking for leftover files."))
                      # Still show main success message even if leftover check failed
                      self.show_loading(False, translator.get_text("Uninstallation of {app_name} completed").format(app_name=app_name))
                      QMessageBox.information(self, translator.get_text("Uninstall Successful"), 
                                               translator.get_text("'{app_name}' has been successfully uninstalled (leftover check failed).").format(app_name=app_name))
            elif not db_removal_done: # If DB removal failed or wasn't reached
                 self.show_loading(False, translator.get_text("Uninstallation partially failed"))
                 # Previous error messages should guide the user

        except Exception as e:
            logger.error(f"An unexpected error occurred during uninstall: {e}", exc_info=True)
            self.show_loading(False, translator.get_text("Uninstallation error"))
            QMessageBox.critical(self, translator.get_text("Uninstall Error"), translator.get_text("An unexpected error occurred: {error}").format(error=e))
        finally:
            # Refresh the list regardless of outcome to show current state
            self.refresh_app_list()

    def _cleanup_icon_files(self, app_name):
        # This method might become redundant if AppImageUninstaller handles icon cleanup correctly
        # Keep it for now as a fallback or if direct icon path was stored?
        # ... (keep existing code for now) ...
        # Standard sizes to check for icons
        if not app_name:
            return
            
        logger.info(f"Cleaning up icon files for {app_name}")
        
        # Standard sizes to check for icons
        icon_sizes = ["16x16", "22x22", "24x24", "32x32", "48x48", "64x64", "128x128", "256x256", "512x512", "scalable"]
        icon_exts = [".png", ".svg", ".svgz", ".xpm"]
        
        # Base directories to check
        icon_dirs = [
            os.path.join(config.USER_HOME, ".local/share/icons/hicolor"),
            "/usr/share/icons/hicolor"  # This would require root to clean
        ]
        
        # Only try to clean user's directories unless we're root
        is_root = os.geteuid() == 0
        if not is_root:
            icon_dirs = [icon_dirs[0]]
        
        removed_count = 0
        for icon_dir in icon_dirs:
            if not os.path.exists(icon_dir):
                continue
                
            for size in icon_sizes:
                size_dir = os.path.join(icon_dir, size, "apps")
                if not os.path.exists(size_dir):
                    continue
                    
                for ext in icon_exts:
                    icon_path = os.path.join(size_dir, f"{app_name}{ext}")
                    if os.path.exists(icon_path):
                        try:
                            os.remove(icon_path)
                            logger.info(f"Removed icon file: {icon_path}")
                            removed_count += 1
                        except (OSError, PermissionError) as e:
                            logger.warning(f"Failed to remove icon file {icon_path}: {e}")
        
        # Update icon cache if we removed any files
        if removed_count > 0:
            try:
                if shutil.which("gtk-update-icon-cache"):
                    subprocess.run(
                        ["gtk-update-icon-cache", "-f", "-t", os.path.join(config.USER_HOME, ".local/share/icons/hicolor")],
                        check=False,
                        capture_output=True
                    )
                    logger.info("Updated icon cache after removing icon files")
            except Exception as e:
                logger.warning(f"Failed to update icon cache: {e}")
                
        return removed_count

    def filter_apps(self, search_text):
        """Filter the app table based on search text"""
        search_text = search_text.lower()
        
        # If empty, show all rows
        if not search_text:
            for row in range(self.app_table.rowCount()):
                self.app_table.setRowHidden(row, False)
            return
            
        # Otherwise, filter based on text
        for row in range(self.app_table.rowCount()):
            show_row = False
            
            # Check name (column 1)
            name_item = self.app_table.item(row, 1)
            if name_item and search_text in name_item.text().lower():
                show_row = True
                
            # Check version (column 2)
            version_item = self.app_table.item(row, 2)
            if version_item and search_text in version_item.text().lower():
                show_row = True
                
            # Check path (column 3)
            path_item = self.app_table.item(row, 3)
            if path_item and search_text in path_item.text().lower():
                show_row = True
                
            # Show/hide the row based on match
            self.app_table.setRowHidden(row, not show_row)

    def retranslateUi(self):
        """Update all UI texts for language changes"""
        translator = get_translator()  # Get fresh translator
        
        # Update buttons
        self.refresh_button.setText(translator.get_text("Refresh List"))
        self.scan_leftovers_button.setText(translator.get_text("Scan for Leftovers"))
        self.clean_orphans_button.setText(translator.get_text("Clean Orphaned Files"))
        self.uninstall_button.setText(translator.get_text("Uninstall Selected"))
        self.run_button.setText(translator.get_text("Run Application"))
        
        # Update search label and placeholder
        search_layout = self.search_box.parent().layout()
        if search_layout:
            for i in range(search_layout.count()):
                item = search_layout.itemAt(i)
                if item.widget() and isinstance(item.widget(), QLabel):
                    item.widget().setText(translator.get_text("Search:"))
        
        self.search_box.setPlaceholderText(translator.get_text("Search by name, version..."))
        
        # Update table headers
        self.app_table.setHorizontalHeaderLabels([
            "",  # Icon column
            translator.get_text("Application Name"),
            translator.get_text("Version"),
            translator.get_text("Installation Path"),
            translator.get_text("Status")
        ])
        
        # Update status label
        if not self.progress_bar.isVisible():
            self.status_label.setText(translator.get_text("Ready"))
            
        # Force update for the potentially problematic button
        self.scan_leftovers_button.setText(translator.get_text("Scan for Leftovers"))

    def scan_for_leftover_installs(self):
        """Scans for leftover/untracked installations and prompts the user to remove them."""
        logger.info("Starting leftover installation scan...")
        self.show_loading(True, translator.get_text("Scanning for leftovers..."))
        try:
            leftover_installs = appimage_utils.find_leftover_installs()
            self.show_loading(False)
            
            if not leftover_installs:
                logger.info("No leftover installations found.")
                QMessageBox.information(self, 
                                      translator.get_text("Leftover Scan Complete"),
                                      translator.get_text("No leftover installations found."))
            else:
                logger.info(f"Found {len(leftover_installs)} leftover installation(s).")
                dialog = LeftoverInstallDialog(leftover_installs, self)
                if dialog.exec() == QDialog.DialogCode.Accepted:
                    selected_to_remove = dialog.get_selected_paths()
                    if not selected_to_remove:
                         logger.info("User accepted leftover dialog but selected no items to remove.")
                         return
                         
                    logger.info(f"User chose to remove {len(selected_to_remove)} leftover installation(s).")
                    self.show_loading(True, translator.get_text("Removing leftovers..."))
                    
                    success_count = 0
                    fail_count = 0
                    for path in selected_to_remove:
                        if appimage_utils.remove_leftover_install(path):
                            success_count += 1
                        else:
                            fail_count += 1
                            
                    self.show_loading(False)
                    result_message = ""
                    if success_count > 0:
                         result_message += translator.get_text("Successfully removed {count} leftover installation(s).").format(count=success_count)
                    if fail_count > 0:
                        if result_message: result_message += "\n"
                        result_message += translator.get_text("Failed to remove {count} leftover installation(s). Check logs for details.").format(count=fail_count)
                    
                    if fail_count > 0:
                        QMessageBox.warning(self, translator.get_text("Leftover Removal Result"), result_message)
                    elif success_count > 0:
                        QMessageBox.information(self, translator.get_text("Leftover Removal Result"), result_message)
                        
                else:
                    logger.info("User cancelled leftover removal dialog.")
    
        except Exception as e:
            logger.error(f"Error during leftover scan: {e}", exc_info=True)
            self.show_loading(False, translator.get_text("Error during scan."))
            QMessageBox.critical(self, 
                               translator.get_text("Error"), 
                               translator.get_text("An error occurred while scanning for leftovers. Check logs."))

    def scan_for_orphaned_files(self):
        """Scans for orphaned .desktop files and presents them for removal."""
        logger.info("Scanning for orphaned integration files (.desktop)...")
        try:
            orphans = appimage_utils.find_orphaned_integrations()
            if orphans:
                logger.info(f"Found {len(orphans)} potential orphaned integration file(s).")
                # Re-use LeftoverSelectionDialog, formatting data appropriately
                dialog = LeftoverSelectionDialog(orphans, self)
                dialog.setWindowTitle(translator.get_text("Orphaned Integration Files"))
                dialog.findChild(QLabel).setText(translator.get_text("Found integration files (.desktop) that seem to be managed by this tool but don't belong to any known application. Select items to remove:"))
                
                if dialog.exec_() == QDialog.Accepted:
                    selected_paths = dialog.get_selected_paths()
                    if selected_paths:
                        logger.info(f"User selected {len(selected_paths)} orphaned integration files to remove.")
                        removed_count = 0
                        overall_success = True
                        for path in selected_paths:
                            if appimage_utils.remove_orphaned_integration(path):
                                removed_count += 1
                            else:
                                overall_success = False
                                
                        if overall_success:
                            QMessageBox.information(self, translator.get_text("Cleanup Complete"), translator.get_text("Removed {count} selected orphaned integration file(s).").format(count=removed_count))
                        else:
                            QMessageBox.warning(self, translator.get_text("Cleanup Issue"), translator.get_text("Could not remove all selected orphaned files. Removed {count}. Check logs.").format(count=removed_count))
                        # Refresh desktop database implicitly done by remove_orphaned_integration
            else:
                logger.info("No potential orphaned integration files found.")
                QMessageBox.information(self, translator.get_text("Scan Complete"), translator.get_text("No orphaned integration files (.desktop) found."))
        except Exception as e:
            logger.error(f"Error during orphaned integration scan: {e}", exc_info=True)
            QMessageBox.critical(self, translator.get_text("Error"), translator.get_text("An error occurred while scanning for orphaned files.") + f"\n{e}")

# --- Leftover Files Dialog ---

class LeftoverDialog(QDialog):
    """Dialog to show potential leftover files and allow user to select for deletion."""
    def __init__(self, leftover_paths, parent=None):
        super().__init__(parent)
        self.setWindowTitle(translator.get_text("Potential Leftover Files Found"))
        self.setMinimumWidth(500)

        layout = QVBoxLayout(self)

        info_label = QLabel(translator.get_text(
            "The following files/directories might be leftovers from the uninstalled application. "
            "Please review carefully and select the ones you want to remove:"
        ))
        info_label.setWordWrap(True)
        layout.addWidget(info_label)

        self.list_widget = QListWidget()
        self.list_widget.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection) # Prevent blue selection highlight

        for path in leftover_paths:
            item = QListWidgetItem(path)
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            item.setCheckState(Qt.CheckState.Unchecked) # Default to unchecked
            self.list_widget.addItem(item)

        layout.addWidget(self.list_widget)

        # Select All / Deselect All Buttons
        button_layout = QHBoxLayout()
        select_all_button = QPushButton(translator.get_text("Select All"))
        deselect_all_button = QPushButton(translator.get_text("Deselect All"))
        button_layout.addWidget(select_all_button)
        button_layout.addWidget(deselect_all_button)
        button_layout.addStretch()
        layout.addLayout(button_layout)

        # Standard OK/Cancel buttons
        button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        layout.addWidget(button_box)

        # Connect signals
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        select_all_button.clicked.connect(self.select_all)
        deselect_all_button.clicked.connect(self.deselect_all)

    def select_all(self):
        for i in range(self.list_widget.count()):
            self.list_widget.item(i).setCheckState(Qt.CheckState.Checked)

    def deselect_all(self):
        for i in range(self.list_widget.count()):
            self.list_widget.item(i).setCheckState(Qt.CheckState.Unchecked)

    def get_selected_paths(self):
        """Returns a list of paths corresponding to checked items."""
        selected_paths = []
        for i in range(self.list_widget.count()):
            item = self.list_widget.item(i)
            if item.checkState() == Qt.CheckState.Checked:
                selected_paths.append(item.text())
        return selected_paths

# --- Orphaned Installations Dialog ---

class LeftoverInstallDialog(QDialog):
    """Dialog to show leftover/untracked installation directories and allow user to select for deletion."""
    def __init__(self, leftover_installs, parent=None):
        super().__init__(parent)
        self.setWindowTitle(translator.get_text("Leftover Installations Found"))
        self.setMinimumWidth(600)
        self.leftover_installs = leftover_installs

        layout = QVBoxLayout(self)

        info_label = QLabel(translator.get_text(
            "The following directories appear to be AppImage Manager installations but are not tracked in the database. "
            "They might be old remnants or from a cleared database. "
            "Marked items (.aim_managed file found) are almost certainly leftovers. Unmarked items are likely remnants but require more caution. "
            "Select the ones you want to permanently remove:"
        ))
        info_label.setWordWrap(True)
        layout.addWidget(info_label)

        self.list_widget = QListWidget()
        self.list_widget.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection)

        for item_info in self.leftover_installs:
            type_indicator = "(Marked)" if item_info['type'] == 'marked_leftover' else "(Unmarked)"
            display_text = f"{item_info['guessed_name']} {type_indicator} (Path: {item_info['path']})"
            item = QListWidgetItem(display_text)
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            item.setCheckState(Qt.CheckState.Unchecked)
            item.setData(Qt.ItemDataRole.UserRole, item_info['path'])
            self.list_widget.addItem(item)

        layout.addWidget(self.list_widget)

        button_layout = QHBoxLayout()
        select_all_button = QPushButton(translator.get_text("Select All"))
        deselect_all_button = QPushButton(translator.get_text("Deselect All"))
        button_layout.addWidget(select_all_button)
        button_layout.addWidget(deselect_all_button)
        button_layout.addStretch()
        layout.addLayout(button_layout)

        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Cancel | QDialogButtonBox.StandardButton.Reset
        )
        remove_button = button_box.addButton(translator.get_text("Remove Selected Leftovers"), QDialogButtonBox.ButtonRole.AcceptRole)
        layout.addWidget(button_box)

        button_box.rejected.connect(self.reject)
        remove_button.clicked.connect(self.accept)
        select_all_button.clicked.connect(self.select_all)
        deselect_all_button.clicked.connect(self.deselect_all)

    def select_all(self):
        for i in range(self.list_widget.count()):
            self.list_widget.item(i).setCheckState(Qt.CheckState.Checked)

    def deselect_all(self):
        for i in range(self.list_widget.count()):
            self.list_widget.item(i).setCheckState(Qt.CheckState.Unchecked)

    def get_selected_paths(self):
        """Returns a list of paths corresponding to checked items."""
        selected_paths = []
        for i in range(self.list_widget.count()):
            item = self.list_widget.item(i)
            if item.checkState() == Qt.CheckState.Checked:
                selected_paths.append(item.data(Qt.ItemDataRole.UserRole))
        return selected_paths

# --- Leftover Selection Dialog ---
class LeftoverSelectionDialog(QDialog):
    def __init__(self, leftovers, parent=None):
        super().__init__(parent)
        self.setWindowTitle(translator.get_text("Select Leftovers to Remove"))
        self.setMinimumWidth(500)

        layout = QVBoxLayout(self)

        label_text = translator.get_text("Select the items you are sure are leftovers and should be removed:")
        layout.addWidget(QLabel(label_text))

        self.list_widget = QListWidget()
        self.list_widget.setSelectionMode(QAbstractItemView.ExtendedSelection) # Allow multiple selections
        for item in leftovers:
            # Display type (marked/unmarked install, config/cache, desktop)
            display_type = item.get('type', 'unknown')
            if 'path' in item and item['path'].endswith('.desktop'): display_type = 'integration' 
            
            list_item = QListWidgetItem(f"{item.get('guessed_name', 'Unknown Name')} ({display_type}) - {item['path']}")
            list_item.setData(Qt.UserRole, item['path']) # Store the full path
            self.list_widget.addItem(list_item)
            
        layout.addWidget(self.list_widget)

        # Buttons
        self.button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)
        layout.addWidget(self.button_box)

    def get_selected_paths(self):
        selected_paths = []
        for item in self.list_widget.selectedItems():
            selected_paths.append(item.data(Qt.UserRole))
        return selected_paths

# --- Logger Setup (Example - Adapt as needed) ---
import logging
logger = logging.getLogger(__name__)
if not logger.hasHandlers():
    # Add basic handler if none exist, prevents 'No handlers could be found' error
    handler = logging.StreamHandler()
    formatter = logging.Formatter('%(levelname)s: %(name)s: %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.setLevel(logging.DEBUG) # Set level to DEBUG to see all messages 