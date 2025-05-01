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
from PyQt6.QtCore import Qt, QTimer, QSize
import os
import shutil # Import shutil for rmtree
import subprocess # For running applications

from .. import config
from ..i18n import get_translator
from ..db_manager import DBManager # To interact with the database
from .. import sudo_helper # ADD THIS IMPORT
from .. import appimage_utils # Import appimage_utils for leftover functions
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
        self.uninstall_button = QPushButton(QIcon.fromTheme("edit-delete"), translator.get_text("Uninstall Selected"))
        self.run_button = QPushButton(QIcon.fromTheme("media-playback-start"), translator.get_text("Run Application"))
        self.run_button.setEnabled(False) # Disable initially
        self.uninstall_button.setEnabled(False) # Disable initially
        
        toolbar_layout.addWidget(self.refresh_button)
        toolbar_layout.addWidget(self.scan_leftovers_button)
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
                install_path = app_data.get("app_install_dir")
                if not install_path or not os.path.exists(install_path):
                    is_missing = True
                    logger.warning(f"Installation path not found for app '{app_data.get('name')}': {install_path}")

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
                path_item = QTableWidgetItem(app_data.get("app_install_dir", translator.get_text("N/A")))
                self.app_table.setItem(row, 3, path_item)

                # --- Status --- 
                status_text = translator.get_text("OK") if not is_missing else translator.get_text("Missing")
                status_item = QTableWidgetItem(status_text)
                self.app_table.setItem(row, 4, status_item)

                # Store the App ID in the first column's item data for later retrieval
                # Using Qt.ItemDataRole.UserRole for custom data storage
                name_item.setData(Qt.ItemDataRole.UserRole, app_data.get("id"))
                # Store the missing status as well
                name_item.setData(Qt.ItemDataRole.UserRole + 1, is_missing)
                # Store the executable path
                name_item.setData(Qt.ItemDataRole.UserRole + 2, app_data.get("executable_path"))
                # Log the ID being set for debugging
                logger.debug(f"Setting data for row {row}: AppID={app_data.get('id')}, Missing={is_missing}")

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
        selected_row = self.app_table.currentRow()
        if selected_row < 0:
            return
            
        name_item = self.app_table.item(selected_row, 1)
        if not name_item:
            return
            
        app_name = name_item.text()
        is_missing = name_item.data(Qt.ItemDataRole.UserRole + 1)
        executable_path = name_item.data(Qt.ItemDataRole.UserRole + 2)
        
        if is_missing:
            QMessageBox.information(self, 
                translator.get_text("Cannot Run"), 
                translator.get_text("This application is missing its files and cannot be run."))
            return
            
        if not executable_path or not os.path.exists(executable_path):
            logger.error(f"Cannot run '{app_name}': Executable path not found: {executable_path}")
            QMessageBox.warning(self,
                translator.get_text("Run Error"),
                translator.get_text("Could not find the executable for '{app_name}'.").format(app_name=app_name))
            return
            
        try:
            logger.info(f"Starting application: {executable_path}")
            self.status_label.setText(translator.get_text("Starting {app_name}...").format(app_name=app_name))
            
            # Use subprocess to start the application in the background
            subprocess.Popen([executable_path], 
                             stdout=subprocess.DEVNULL, 
                             stderr=subprocess.DEVNULL,
                             start_new_session=True)
            
            # Set a delayed status message reset
            QTimer.singleShot(3000, lambda: self.status_label.setText(translator.get_text("Ready")))
            
        except Exception as e:
            logger.error(f"Failed to start application '{app_name}': {e}")
            QMessageBox.critical(self,
                translator.get_text("Run Error"),
                translator.get_text("Failed to start '{app_name}': {error}").format(app_name=app_name, error=str(e)))

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

        app_id = name_item.data(Qt.ItemDataRole.UserRole)
        is_missing = name_item.data(Qt.ItemDataRole.UserRole + 1)
        app_name = name_item.text() # Get app name for messages

        # Handle case where App ID might be missing (None)
        if not app_id and not is_missing:
            # This is an unexpected state: no ID but files are supposedly present?
            logger.error(f"Corrupted entry for '{app_name}': Missing ID but files reported as present.")
            QMessageBox.critical(self, translator.get_text("Data Error"), 
                                 translator.get_text("The database entry for '{app_name}' is inconsistent (missing ID). Cannot proceed with uninstall.").format(app_name=app_name))
            return
        # If ID is missing BUT files are also missing, we can offer to remove the DB entry.

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
            app_info = db.get_app(app_id)
            
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
                uninstaller = appimage_utils.AppImageUninstaller(app_info) # Use the uninstaller class
                
                if not is_missing:
                    logger.info("Attempting to remove application files and symlinks...")
                    if uninstaller.requires_root:
                        commands = uninstaller.get_uninstall_commands()
                        if commands:
                             logger.debug(f"Executing uninstall commands with sudo: {commands}")
                             # Make sure sudo_helper is imported and works
                             try:
                                 sudo_success, output = sudo_helper.execute_commands_with_sudo(commands)
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
                        if uninstaller.uninstall(): # Call the direct uninstall method
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