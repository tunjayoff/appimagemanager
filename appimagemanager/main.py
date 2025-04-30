#!/usr/bin/env python3
"""
AppImage Manager - Main Application
Install, manage and remove AppImage applications on Ubuntu 24.04.
"""

import sys
import os
import logging
import traceback
from PyQt6.QtWidgets import (QApplication, QMainWindow, QVBoxLayout, QHBoxLayout, 
                             QWidget, QLabel, QListWidget, QStackedWidget, 
                             QListWidgetItem, QMessageBox, QToolButton, QSizePolicy, QToolBar)
from PyQt6.QtGui import QIcon, QAction, QFont, QPixmap, QDrag, QDragEnterEvent, QDropEvent, QPainter, QColor
from PyQt6.QtCore import Qt, QSize, QUrl, QPropertyAnimation, QRect # QRect'i ekledim

# Import application modules
import config
import utils
from i18n import _, get_translator, set_language
# from main_window import MainWindow  # Import the new PyQt5 main window # Remove old import

# Import page widgets
from install_page import InstallPage # ADD THIS LINE
from manage_page import ManagePage # ADD THIS LINE
from settings_page import SettingsPage # ADD THIS LINE
from about_page import AboutPage

# Local imports
import db_manager
import appimage_utils
import sudo_helper # Added
import i18n # Add this line

# Set up logging
logger = utils.setup_logging()
logger.info(f"===== {config.APP_NAME} v{config.APP_VERSION} Starting =====")

# Translate function placeholder (assuming i18n setup)
# _ = i18n.translate # REMOVE THIS LINE

# --- Constants for Sidebar ---
SIDEBAR_WIDTH = 200
SIDEBAR_ICON_SIZE = QSize(32, 32)

# Base stylesheet with variables
STYLESHEET_BASE = """
/* Variables will be substituted */
QWidget {
    background-color: %BACKGROUND_COLOR%;
    color: %TEXT_COLOR%;
    font-family: system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Roboto', 'Oxygen', 'Ubuntu', 'Cantarell', 'Fira Sans', 'Droid Sans', 'Helvetica Neue', sans-serif;
}

#sidebar {
    background-color: %SIDEBAR_BG%;
    border-right: 1px solid %BORDER_COLOR%;
}

#sidebar::item {
    padding: 10px;
    border-radius: 5px;
}

#sidebar::item:selected {
    background-color: %SELECTED_BG%;
    color: %SELECTED_TEXT%;
}

#sidebar::item:hover:!selected {
    background-color: %HOVER_BG%;
}

#contentArea {
    background-color: %BACKGROUND_COLOR%;
}

#contentArea QLabel {
    color: %TEXT_COLOR%;
    font-size: 14px;
}

QGroupBox {
    font-weight: bold;
    border: 1px solid %BORDER_COLOR%;
    border-radius: 5px;
    margin-top: 1ex;
    padding-top: 10px;
}

QGroupBox::title {
    subcontrol-origin: margin;
    padding: 0 3px;
}

QLineEdit {
    border: 1px solid %CONTROL_BORDER%;
    border-radius: 3px;
    padding: 4px;
    background-color: %INPUT_BG%;
    color: %INPUT_TEXT%;
}

QTableWidget {
    gridline-color: %BORDER_COLOR%;
    selection-background-color: %TABLE_SELECTION_BG%;
    selection-color: %TABLE_SELECTION_TEXT%;
}

QHeaderView::section {
    background-color: %HEADER_BG%;
    padding: 4px;
    border: 1px solid %BORDER_COLOR%;
    color: %HEADER_TEXT%;
}

QScrollBar:vertical {
    border: none;
    background: %SCROLLBAR_BG%;
    width: 10px;
    margin: 0px;
}

QScrollBar::handle:vertical {
    background: %SCROLLBAR_HANDLE%;
    min-height: 20px;
    border-radius: 5px;
}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    border: none;
    background: none;
    height: 0px;
}

QProgressBar {
    border: 1px solid %CONTROL_BORDER%;
    border-radius: 3px;
    text-align: center;
    background-color: %PROGRESS_BG%;
}

QProgressBar::chunk {
    background-color: %ACCENT_COLOR%; 
    width: 10px;
    margin: 0.5px;
}

QPushButton {
    padding: 8px 15px;
    background-color: %BUTTON_BG%; 
    color: %BUTTON_TEXT%;
    border: none;
    border-radius: 5px;
}

QPushButton:hover {
    background-color: %BUTTON_HOVER_BG%;
}

QPushButton:pressed {
    background-color: %BUTTON_PRESSED_BG%;
}

QRadioButton::indicator {
    width: 15px;
    height: 15px;
    border: 1px solid %CONTROL_BORDER%;
    border-radius: 8px;
    background-color: %RADIO_BG%;
}

QRadioButton::indicator:checked {
    background-color: %ACCENT_COLOR%;
    border: 4px solid %RADIO_BG%;
}
"""

# Light theme colors
LIGHT_THEME = {
    "BACKGROUND_COLOR": "#ffffff",
    "TEXT_COLOR": "#333333",
    "SIDEBAR_BG": "#f5f5f5",
    "BORDER_COLOR": "#dddddd",
    "SELECTED_BG": "#007AFF",
    "SELECTED_TEXT": "#ffffff",
    "HOVER_BG": "#e5e5e5",
    "CONTROL_BORDER": "#c0c0c0",
    "INPUT_BG": "#ffffff",
    "INPUT_TEXT": "#333333",
    "TABLE_SELECTION_BG": "#007AFF",
    "TABLE_SELECTION_TEXT": "#ffffff",
    "HEADER_BG": "#f0f0f0",
    "HEADER_TEXT": "#333333",
    "SCROLLBAR_BG": "#f0f0f0",
    "SCROLLBAR_HANDLE": "#c0c0c0",
    "PROGRESS_BG": "#e8e8e8",
    "ACCENT_COLOR": "#007AFF",
    "BUTTON_BG": "#007AFF",
    "BUTTON_TEXT": "#ffffff",
    "BUTTON_HOVER_BG": "#0056b3",
    "BUTTON_PRESSED_BG": "#003d80",
    "RADIO_BG": "#ffffff"
}

# Dark theme colors
DARK_THEME = {
    "BACKGROUND_COLOR": "#222222",
    "TEXT_COLOR": "#ffffff",
    "SIDEBAR_BG": "#333333",
    "BORDER_COLOR": "#444444",
    "SELECTED_BG": "#0066cc",
    "SELECTED_TEXT": "#ffffff",
    "HOVER_BG": "#3a3a3a",
    "CONTROL_BORDER": "#555555",
    "INPUT_BG": "#333333",
    "INPUT_TEXT": "#ffffff",
    "TABLE_SELECTION_BG": "#0066cc",
    "TABLE_SELECTION_TEXT": "#ffffff",
    "HEADER_BG": "#2c2c2c",
    "HEADER_TEXT": "#ffffff",
    "SCROLLBAR_BG": "#333333",
    "SCROLLBAR_HANDLE": "#666666",
    "PROGRESS_BG": "#333333",
    "ACCENT_COLOR": "#0099ff",
    "BUTTON_BG": "#0066cc",
    "BUTTON_TEXT": "#ffffff",
    "BUTTON_HOVER_BG": "#0077e6",
    "BUTTON_PRESSED_BG": "#004c99",
    "RADIO_BG": "#333333"
}

def get_theme_stylesheet(dark_mode=False):
    """Generate stylesheet with theme variable substitution"""
    theme = DARK_THEME if dark_mode else LIGHT_THEME
    stylesheet = STYLESHEET_BASE
    
    # Replace all variables with their values
    for key, value in theme.items():
        stylesheet = stylesheet.replace(f"%{key}%", value)
        
    return stylesheet

class MainWindow(QMainWindow):
    """Main application window."""

    def __init__(self):
        super().__init__()
        try:
            # Get translator instance
            self.translator = get_translator()
            
            self.setWindowTitle(_("AppImage Manager"))
            self.setGeometry(100, 100, 850, 600) # Adjusted initial size
            self.setWindowIcon(QIcon.fromTheme("application-x-appimage", QIcon(config.WINDOW_ICON)))
            
            # Enable drag and drop
            self.setAcceptDrops(True)
            
            # Initialize with theme preference from settings
            self.dark_mode = config.get_setting("dark_mode", False)
            logger.info(f"Using theme: {'Dark' if self.dark_mode else 'Light'}")
            
            # Apply the stylesheet
            self.update_theme()
            
            # --- Create toolbar for theme toggle ---
            self.setup_toolbar()

            # Setup main layout (Horizontal: Sidebar | Content)
            main_layout = QHBoxLayout()
            main_layout.setContentsMargins(0, 0, 0, 0) # No margins for the main layout
            main_layout.setSpacing(0) # No spacing between sidebar and content

            # --- Sidebar ---
            self.sidebar = QListWidget()
            self.sidebar.setObjectName("sidebar") # For QSS styling
            self.sidebar.setFixedWidth(SIDEBAR_WIDTH)
            self.sidebar.setIconSize(SIDEBAR_ICON_SIZE) # Set icon size for list items
            main_layout.addWidget(self.sidebar)

            # --- Content Area ---
            self.content_area = QStackedWidget()
            self.content_area.setObjectName("contentArea") # For QSS styling
            main_layout.addWidget(self.content_area)

            # --- Central Widget ---
            central_widget = QWidget()
            central_widget.setLayout(main_layout)
            self.setCentralWidget(central_widget)

            # --- Create Pages and Sidebar Items ---
            self.create_pages()
            self.populate_sidebar()

            # Connect sidebar selection changes to content area
            self.sidebar.currentItemChanged.connect(self.change_page)

            # --- Initialize other components ---
            self.create_menus()
            self.create_status_bar()

            # --- Load user language preference ---
            saved_language = config.get_setting("language", config.DEFAULT_LANGUAGE)
            self.translator.set_language(saved_language)
            logger.info(f"Using language: {saved_language}")
            # Update all UI texts to the selected language
            self.update_ui_texts()
            # --- Initial Checks ---
            self.perform_initial_checks()
            
            logger.info(_("Application started successfully."))
        except Exception as e:
            logger.error(f"Error during main window initialization: {e}", exc_info=True)
            QMessageBox.critical(self, _("Error"), 
                                 _("An error occurred during application initialization: {0}").format(str(e)))

    def setup_toolbar(self):
        """Setup the toolbar with theme toggle button"""
        toolbar = self.addToolBar("Theme Toggle")
        toolbar.setMovable(False)
        toolbar.setFloatable(False)
        toolbar.setContextMenuPolicy(Qt.ContextMenuPolicy.PreventContextMenu)
        
        # Set toolbar height and style
        toolbar.setMinimumHeight(48)
        toolbar.setStyleSheet("""
            QToolBar {
                spacing: 5px;
                padding: 3px;
                border-bottom: 1px solid rgba(150, 150, 150, 0.3);
                background-color: transparent;
            }
        """)
        
        # Add spacer to push theme toggle to the right
        spacer = QWidget()
        spacer.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        toolbar.addWidget(spacer)

        # Add theme toggle button - daha büyük ve çekici hale getir
        self.theme_toggle_button = QToolButton()
        
        # Use better theme icons - explicit paths to ensure visibility
        # Fallback mechanisms for different icon themes
        self.sun_icon = QIcon.fromTheme("weather-clear")
        self.moon_icon = QIcon.fromTheme("weather-clear-night")
        
        # If system icons not found, try alternative names
        if self.sun_icon.isNull():
            self.sun_icon = QIcon.fromTheme("preferences-desktop-display")
        if self.moon_icon.isNull():
            self.moon_icon = QIcon.fromTheme("weather-few-clouds-night")
            
        # If still null, use fallback character icons
        if self.sun_icon.isNull() or self.moon_icon.isNull():
            try:
                # Create custom icons with unicode characters
                sun_pixmap = QPixmap(32, 32)
                if not sun_pixmap.isNull():
                    sun_pixmap.fill(Qt.GlobalColor.transparent)
                    sun_painter = QPainter(sun_pixmap)
                    sun_painter.setPen(QColor(255, 140, 0))  # Turuncu
                    sun_painter.setFont(QFont("Arial", 24))
                    sun_painter.drawText(QRect(0, 0, 32, 32), Qt.AlignmentFlag.AlignCenter, "☀")
                    sun_painter.end()  # Ensure the painter is properly closed
                    self.sun_icon = QIcon(sun_pixmap)
                
                moon_pixmap = QPixmap(32, 32)
                if not moon_pixmap.isNull():
                    moon_pixmap.fill(Qt.GlobalColor.transparent)
                    moon_painter = QPainter(moon_pixmap)
                    moon_painter.setPen(QColor(200, 200, 255))  # Açık mavi
                    moon_painter.setFont(QFont("Arial", 24))
                    moon_painter.drawText(QRect(0, 0, 32, 32), Qt.AlignmentFlag.AlignCenter, "☽")
                    moon_painter.end()  # Ensure the painter is properly closed
                    self.moon_icon = QIcon(moon_pixmap)
            except Exception as e:
                logger.error(f"Error creating custom theme icons: {e}")
                # Fallback to text based icons if all else fails
                self.sun_icon = QIcon.fromTheme("application-x-executable")
                self.moon_icon = QIcon.fromTheme("application-x-executable")
        
        # Set up the initial icon based on theme
        # Final null icon check - assign a default if all fallbacks failed
        if self.sun_icon.isNull():
            self.sun_icon = QIcon()
        if self.moon_icon.isNull():
            self.moon_icon = QIcon()

        self.theme_toggle_button.setIcon(self.moon_icon if self.dark_mode else self.sun_icon)
        
        # Make button bigger and more visible
        self.theme_toggle_button.setIconSize(QSize(32, 32))
        self.theme_toggle_button.setMinimumSize(QSize(44, 44))
        self.theme_toggle_button.setToolTip(self.translator.get_text("toggle_dark_mode"))
        self.theme_toggle_button.clicked.connect(self.toggle_theme)
        
        # Style button to be more visible
        self.theme_toggle_button.setStyleSheet("""
            QToolButton { 
                border: none;
                padding: 8px;
                background-color: transparent;
                border-radius: 22px;
            }
            QToolButton:hover { 
                background-color: rgba(128, 128, 128, 0.2);
            }
            QToolButton:pressed { 
                background-color: rgba(128, 128, 128, 0.3);
            }
        """)
        toolbar.addWidget(self.theme_toggle_button)
        
        # Add some padding after the button
        end_spacer = QWidget()
        end_spacer.setMinimumWidth(10)
        toolbar.addWidget(end_spacer)

    def create_pages(self):
        """Creates the placeholder pages for the QStackedWidget."""
        # Placeholder widgets for now
        # self.install_page = QWidget() # Remove old placeholder
        # install_layout = QVBoxLayout()
        # install_label = QLabel(_("Install Page Content (Placeholder)"))
        # install_label.setStyleSheet("color: black;") # Set text color explicitly
        # install_layout.addWidget(install_label)
        # self.install_page.setLayout(install_layout)
        self.install_page = InstallPage(self) # Use the new InstallPage widget
        
        # self.manage_page = QWidget() # Remove old placeholder
        # manage_layout = QVBoxLayout()
        # manage_label = QLabel(translator.get_text("Manage Page Content (Placeholder)"))
        # manage_label.setStyleSheet("color: black;") # Set text color explicitly
        # manage_layout.addWidget(manage_label)
        # self.manage_page.setLayout(manage_layout)
        self.manage_page = ManagePage(self) # Use the new ManagePage widget

        # self.settings_page = QWidget() # Remove old placeholder
        # settings_layout = QVBoxLayout()
        # settings_label = QLabel(translator.get_text("Settings Page Content (Placeholder)"))
        # settings_label.setStyleSheet("color: black;") # Set text color explicitly
        # settings_layout.addWidget(settings_label)
        # self.settings_page.setLayout(settings_layout)
        self.settings_page = SettingsPage(self) # Use the new SettingsPage widget
        self.about_page = AboutPage(self)

        # Add pages to the stacked widget
        self.content_area.addWidget(self.install_page)
        self.content_area.addWidget(self.manage_page)
        self.content_area.addWidget(self.settings_page)
        self.content_area.addWidget(self.about_page)

    def populate_sidebar(self):
        """Adds items to the sidebar."""
        items_data = [
            {"text": _("Install"), "icon": "document-new", "page_index": 0},
            {"text": _("Manage"), "icon": "preferences-system", "page_index": 1},
            {"text": _("Settings"), "icon": "preferences-desktop", "page_index": 2},
            {"text": _("About"), "icon": "help-about", "page_index": 3} # Add About item
        ]

        for item_data in items_data:
            list_item = QListWidgetItem(QIcon.fromTheme(item_data["icon"]), item_data["text"])
            # Store the page index in the item's data
            list_item.setData(Qt.ItemDataRole.UserRole, item_data["page_index"]) 
            self.sidebar.addItem(list_item)

        # Select the first item by default
        if self.sidebar.count() > 0:
            self.sidebar.setCurrentRow(0)

    def change_page(self, current_item, previous_item):
        """Switches the content area page based on sidebar selection."""
        if current_item:
            page_index = current_item.data(Qt.ItemDataRole.UserRole)
            if page_index is not None:
                self.content_area.setCurrentIndex(page_index)
                logger.debug(f"Switched to page index: {page_index}")

    def create_menus(self):
        """Creates the main menu bar."""
        menu_bar = self.menuBar()

        # --- File Menu ---
        file_menu = menu_bar.addMenu(_("&File"))

        install_action = QAction(QIcon.fromTheme("document-new"), _("&Install AppImage..."), self)
        install_action.setStatusTip(_("Install a new AppImage"))
        install_action.triggered.connect(self.select_install_page) # Go to install page
        file_menu.addAction(install_action)

        file_menu.addSeparator()

        exit_action = QAction(QIcon.fromTheme("application-exit"), _("E&xit"), self)
        exit_action.setStatusTip(_("Exit application"))
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        # --- View Menu ---
        view_menu = menu_bar.addMenu(self.translator.get_text("menu_view"))
        theme_action = QAction(self.translator.get_text("toggle_dark_mode"), self)
        theme_action.setStatusTip(self.translator.get_text("msg_theme_changed"))
        theme_action.triggered.connect(self.toggle_theme)
        view_menu.addAction(theme_action)

        # --- Edit Menu (Placeholder/Example) ---
        edit_menu = menu_bar.addMenu(_("&Edit"))
        settings_action = QAction(QIcon.fromTheme("preferences-desktop"), _("&Preferences"), self)
        settings_action.setStatusTip(_("Application settings"))
        settings_action.triggered.connect(self.select_settings_page) # Go to settings page
        edit_menu.addAction(settings_action)

        # --- Help Menu ---
        help_menu = menu_bar.addMenu(_("&Help"))
        about_action = QAction(QIcon.fromTheme("help-about"), _("&About"), self)
        about_action.setStatusTip(_("Show application information"))
        about_action.triggered.connect(self.select_about_page) # Go to about page
        help_menu.addAction(about_action)

    def create_status_bar(self):
        """Creates the status bar."""
        self.statusBar().showMessage(_("Ready"))

    def select_install_page(self):
        """Selects the Install item in the sidebar."""
        self.select_sidebar_item_by_index(0)

    def select_settings_page(self):
        """Selects the Settings item in the sidebar."""
        self.select_sidebar_item_by_index(2)

    def select_about_page(self):
        """Selects the About item in the sidebar."""
        self.select_sidebar_item_by_index(3)

    def select_sidebar_item_by_index(self, index):
        """Selects a sidebar item programmatically."""
        if 0 <= index < self.sidebar.count():
            self.sidebar.setCurrentRow(index)
            # change_page will be called automatically by the signal

    def perform_initial_checks(self):
        """Performs initial system checks on startup."""
        logger.info(_("Performing initial system checks..."))
        
        # Check directories - This should be handled by respective modules or setup_logging
        # utils.ensure_dirs_exist() # REMOVE THIS LINE
        
        # Check database by attempting to instantiate DBManager
        # The DBManager constructor handles ensuring the DB exists and is loadable.
        try:
            db = db_manager.DBManager()
            # Optionally, load apps here if needed immediately
            # all_apps = db.get_all_apps() 
            logger.info(_("Database check passed (DBManager instantiated)."))
        except Exception as e:
             # The error should have been logged by DBManager already
             self.show_critical_error(_("Database Initialization Failed"), 
                                        _("Could not initialize or load the application database. Check logs for details. Error: {}").format(e))
             # Consider exiting or disabling DB features
             return

        # Check system compatibility (optional display)
        compatibility = appimage_utils.check_system_compatibility()
        if not compatibility.get("libfuse_installed"):
             logger.warning(_("libFUSE package ({pkg}) might be missing. AppImage execution may fail.").format(pkg=config.LIBFUSE_PACKAGE))
             # Optionally show a non-critical warning to the user
             # QMessageBox.warning(self, _("Compatibility Warning"), 
             #                    _("libFUSE package ({pkg}) might be missing. This is often required to run AppImages.").format(pkg=config.LIBFUSE_PACKAGE))

        logger.info(_("Initial checks completed."))
        
    def show_critical_error(self, title, message):
        """Displays a critical error message box."""
        logger.critical(f"{title}: {message}")
        QMessageBox.critical(self, title, message)

    def closeEvent(self, event):
        """Handle the close event."""
        reply = QMessageBox.question(self, _("Confirm Exit"),
                                     _("Are you sure you want to exit AppImage Manager?"),
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                                     QMessageBox.StandardButton.No)

        if reply == QMessageBox.StandardButton.Yes:
            logger.info(_("Application closing."))
            event.accept()
        else:
            event.ignore()

    def dragEnterEvent(self, event: QDragEnterEvent):
        """Handle drag enter events - accept only files with .AppImage extension"""
        if event.mimeData().hasUrls():
            for url in event.mimeData().urls():
                if url.toLocalFile().lower().endswith(".appimage"):
                    event.acceptProposedAction()
                    return
        event.ignore()
        
    def dropEvent(self, event: QDropEvent):
        """Handle drop events - process AppImage files"""
        if event.mimeData().hasUrls():
            appimage_files = [url.toLocalFile() for url in event.mimeData().urls() 
                            if url.toLocalFile().lower().endswith(".appimage")]
            if appimage_files:
                # Switch to install page
                self.select_install_page()
                # Set the first dropped file in the install page
                self.install_page.set_file_path(appimage_files[0])
                # If multiple files were dropped, we only handle the first one for now
                if len(appimage_files) > 1:
                    self.statusBar().showMessage(_("Only the first AppImage file was loaded. Multiple file install not supported yet."))
                event.acceptProposedAction()
            else:
                event.ignore()
        else:
            event.ignore()

    def update_theme(self):
        """Update the application theme based on settings"""
        stylesheet = get_theme_stylesheet(self.dark_mode)
        self.setStyleSheet(stylesheet)
        
        # Also update toolbar style to match theme
        if hasattr(self, 'theme_toggle_button'):
            # Get the toolbar containing the theme toggle button
            for toolbar in self.findChildren(QToolBar):
                if self.theme_toggle_button in toolbar.findChildren(QToolButton):
                    if self.dark_mode:
                        toolbar.setStyleSheet("""
                            QToolBar {
                                spacing: 5px;
                                padding: 3px;
                                border-bottom: 1px solid rgba(100, 100, 100, 0.4);
                                background-color: transparent;
                            }
                        """)
                    else:
                        toolbar.setStyleSheet("""
                            QToolBar {
                                spacing: 5px;
                                padding: 3px;
                                border-bottom: 1px solid rgba(200, 200, 200, 0.7);
                                background-color: transparent;
                            }
                        """)
            
            if self.dark_mode:
                self.theme_toggle_button.setStyleSheet("""
                    QToolButton { 
                        border: none;
                        padding: 8px;
                        border-radius: 22px;
                        background-color: transparent;
                    }
                    QToolButton:hover { 
                        background-color: rgba(180, 180, 180, 0.3);
                    }
                    QToolButton:pressed { 
                        background-color: rgba(180, 180, 180, 0.4);
                    }
                """)
            else:
                self.theme_toggle_button.setStyleSheet("""
                    QToolButton { 
                        border: none;
                        padding: 8px;
                        border-radius: 22px;
                        background-color: transparent;
                    }
                    QToolButton:hover { 
                        background-color: rgba(100, 100, 100, 0.1);
                    }
                    QToolButton:pressed { 
                        background-color: rgba(100, 100, 100, 0.2);
                    }
                """)

    def toggle_theme(self):
        """Toggle between light and dark theme with animation"""
        self.dark_mode = not self.dark_mode
        config.set_setting("dark_mode", self.dark_mode)
        
        # Create animation for smoother transition
        self.fade_animation = QPropertyAnimation(self, b"windowOpacity")
        self.fade_animation.setDuration(150)  # milliseconds
        self.fade_animation.setStartValue(1.0)
        self.fade_animation.setEndValue(0.95)
        self.fade_animation.finished.connect(self._complete_theme_change)
        self.fade_animation.start()
        
        # Update the toggle button icon immediately for better feedback
        self.theme_toggle_button.setIcon(self.moon_icon if self.dark_mode else self.sun_icon)
        
        theme_name = "Dark" if self.dark_mode else "Light"
        self.statusBar().showMessage(self.translator.get_text("Theme switched to {theme_name}").format(theme_name=theme_name))

    def _complete_theme_change(self):
        """Complete the theme change after animation"""
        # Apply the new theme
        self.update_theme()
        
        # Fade back in
        self.fade_animation = QPropertyAnimation(self, b"windowOpacity")
        self.fade_animation.setDuration(100)
        self.fade_animation.setStartValue(0.95)
        self.fade_animation.setEndValue(1.0)
        self.fade_animation.start()

    def update_ui_texts(self):
        """Update all UI texts when language changes."""
        logger.info("Updating UI texts for language change...")
        
        # Update window title
        self.setWindowTitle(_("AppImage Manager"))
        
        # Update sidebar items
        sidebar_texts = [
            _("Install"),
            _("Manage"),
            _("Settings"),
            _("About")
        ]
        
        for i in range(self.sidebar.count()):
            item = self.sidebar.item(i)
            if item and i < len(sidebar_texts):
                item.setText(sidebar_texts[i])
        
        # Update theme toggle tooltip
        self.theme_toggle_button.setToolTip(self.translator.get_text("toggle_dark_mode"))
        
        # Update menu items
        menu_bar = self.menuBar()
        if menu_bar:
            actions = menu_bar.actions()
            menu_texts = [_("&File"), self.translator.get_text("menu_view"), _("&Edit"), _("&Help")]
            
            # Main menus
            for i, menu_text in enumerate(menu_texts):
                if i < len(actions):
                    actions[i].setText(menu_text)
            
            # File menu actions
            if len(actions) > 0:
                file_menu = actions[0].menu()
                if file_menu:
                    file_actions = file_menu.actions()
                    file_texts = [
                        (_("&Install AppImage..."), _("Install a new AppImage")),
                        (None, None),  # Separator
                        (_("E&xit"), _("Exit application"))
                    ]
                    
                    for i, (text, tip) in enumerate(file_texts):
                        if i < len(file_actions):
                            action = file_actions[i]
                            if text:  # Not a separator
                                action.setText(text)
                                action.setStatusTip(tip)
            
            # View menu
            if len(actions) > 1:
                view_menu = actions[1].menu()
                if view_menu and view_menu.actions():
                    view_actions = view_menu.actions()
                    if len(view_actions) > 0:
                        view_actions[0].setText(self.translator.get_text("toggle_dark_mode"))
                        view_actions[0].setStatusTip(self.translator.get_text("msg_theme_changed"))
            
            # Edit menu
            if len(actions) > 2:
                edit_menu = actions[2].menu()
                if edit_menu and edit_menu.actions():
                    edit_actions = edit_menu.actions()
                    if len(edit_actions) > 0:
                        edit_actions[0].setText(_("&Preferences"))
                        edit_actions[0].setStatusTip(_("Application settings"))
            
            # Help menu
            if len(actions) > 3:
                help_menu = actions[3].menu()
                if help_menu and help_menu.actions():
                    help_actions = help_menu.actions()
                    if len(help_actions) > 0:
                        help_actions[0].setText(_("&About"))
                        help_actions[0].setStatusTip(_("Show application information"))
        
        # Update status bar
        self.statusBar().showMessage(_("Ready"))
        
        # Force update the content pages
        if hasattr(self, 'install_page') and hasattr(self.install_page, 'retranslateUi'):
            self.install_page.retranslateUi()
        
        if hasattr(self, 'manage_page') and hasattr(self.manage_page, 'retranslateUi'):
            self.manage_page.retranslateUi()
        
        if hasattr(self, 'settings_page') and hasattr(self.settings_page, 'retranslateUi'):
            self.settings_page.retranslateUi()
        
        # Update about page texts
        if hasattr(self, 'about_page') and hasattr(self.about_page, 'retranslateUi'):
            self.about_page.retranslateUi()
        
        logger.info("UI texts updated for new language")

def main():
    """Main entry point for the application."""
    # Initialize the PyQt6 application
    try:
        # Ensure essential directories exist before logging might fully initialize
        # utils.ensure_dirs_exist([config.CONFIG_DIR, config.LOG_DIR]) # REMOVE THIS LINE
        
        # Initialize logging AFTER ensuring directories
        logger = utils.setup_logging()
        logger.info(f"===== {config.APP_NAME} v{config.APP_VERSION} Starting =====")

        # Initialize translator
        translator = get_translator()
        saved_language = config.get_setting("language", config.DEFAULT_LANGUAGE)
        translator.set_language(saved_language)
        logger.info(f"Application language set to: {saved_language}")
        
        app = QApplication(sys.argv)
        
        # Set application details (optional but good practice)
        app.setApplicationName(config.APP_NAME)
        app.setApplicationVersion(config.APP_VERSION)
        app.setOrganizationName("YourOrg") # Or remove if not applicable
        
        # Create and show the main window
        main_window = MainWindow()
        main_window.show()
        
        # Start the Qt event loop
        sys.exit(app.exec())
        
    except Exception as e:
        logger.error(f"Critical error during application execution: {e}")
        logger.error(traceback.format_exc())
        # Using print here as we don't have a GUI messagebox yet
        print(
            f"{_('error_critical')}: {e}\n\n"
            f"For more details, check the log file: {config.LOG_PATH}"
        )
        sys.exit(1)

if __name__ == "__main__":
    main() 