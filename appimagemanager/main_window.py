"""
AppImage Manager - PyQt5 Main Window
"""

import logging
import os
import traceback
import subprocess
import webbrowser

from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QTabWidget, QLabel, QApplication, 
    QStatusBar, QMenuBar, QAction, QMessageBox, QDialog, QLineEdit, QButtonGroup, 
    QGroupBox, QFormLayout, QTextEdit, QPushButton, QFileDialog, QDialogButtonBox, 
    QRadioButton, QHBoxLayout, QVBoxLayout, QActionGroup, QTreeView, QComboBox, QSplitter, 
    QFrame, QHeaderView, QStyledItemDelegate, QStyle, QStyleOptionViewItem, QListView, QMenu
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QSize, QSortFilterProxyModel, QItemSelectionModel, QTimer, QRect, QPoint
from PyQt5.QtGui import QIcon, QStandardItemModel, QStandardItem, QPixmap, QPainter, QColor, QPalette, QFont

import config
from i18n import _, get_translator
from db_manager import DBManager
from appimage_utils import check_system_compatibility, AppImageInstaller, AppImageUninstaller
import sudo_helper # Import sudo helper

logger = logging.getLogger(__name__)

# --- Worker Thread for background tasks ---
class Worker(QThread):
    """Generic worker thread for running tasks in the background."""
    finished = pyqtSignal(object)  # Emits result upon completion
    error = pyqtSignal(str)       # Emits error message on failure
    progress = pyqtSignal(str)    # Emits progress messages

    def __init__(self, function, *args, **kwargs):
        super().__init__()
        self.function = function
        self.args = args
        self.kwargs = kwargs

    def run(self):
        try:
            result = self.function(*self.args, **self.kwargs)
            self.finished.emit(result)
        except Exception as e:
            logger.error(f"Error in worker thread: {e}")
            logger.error(traceback.format_exc())
            self.error.emit(str(e))

# --- Custom Password Dialog (PyQt) ---
class PasswordDialog(QDialog):
    """Custom dialog for securely requesting a password using PyQt5."""
    def __init__(self, parent=None, title="Authentication Required", prompt="Password:"):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setModal(True)

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel(prompt))
        self.password_entry = QLineEdit()
        self.password_entry.setEchoMode(QLineEdit.Password)
        layout.addWidget(self.password_entry)

        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)

        self.password_entry.setFocus()

    def get_password(self):
        """Get the entered password."""
        return self.password_entry.text()

# --- Custom Delegate for App List Item --- 
class AppItemDelegate(QStyledItemDelegate):
    """Custom delegate to draw app items with icon, name, and description."""
    def paint(self, painter, option, index):
        if not index.isValid():
            return

        # Get data from model
        app_data = index.data(Qt.UserRole) # Our custom data role
        if not app_data:
            super().paint(painter, option, index)
            return
            
        app_name = app_data.get("name", "Unknown")
        app_desc = app_data.get("description", "")
        icon_path = app_data.get("icon_path")
        
        # --- Layout --- 
        icon_size = 48
        padding = 10
        text_x_offset = icon_size + 2 * padding
        name_font = painter.font()
        name_font.setBold(True)
        name_font.setPointSize(name_font.pointSize() + 1)
        desc_font = painter.font()
        desc_font.setPointSize(desc_font.pointSize() - 1)
        
        painter.save()
        
        # --- Draw rounded rect background ---
        if option.state & QStyle.State_Selected:
            painter.fillRect(option.rect, option.palette.highlight())
            text_pen = option.palette.highlightedText().color()
            # Draw rounded selection rectangle
            painter.setPen(Qt.NoPen)
            painter.setBrush(option.palette.highlight())
            painter.drawRoundedRect(option.rect, 8, 8)
        else:
            # Draw subtle background for non-selected items
            painter.setPen(Qt.NoPen)
            bg_color = QColor(option.palette.alternateBase().color())
            bg_color.setAlpha(50)  # Subtle transparency
            painter.setBrush(bg_color)
            painter.drawRoundedRect(option.rect, 8, 8)
            text_pen = option.palette.text().color()

        painter.setPen(text_pen)

        # --- Icon --- 
        icon_rect = option.rect.adjusted(padding, padding, -option.rect.width() + icon_size + padding, -option.rect.height() + icon_size + padding)
        pixmap = QPixmap(icon_path).scaled(icon_size, icon_size, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        if pixmap.isNull(): # Fallback icon
            pixmap = QPixmap(":/icons/app_default.png").scaled(icon_size, icon_size, Qt.KeepAspectRatio, Qt.SmoothTransformation) # Assuming fallback in resources
        painter.drawPixmap(icon_rect.topLeft(), pixmap)

        # --- Text (Name and Description) ---
        text_width = option.rect.width() - text_x_offset - padding
        
        # Name
        painter.setFont(name_font)
        name_rect = option.rect.adjusted(text_x_offset, padding, -padding, -padding)
        painter.drawText(name_rect, Qt.AlignLeft | Qt.AlignTop | Qt.TextWordWrap, app_name)
        
        # Description (below name)
        # Calculate where description starts based on name height
        name_bound_rect = painter.boundingRect(name_rect, Qt.AlignLeft | Qt.AlignTop | Qt.TextWordWrap, app_name)
        desc_y_offset = name_bound_rect.height() + padding // 2
        
        painter.setFont(desc_font)
        desc_rect = option.rect.adjusted(text_x_offset, padding + desc_y_offset, -padding, -padding)
        painter.drawText(desc_rect, Qt.AlignLeft | Qt.AlignTop | Qt.TextWordWrap, app_desc)
        
        painter.restore()

    def sizeHint(self, option, index):
        # Provide a size hint for each item (e.g., based on icon + text lines)
        return QSize(200, 80) # Increased height for better spacing

class LoadingSpinner(QWidget):
    """A spinner widget indicating loading/processing operation."""
    
    def __init__(self, parent=None, size=40, color=None):
        super().__init__(parent)
        self.size = size
        self.color = color if color else QColor(26, 115, 232)  # Default blue
        self.dark_mode_color = QColor(77, 171, 247)  # Lighter blue for dark mode
        self.angle = 0
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.rotate)
        self.setFixedSize(size, size)
        
        # Allow transparent background
        self.setAttribute(Qt.WA_TranslucentBackground)
        
    def start(self):
        """Start the spinner animation."""
        if not self.timer.isActive():
            self.timer.start(50)  # Update every 50ms
            self.show()
    
    def stop(self):
        """Stop the spinner animation."""
        self.timer.stop()
        self.hide()
    
    def rotate(self):
        """Rotate the spinner."""
        self.angle = (self.angle + 15) % 360
        self.update()
        
    def paintEvent(self, event):
        """Paint the spinner."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # Determine spinner color based on app theme
        if self.window().property("darkMode"):
            color = self.dark_mode_color
        else:
            color = self.color
        
        # Draw spinner
        pen = painter.pen()
        pen.setWidth(self.size // 10)  # Line width proportional to spinner size
        
        # Draw 12 lines with different opacity
        for i in range(12):
            rotation_angle = self.angle - i * 30
            opacity = 1.0 - (i * 0.08)  # Decrease opacity for trailing lines
            if opacity < 0.2:
                opacity = 0.2  # Minimum opacity
                
            pen.setColor(QColor(color.red(), color.green(), color.blue(), 
                              int(255 * opacity)))
            painter.setPen(pen)
            
            painter.save()
            painter.translate(self.size // 2, self.size // 2)  # Center of widget
            painter.rotate(rotation_angle)
            painter.drawLine(0, self.size // 4, 0, self.size // 2.2)  # Draw line
            painter.restore()

class MainWindow(QMainWindow):
    """Main application window using PyQt5."""
    
    # Signal for status bar updates from threads
    update_status_signal = pyqtSignal(str)
    
    # Additional signal for installation log messages
    log_message_signal = pyqtSignal(str)
    
    def __init__(self):
        super().__init__()
        
        self.db = DBManager()
        self.translator = get_translator()
        self.installed_apps = []
        self.sudo_password = None # Store sudo password if obtained
        self.current_worker = None # To manage background worker
        
        self._init_ui()
        self._check_system()
        self._load_installed_apps() # Load apps after UI is initialized
        
        # Force a retranslation of all UI elements to ensure correct language
        QTimer.singleShot(100, self._retranslate_ui)
        
        # Connect signals
        self.update_status_signal.connect(self.statusBar().showMessage)
        self.log_message_signal.connect(self._append_log_message)
        
    def _init_ui(self):
        """Initialize the main user interface."""
        self.setWindowTitle(f"{config.APP_NAME} v{config.APP_VERSION}")
        self.setGeometry(100, 100, config.WINDOW_WIDTH, config.WINDOW_HEIGHT)
        
        # Set window icon - create our own if none specified in config
        if config.WINDOW_ICON:
            self.setWindowIcon(QIcon(config.WINDOW_ICON))
        else:
            # Create a simple app icon
            icon_pixmap = QPixmap(64, 64)
            icon_pixmap.fill(Qt.transparent)
            painter = QPainter(icon_pixmap)
            painter.setRenderHint(QPainter.Antialiasing)
            painter.setBrush(QColor("#1a73e8"))
            painter.setPen(Qt.NoPen)
            painter.drawRoundedRect(4, 4, 56, 56, 10, 10)
            
            # Draw "A" text in the center
            painter.setPen(QColor("white"))
            font = QFont()
            font.setPointSize(30)
            font.setBold(True)
            painter.setFont(font)
            painter.drawText(icon_pixmap.rect(), Qt.AlignCenter, "A")
            painter.end()
            
            # Set the generated icon
            self.setWindowIcon(QIcon(icon_pixmap))
            
        # Create central widget and layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        
        # Add a welcome banner widget at the top
        self.welcome_widget = self._create_welcome_widget()
        main_layout.addWidget(self.welcome_widget)
        
        # Create Tab Widget
        self.tab_widget = QTabWidget()
        main_layout.addWidget(self.tab_widget)
        
        # Create tabs (placeholders for now)
        self.tab_installer = QWidget()
        self.tab_manager = QWidget()
        self.tab_about = QWidget()
        
        # Ensure the about tab has a valid empty layout ready
        logger.debug("Initializing about tab with empty layout")
        QVBoxLayout(self.tab_about)
        
        # Add the tabs to the tab widget
        self.tab_widget.addTab(self.tab_installer, _("tab_install"))
        self.tab_widget.addTab(self.tab_manager, _("tab_manage"))
        self.tab_widget.addTab(self.tab_about, _("tab_about"))

        # Connect tab changed signal to update tabs when selected
        self.tab_widget.currentChanged.connect(self._handle_tab_changed)
        
        # Populate tabs in a specific order
        logger.debug("Creating installer tab...")
        self._create_installer_tab()
        
        logger.debug("Creating manager tab...")
        self._create_manager_tab()
        
        logger.debug("Creating about tab...")
        # Force creation of about tab with proper content
        self._create_about_tab()  # Create the real about tab content
        
        # Create Menu Bar
        self._create_menu()
        
        # Create Status Bar
        self.setStatusBar(QStatusBar())
        self.statusBar().showMessage(_("status_ready"))
        
        # Apply modern stylesheet
        self._apply_stylesheet()

    def _apply_stylesheet(self):
        """Apply a modern stylesheet to the application."""
        qss = """
        /* Global Styles */
        QMainWindow, QDialog {
            background-color: #f5f5f7;
            color: #333333;
        }
        
        /* Dark mode support */
        QMainWindow[darkMode="true"], QDialog[darkMode="true"] {
            background-color: #2d2d30;
            color: #e0e0e0;
        }
        
        /* Tabs */
        QTabWidget::pane {
            border: 1px solid #cccccc;
            border-radius: 8px;
            background-color: white;
            padding: 5px;
        }
        
        QTabWidget::tab-bar {
            alignment: center;
        }
        
        QTabBar::tab {
            background-color: #e8e8e8;
            color: #555555;
            min-width: 120px;
            padding: 8px 16px;
            margin-right: 4px;
            border-top-left-radius: 6px;
            border-top-right-radius: 6px;
        }
        
        QTabBar::tab:selected {
            background-color: white;
            color: #1a73e8;
            font-weight: bold;
            border-bottom: 2px solid #1a73e8;
        }
        
        QTabBar::tab:hover:!selected {
            background-color: #d8d8d8;
        }
        
        /* GroupBox */
        QGroupBox {
            font-weight: bold;
            border: 1px solid #cccccc;
            border-radius: 8px;
            margin-top: 16px;
            padding-top: 16px;
            background-color: rgba(255, 255, 255, 0.7);
        }
        
        QGroupBox::title {
            subcontrol-origin: margin;
            subcontrol-position: top center;
            padding: 0 8px;
            color: #1a73e8;
        }
        
        /* Buttons */
        QPushButton {
            background-color: #1a73e8;
            color: white;
            border: none;
            border-radius: 6px;
            padding: 8px 16px;
            font-weight: bold;
            min-height: 28px;
        }
        
        QPushButton:hover {
            background-color: #1565c0;
        }
        
        QPushButton:pressed {
            background-color: #0d47a1;
        }
        
        QPushButton:disabled {
            background-color: #cccccc;
            color: #777777;
        }
        
        QPushButton#install_button {
            background-color: #34a853;
        }
        
        QPushButton#install_button:hover {
            background-color: #2d9248;
        }
        
        QPushButton#uninstall_button {
            background-color: #ea4335;
        }
        
        QPushButton#uninstall_button:hover {
            background-color: #d32f2f;
        }
        
        /* Input Fields */
        QLineEdit, QTextEdit {
            border: 1px solid #cccccc;
            border-radius: 6px;
            padding: 8px;
            background-color: white;
            selection-background-color: #1a73e8;
        }
        
        QLineEdit:focus, QTextEdit:focus {
            border: 2px solid #1a73e8;
        }
        
        /* Radio Buttons */
        QRadioButton {
            spacing: 8px;
            padding: 4px;
        }
        
        QRadioButton::indicator {
            width: 18px;
            height: 18px;
        }
        
        /* ComboBox */
        QComboBox {
            border: 1px solid #cccccc;
            border-radius: 6px;
            padding: 6px 12px;
            min-height: 28px;
            background-color: white;
        }
        
        QComboBox:focus {
            border: 2px solid #1a73e8;
        }
        
        QComboBox::drop-down {
            subcontrol-origin: padding;
            subcontrol-position: center right;
            width: 24px;
            border-left-width: 0px;
        }
        
        /* ListView */
        QListView {
            border: 1px solid #cccccc;
            border-radius: 8px;
            padding: 4px;
            background-color: white;
            alternate-background-color: #f9f9f9;
        }
        
        QListView::item {
            border-radius: 6px;
            padding: 4px;
            margin: 4px;
        }
        
        QListView::item:selected {
            background-color: #e8f0fe;
            color: #1a73e8;
            border: 1px solid #1a73e8;
        }
        
        QListView::item:hover:!selected {
            background-color: #f5f5f5;
        }
        
        /* Status Bar */
        QStatusBar {
            background-color: #f0f0f0;
            color: #555555;
            border-top: 1px solid #cccccc;
        }
        
        /* Menu Bar */
        QMenuBar {
            background-color: white;
            border-bottom: 1px solid #cccccc;
        }
        
        QMenuBar::item {
            padding: 6px 12px;
            background-color: transparent;
        }
        
        QMenuBar::item:selected {
            background-color: #e8f0fe;
            color: #1a73e8;
            border-radius: 4px;
        }
        
        QMenu {
            background-color: white;
            border: 1px solid #cccccc;
            border-radius: 6px;
            padding: 4px;
        }
        
        QMenu::item {
            padding: 6px 24px 6px 16px;
            border-radius: 4px;
            margin: 2px 4px;
        }
        
        QMenu::item:selected {
            background-color: #e8f0fe;
            color: #1a73e8;
        }
        
        /* Scrollbars */
        QScrollBar:vertical {
            border: none;
            background-color: #f0f0f0;
            width: 12px;
            margin: 0px;
            border-radius: 6px;
        }
        
        QScrollBar::handle:vertical {
            background-color: #cccccc;
            min-height: 20px;
            border-radius: 5px;
            margin: 2px;
        }
        
        QScrollBar::handle:vertical:hover {
            background-color: #aaaaaa;
        }
        
        QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
            height: 0px;
        }
        
        QScrollBar:horizontal {
            border: none;
            background-color: #f0f0f0;
            height: 12px;
            margin: 0px;
            border-radius: 6px;
        }
        
        QScrollBar::handle:horizontal {
            background-color: #cccccc;
            min-width: 20px;
            border-radius: 5px;
            margin: 2px;
        }
        
        QScrollBar::handle:horizontal:hover {
            background-color: #aaaaaa;
        }
        
        QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
            width: 0px;
        }
        
        /* Dark mode adjustments */
        QMainWindow[darkMode="true"] QTabWidget::pane {
            border: 1px solid #454545;
            background-color: #333333;
        }
        
        QMainWindow[darkMode="true"] QTabBar::tab {
            background-color: #383838;
            color: #cccccc;
        }
        
        QMainWindow[darkMode="true"] QTabBar::tab:selected {
            background-color: #454545;
            color: #4dabf7;
            border-bottom: 2px solid #4dabf7;
        }
        
        QMainWindow[darkMode="true"] QGroupBox {
            border: 1px solid #454545;
            background-color: rgba(51, 51, 51, 0.7);
        }
        
        QMainWindow[darkMode="true"] QGroupBox::title {
            color: #4dabf7;
        }
        
        QMainWindow[darkMode="true"] QLineEdit, 
        QMainWindow[darkMode="true"] QTextEdit,
        QMainWindow[darkMode="true"] QComboBox,
        QMainWindow[darkMode="true"] QListView {
            background-color: #383838;
            color: #e0e0e0;
            border: 1px solid #555555;
        }
        
        QMainWindow[darkMode="true"] QMenuBar,
        QMainWindow[darkMode="true"] QMenu {
            background-color: #333333;
            color: #e0e0e0;
            border-color: #454545;
        }
        
        QMainWindow[darkMode="true"] QMenuBar::item:selected,
        QMainWindow[darkMode="true"] QMenu::item:selected {
            background-color: #4a4a4a;
            color: #4dabf7;
        }
        
        QMainWindow[darkMode="true"] QStatusBar {
            background-color: #2d2d30;
            color: #cccccc;
            border-top: 1px solid #454545;
        }
        """
        self.setStyleSheet(qss)
        
        # Make UI elements use our defined styles
        self.install_button.setObjectName("install_button")
        self.uninstall_button.setObjectName("uninstall_button")

    def _create_menu(self):
        """Create the main menu bar."""
        menubar = self.menuBar()
        
        # File Menu
        file_menu = menubar.addMenu(_("menu_file"))
        
        refresh_action = QAction(_("menu_refresh"), self)
        refresh_action.triggered.connect(self._load_installed_apps)
        file_menu.addAction(refresh_action)
        
        file_menu.addSeparator()
        
        exit_action = QAction(_("menu_exit"), self)
        exit_action.setShortcut("Ctrl+Q")
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
        
        # Tools Menu
        tools_menu = menubar.addMenu(_("menu_tools"))
        settings_action = QAction(_("menu_settings"), self)
        # settings_action.triggered.connect(self._show_settings) # Implement later
        tools_menu.addAction(settings_action)

        # Language Menu
        language_menu = menubar.addMenu(_("menu_language"))
        lang_group = QActionGroup(self)
        lang_group.setExclusive(True)
        
        current_lang = self.translator.current_lang
        for lang_code, lang_name in self.translator.get_languages().items():
            action = QAction(lang_name, self, checkable=True)
            action.setData(lang_code)
            if lang_code == current_lang:
                action.setChecked(True)
            action.triggered.connect(self._change_language_triggered)
            language_menu.addAction(action)
            lang_group.addAction(action)
            
        # Help Menu
        help_menu = menubar.addMenu(_("menu_help"))
        about_action = QAction(_("menu_about"), self)
        about_action.triggered.connect(lambda: self.tab_widget.setCurrentWidget(self.tab_about))
        help_menu.addAction(about_action)
        
        # Add Documentation Link later

    def _create_installer_tab(self):
        """Create the UI for the Installer tab using PyQt5 widgets."""
        layout = QVBoxLayout(self.tab_installer)
        layout.setSpacing(15)

        # 1. File Selection GroupBox
        file_group = QGroupBox(_("Select AppImage"))
        file_layout = QHBoxLayout()
        file_group.setLayout(file_layout)
        
        self.select_file_button = QPushButton(_("btn_select_appimage"))
        self.select_file_button.clicked.connect(self._select_appimage_file)
        self.select_file_button.setToolTip(_("tip_select_appimage", "Browse your files to select an AppImage file to install"))
        self.appimage_path_edit = QLineEdit()
        self.appimage_path_edit.setPlaceholderText("Path to AppImage file...")
        self.appimage_path_edit.setReadOnly(True)
        self.appimage_path_edit.setToolTip(_("tip_appimage_path", "Shows the path to the selected AppImage file"))
        
        file_layout.addWidget(self.select_file_button)
        file_layout.addWidget(self.appimage_path_edit, 1) # Expand line edit
        layout.addWidget(file_group)

        # 2. Installation Mode GroupBox
        mode_group = QGroupBox(_("lbl_install_mode"))
        mode_layout = QVBoxLayout()
        mode_group.setLayout(mode_layout)
        
        self.install_mode_group = QButtonGroup(self) # Exclusive radio buttons
        self.system_radio = QRadioButton(_("install_mode_system"))
        self.user_radio = QRadioButton(_("install_mode_user"))
        self.custom_radio = QRadioButton(_("install_mode_custom"))
        
        # Add tooltips for installation modes
        self.system_radio.setToolTip(_("tip_install_system", "Install for all users (requires administrator privileges)"))
        self.user_radio.setToolTip(_("tip_install_user", "Install only for your user account (recommended)"))
        self.custom_radio.setToolTip(_("tip_install_custom", "Specify a custom installation location"))
        
        self.install_mode_group.addButton(self.system_radio, 1)
        self.install_mode_group.addButton(self.user_radio, 2)
        self.install_mode_group.addButton(self.custom_radio, 3)
        self.user_radio.setChecked(True) # Default to user mode
        
        # System install warning
        system_warning_label = QLabel(f"<font color='red'>{_('warning_system_install')}</font>")
        system_warning_label.setWordWrap(True)
        
        # Custom path selection
        custom_path_widget = QWidget()
        custom_path_layout = QHBoxLayout(custom_path_widget)
        custom_path_layout.setContentsMargins(20, 0, 0, 0) # Indent
        self.custom_path_edit = QLineEdit()
        self.custom_path_edit.setPlaceholderText("Installation directory...")
        self.custom_path_edit.setToolTip(_("tip_custom_path", "Specify the directory where you want to install the AppImage"))
        self.browse_button = QPushButton(_("btn_browse"))
        self.browse_button.clicked.connect(self._browse_custom_directory)
        self.browse_button.setToolTip(_("tip_browse", "Browse for a custom installation directory"))
        custom_path_layout.addWidget(QLabel(_("lbl_custom_path")))
        custom_path_layout.addWidget(self.custom_path_edit, 1)
        custom_path_layout.addWidget(self.browse_button)
        custom_path_widget.setEnabled(False) # Disabled by default
        self.custom_path_widget = custom_path_widget

        mode_layout.addWidget(self.system_radio)
        mode_layout.addWidget(system_warning_label)
        mode_layout.addWidget(self.user_radio)
        mode_layout.addWidget(self.custom_radio)
        mode_layout.addWidget(custom_path_widget)
        layout.addWidget(mode_group)
        
        # Connect radio button toggle to enable/disable custom path
        self.custom_radio.toggled.connect(custom_path_widget.setEnabled)

        # 3. Application Info GroupBox (Initially empty)
        info_group = QGroupBox(_("lbl_app_info"))
        info_layout = QFormLayout()
        info_group.setLayout(info_layout)
        self.app_name_label = QLabel("-")
        self.app_version_label = QLabel("-")
        self.app_desc_label = QLabel("-")
        info_layout.addRow(_("lbl_app_name"), self.app_name_label)
        info_layout.addRow(_("lbl_app_version"), self.app_version_label)
        info_layout.addRow(_("lbl_app_desc"), self.app_desc_label)
        layout.addWidget(info_group)

        # 4. Installation Log GroupBox
        log_group = QGroupBox(_("lbl_installation_log"))
        log_layout = QVBoxLayout()
        log_group.setLayout(log_layout)
        self.log_text_edit = QTextEdit()
        self.log_text_edit.setReadOnly(True)
        log_layout.addWidget(self.log_text_edit)
        layout.addWidget(log_group, 1) # Make log area expand vertically

        # 5. Buttons
        button_layout = QHBoxLayout()
        self.install_button = QPushButton(_("btn_install"))
        self.install_button.setStyleSheet("background-color: lightgreen")
        self.install_button.setEnabled(False) # Disabled until file selected
        self.install_button.clicked.connect(self._start_installation)
        self.install_button.setToolTip(_("tip_install", "Start the installation process for the selected AppImage"))
        
        self.cancel_button = QPushButton(_("btn_cancel"))
        self.cancel_button.clicked.connect(self._clear_installer_form)
        self.cancel_button.setToolTip(_("tip_cancel", "Clear the form and cancel the installation process"))
        
        button_layout.addStretch()
        button_layout.addWidget(self.cancel_button)
        button_layout.addWidget(self.install_button)
        layout.addLayout(button_layout)

    # --- Installer Tab Slots --- 

    def _select_appimage_file(self):
        """Slot for selecting an AppImage file."""
        filepath, _ = QFileDialog.getOpenFileName(
            self, 
            self.translator.get_text("Select AppImage File"),
            "",
            f"AppImage files (*.AppImage);;All files (*.*)"
        )
        if filepath:
            self.appimage_path_edit.setText(filepath)
            self._update_app_info_display(filepath)
            self.install_button.setEnabled(True)
            self.log_message_signal.emit(f"Selected: {os.path.basename(filepath)}")
            
            # Check executable status
            if not os.access(filepath, os.X_OK):
                reply = QMessageBox.question(self, "Not Executable", self.translator.get_text("msg_not_executable"),
                                           QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
                if reply == QMessageBox.Yes:
                    try:
                        os.chmod(filepath, 0o755)
                        self.log_message_signal.emit("Made file executable.")
                    except Exception as e:
                        self.log_message_signal.emit(f"Error setting executable: {e}")
                        QMessageBox.warning(self, "Error", f"Could not make file executable: {e}")

    def _browse_custom_directory(self):
        """Slot for browsing for a custom installation directory."""
        dir_path = QFileDialog.getExistingDirectory(
            self, 
            self.translator.get_text("Select Installation Directory")
        )
        if dir_path:
            self.custom_path_edit.setText(dir_path)

    def _update_app_info_display(self, filepath):
        """Update the App Info section based on the selected file."""
        # Basic info from filename (improve later by reading metadata)
        filename = os.path.basename(filepath)
        app_name = filename.replace(".AppImage", "")
        self.app_name_label.setText(app_name)
        self.app_version_label.setText(self.translator.get_text("Unknown"))
        self.app_desc_label.setText("-")
        # TODO: Add logic here later to extract real metadata from AppImage

    def _append_log_message(self, message):
        """Append a message to the log text area."""
        self.log_text_edit.append(message)

    def _clear_installer_form(self):
        """Clear all fields in the installer tab."""
        self.appimage_path_edit.clear()
        self.custom_path_edit.clear()
        self.user_radio.setChecked(True)
        self.custom_path_widget.setEnabled(False)
        self.app_name_label.setText("-")
        self.app_version_label.setText("-")
        self.app_desc_label.setText("-")
        self.log_text_edit.clear()
        self.install_button.setEnabled(False)
        self.statusBar().showMessage(_("status_ready"))

    def _get_selected_install_mode(self):
        """Get the selected installation mode ('system', 'user', 'custom')."""
        if self.system_radio.isChecked():
            return "system"
        elif self.custom_radio.isChecked():
            return "custom"
        else:
            return "user" # Default
            
    def _get_sudo_password_qt(self):
        """Get sudo password using a PyQt dialog if needed.
        
        Returns:
            bool: True if password obtained/valid or not needed, False otherwise.
        """
        install_mode = self._get_selected_install_mode()
        
        # Check if root is needed for the selected mode
        requires_root = config.INSTALL_DESTINATIONS.get(install_mode, {}).get("requires_root", False)
        
        if requires_root and not self.sudo_password:
            dialog = PasswordDialog(self, prompt=self.translator.get_text("msg_enter_password"))
            if dialog.exec_() == QDialog.Accepted:
                password = dialog.get_password()
                if not password:
                    QMessageBox.warning(self, "Error", "Password cannot be empty.")
                    return False
                
                # Verify password (using a simple sudo command)
                self.update_status_signal.emit("Verifying password...")
                QApplication.processEvents() # Update UI
                if sudo_helper.check_sudo_password(password):
                    self.sudo_password = password
                    self.update_status_signal.emit("Password verified.")
                    return True
                else:
                    QMessageBox.critical(self, "Authentication Failed", self.translator.get_text("msg_password_incorrect"))
                    self.sudo_password = None
                    self.update_status_signal.emit(_("status_ready"))
                    return False
            else:
                # User cancelled password dialog
                return False
                
        # Root not required or password already stored
        return True

    def _start_installation(self):
        """Start the installation process in a background thread."""
        appimage_path = self.appimage_path_edit.text()
        install_mode = self._get_selected_install_mode()
        custom_path = self.custom_path_edit.text() if install_mode == "custom" else None
        
        # --- Validations ---
        if not appimage_path or not os.path.exists(appimage_path):
            QMessageBox.critical(self, "Error", self.translator.get_text("msg_no_appimage"))
            return
            
        if install_mode == "custom" and not custom_path:
            QMessageBox.critical(self, "Error", self.translator.get_text("msg_missing_custom_path"))
            return
            
        # --- Get Sudo Password (if needed) ---
        if not self._get_sudo_password_qt():
            self.update_status_signal.emit("Installation cancelled (password).")
            return # Password incorrect or cancelled
            
        # --- Confirmation for System Install ---
        if install_mode == "system":
            app_name = os.path.basename(appimage_path)
            reply = QMessageBox.warning(self, 
                                      self.translator.get_text("warning_important"), 
                                      self.translator.get_text("warning_system_install_detail").format(app_name),
                                      QMessageBox.Yes | QMessageBox.No, 
                                      QMessageBox.No)
            if reply == QMessageBox.No:
                return
                
        # --- Disable UI elements --- 
        self.install_button.setEnabled(False)
        self.cancel_button.setEnabled(False)
        self.select_file_button.setEnabled(False)
        # Consider disabling mode selection too
        self.update_status_signal.emit(self.translator.get_text("status_installing"))
        self.log_message_signal.emit("-"*20)
        self.log_message_signal.emit(f"Starting installation for {os.path.basename(appimage_path)}...")
        
        # --- Show Loading Spinner ---
        self.loading_spinner = LoadingSpinner(self, size=40)
        self.loading_spinner.move(
            self.install_button.mapToGlobal(QPoint(0, 0)) - self.mapToGlobal(QPoint(0, 0)) -
            QPoint(self.loading_spinner.width() + 10, 
                  -self.install_button.height()//2 + self.loading_spinner.height()//2)
        )
        self.loading_spinner.start()
        
        # --- Run in Worker Thread ---
        self.current_worker = Worker(self._run_installation_logic, appimage_path, install_mode, custom_path)
        self.current_worker.finished.connect(self._finish_installation)
        self.current_worker.error.connect(self._handle_installation_error)
        self.current_worker.progress.connect(self.log_message_signal)
        self.current_worker.start()
        
    def _run_installation_logic(self, appimage_path, install_mode, custom_path):
        """The actual installation logic to be run in the worker thread using rsync."""
        installer = AppImageInstaller(appimage_path, install_mode, custom_path)
        
        # Emit progress updates via the worker's signal
        self.current_worker.progress.emit("Checking prerequisites...")
        prereqs = installer.check_prerequisites()
        
        if not prereqs.get("appimage_exists", False):
            raise Exception(self.translator.get_text("error_file_not_found"))
            
        if not prereqs.get("appimage_executable", False):
             self.current_worker.progress.emit("Warning: File might not be executable.")
             
        # --- Extraction ---
        self.current_worker.progress.emit(_("status_extracting")) # Can use _ here in module scope
        extract_success = installer.extract_appimage()
        if not extract_success:
             installer.cleanup()
             raise Exception(self.translator.get_text("msg_extract_failed"))
             
        # --- Installation / Copying using Rsync --- 
        self.current_worker.progress.emit(_("status_copying"))
        commands = installer.get_install_commands()
        if not commands:
             installer.cleanup()
             raise Exception("Failed to generate installation commands (rsync).")
             
        install_success = False
        if installer.requires_root:
            # --- Root Install --- 
            if not self.sudo_password:
                installer.cleanup()
                raise Exception("Sudo password required but not provided.")
                
            # Create helper script for sudo execution
            script_path = sudo_helper.create_root_helper_script(commands)
            if not script_path:
                installer.cleanup()
                raise Exception("Failed to create installation helper script.")
                
            self.current_worker.progress.emit("Running installation with root privileges (rsync)...")
            returncode, stdout, stderr = sudo_helper.run_with_sudo([script_path], self.sudo_password)
            
            # Clean up script
            try:
                os.remove(script_path)
            except Exception as rm_err:
                 logger.warning(f"Could not remove temp script {script_path}: {rm_err}")
                 
            if returncode == 0:
                install_success = True
            else:
                logger.error(f"Sudo installation script failed (rsync). Stderr: {stderr}")
                installer.cleanup()
                raise Exception(f"Installation failed (root command error): {stderr}")
        else:
            # --- Non-Root Install --- 
            self.current_worker.progress.emit("Running installation (rsync)...")
            try:
                # Execute commands directly using subprocess
                for cmd_str in commands:
                     # We need to parse the command string safely if it contains quotes
                     # Using shell=True is a security risk if paths aren't controlled.
                     # A safer approach is difficult without shlex if paths have spaces.
                     # Let's assume simple paths for now or use shell=True carefully.
                     # If paths are complex, get_install_commands should return lists.
                     # For now, let's try a basic split (may fail with complex paths)
                     cmd_list = cmd_str.split() 
                     # A better way for quoted paths requires shlex:
                     # import shlex
                     # cmd_list = shlex.split(cmd_str)
                     
                     # Check if mkdir -p needs to run (it probably should)
                     if cmd_list[0] == "mkdir" and cmd_list[1] == "-p":
                         os.makedirs(cmd_list[2].strip('"\''), exist_ok=True)
                         continue # mkdir done, move to next command (rsync)
                         
                     # Run the rsync command
                     result = subprocess.run(cmd_list, capture_output=True, text=True, check=False)
                     if result.returncode != 0:
                         logger.error(f"Non-root installation command failed: {cmd_str}")
                         logger.error(f"Stderr: {result.stderr}")
                         installer.cleanup()
                         raise Exception(f"Installation command failed: {result.stderr}")
                install_success = True
            except Exception as e:
                 logger.error(f"Non-root installation command execution failed: {e}")
                 installer.cleanup()
                 raise Exception(f"Installation command failed: {e}")
            
        if not install_success:
            # This part should ideally not be reached if exceptions are raised above
            installer.cleanup()
            raise Exception("File copying failed during installation (rsync).")
            
        # Get info and add to DB
        self.current_worker.progress.emit("Registering application...")
        install_info = installer.get_installation_info()
        # Database addition happens in the main thread via _finish_installation
            
        # Cleanup temp files
        installer.cleanup()
        
        return install_info # Return success result (app info dict)

    def _finish_installation(self, result):
        """Slot called when installation worker finishes successfully."""
        # Stop and remove the loading spinner
        if hasattr(self, 'loading_spinner'):
            self.loading_spinner.stop()
            self.loading_spinner.deleteLater()
        
        self.current_worker = None # Clear worker reference
        app_name = result.get("name", "Unknown")
        self.log_message_signal.emit(self.translator.get_text("msg_install_success").format(app_name))
        self.log_message_signal.emit("-"*20)
        
        # Re-enable UI
        self.install_button.setEnabled(True)
        self.cancel_button.setEnabled(True)
        self.select_file_button.setEnabled(True)
        
        self.update_status_signal.emit(self.translator.get_text("status_ready"))
        QMessageBox.information(self, "Installation Complete", self.translator.get_text("msg_install_success").format(app_name))
        
        # Reload installed apps list
        self._load_installed_apps()
        
        # Optionally clear form
        # self._clear_installer_form()

    def _handle_installation_error(self, error_message):
        """Slot called when installation worker encounters an error."""
        # Stop and remove the loading spinner
        if hasattr(self, 'loading_spinner'):
            self.loading_spinner.stop()
            self.loading_spinner.deleteLater()
            
        self.current_worker = None # Clear worker reference
        self.log_message_signal.emit(f"ERROR: {error_message}")
        self.log_message_signal.emit("Installation failed.")
        self.log_message_signal.emit("-"*20)
        
        # Re-enable UI
        self.install_button.setEnabled(True)
        self.cancel_button.setEnabled(True)
        self.select_file_button.setEnabled(True)
        
        self.update_status_signal.emit("Installation failed!")
        QMessageBox.critical(self, "Installation Failed", f"Error: {error_message}")

    def _create_manager_tab(self):
        """Create the UI for the Manager tab using PyQt5 widgets."""
        layout = QVBoxLayout(self.tab_manager)
        layout.setSpacing(10)

        # --- Toolbar (Search, Sort) --- 
        toolbar_widget = QWidget()
        toolbar_layout = QHBoxLayout(toolbar_widget)
        toolbar_layout.setContentsMargins(0, 0, 0, 0)

        toolbar_layout.addWidget(QLabel(self.translator.get_text("lbl_search")))
        self.search_entry = QLineEdit()
        self.search_entry.setPlaceholderText("Filter apps...")
        self.search_entry.textChanged.connect(self._filter_apps)
        self.search_entry.setToolTip(_("tip_search", "Filter the list of installed applications"))
        toolbar_layout.addWidget(self.search_entry)

        toolbar_layout.addSpacing(20)

        toolbar_layout.addWidget(QLabel(self.translator.get_text("lbl_sort_by")))
        self.sort_combo = QComboBox()
        self.sort_combo.addItems([
            self.translator.get_text("sort_name"), 
            self.translator.get_text("sort_date"), 
            # self.translator.get_text("sort_size") # TODO: Add size later if available
        ])
        self.sort_combo.currentIndexChanged.connect(self._sort_apps)
        self.sort_combo.setToolTip(_("tip_sort", "Sort the list of installed applications"))
        toolbar_layout.addWidget(self.sort_combo)
        toolbar_layout.addStretch()

        refresh_button = QPushButton(self.translator.get_text("btn_refresh"))
        refresh_button.setIcon(QIcon.fromTheme("view-refresh")) # Use theme icon
        refresh_button.clicked.connect(self._load_installed_apps)
        refresh_button.setToolTip(_("tip_refresh", "Refresh the list of installed applications"))
        toolbar_layout.addWidget(refresh_button)

        layout.addWidget(toolbar_widget)

        # --- App List View --- 
        self.app_list_view = QListView()
        self.app_list_view.setAlternatingRowColors(True)
        self.app_list_view.setUniformItemSizes(True) # Perf optimization if items similar size
        self.app_list_view.setViewMode(QListView.ListMode)
        self.app_list_view.setResizeMode(QListView.Adjust)
        self.app_list_view.setMovement(QListView.Static) # Items don't move
        self.app_list_view.setToolTip(_("tip_app_list", "List of installed AppImage applications"))
        
        # Create model and proxy model for filtering/sorting
        self.app_list_model = QStandardItemModel(self)
        self.proxy_model = QSortFilterProxyModel(self)
        self.proxy_model.setSourceModel(self.app_list_model)
        self.proxy_model.setFilterCaseSensitivity(Qt.CaseInsensitive)
        self.proxy_model.setFilterKeyColumn(-1) # Filter on all columns (using UserRole data)
        self.proxy_model.setSortRole(Qt.UserRole + 1) # Custom sort role

        self.app_list_view.setModel(self.proxy_model)
        self.app_list_view.setItemDelegate(AppItemDelegate(self)) # Use custom delegate
        
        # Handle selection changes
        self.app_list_view.selectionModel().selectionChanged.connect(self._update_manager_buttons)
        
        layout.addWidget(self.app_list_view, 1)

        # --- Action Buttons --- 
        action_layout = QHBoxLayout()
        self.open_button = QPushButton(self.translator.get_text("btn_open"))
        self.open_button.setIcon(QIcon.fromTheme("application-x-executable"))
        self.open_button.setEnabled(False)
        self.open_button.clicked.connect(self._open_selected_app)
        self.open_button.setToolTip(_("tip_open", "Launch the selected application"))
        
        self.uninstall_button = QPushButton(self.translator.get_text("btn_uninstall"))
        self.uninstall_button.setIcon(QIcon.fromTheme("edit-delete"))
        self.uninstall_button.setStyleSheet("color: red;") # Indicate danger
        self.uninstall_button.setEnabled(False)
        self.uninstall_button.clicked.connect(self._uninstall_selected_app)
        self.uninstall_button.setToolTip(_("tip_uninstall", "Uninstall the selected application"))

        action_layout.addStretch()
        action_layout.addWidget(self.open_button)
        action_layout.addWidget(self.uninstall_button)
        layout.addLayout(action_layout)

    # --- Manager Tab Slots --- 

    def _update_manager_list(self):
        """Populate the app list view with data from self.installed_apps."""
        self.app_list_model.clear()
        if not self.installed_apps:
            # Optionally show a placeholder item or label
            return
            
        for app_data in self.installed_apps:
            item = QStandardItem()
            item.setData(app_data, Qt.UserRole) # Store full data
            item.setData(app_data.get("name", "").lower(), Qt.UserRole + 1) # Data for sorting by name
            item.setData(app_data.get("install_date", ""), Qt.UserRole + 2) # Data for sorting by date
            # Add more roles for other sort keys if needed
            item.setEditable(False)
            self.app_list_model.appendRow(item)
            
        self._sort_apps() # Apply initial sort
        self.app_list_view.clearSelection()
        self._update_manager_buttons() # Disable buttons initially

    def _filter_apps(self, text):
        """Filter the list view based on the search text."""
        # We filter using UserRole which contains the app_data dict
        search_term = text.lower()
        
        def filter_accepts_row(row, parent):
            index = self.app_list_model.index(row, 0, parent)
            if not index.isValid():
                return False
            app_data = index.data(Qt.UserRole)
            if not app_data:
                return False
            
            name_match = search_term in app_data.get("name", "").lower()
            desc_match = search_term in app_data.get("description", "").lower()
            return name_match or desc_match

        self.proxy_model.setFilterRole(Qt.UserRole) # Tell proxy to use our custom role
        self.proxy_model.setFilterFixedString(text) # Use fixed string for simplicity, or regex
        # Custom filtering logic (more flexible but potentially slower):
        # self.proxy_model.setFilterRegExp(QRegExp(".*", Qt.CaseInsensitive, QRegExp.Wildcard)) # Reset filter
        # self.proxy_model.setFilterAcceptsRow(filter_accepts_row)
        # self.proxy_model.invalidateFilter()
        
    def _sort_apps(self):
        """Sort the list view based on the combo box selection."""
        sort_text = self.sort_combo.currentText()
        
        if sort_text == self.translator.get_text("sort_name"):
            self.proxy_model.setSortRole(Qt.UserRole + 1) # Sort by name role
            self.proxy_model.sort(0, Qt.AscendingOrder)
        elif sort_text == self.translator.get_text("sort_date"):
             self.proxy_model.setSortRole(Qt.UserRole + 2) # Sort by date role
             self.proxy_model.sort(0, Qt.DescendingOrder)
        # Add sorting by size later if needed
        
    def _get_selected_app_data(self):
        """Get the data dict for the currently selected app in the list view."""
        selected_indexes = self.app_list_view.selectedIndexes()
        if not selected_indexes:
            return None
        
        proxy_index = selected_indexes[0]
        source_index = self.proxy_model.mapToSource(proxy_index)
        if source_index.isValid():
            return source_index.data(Qt.UserRole)
        return None

    def _update_manager_buttons(self):
        """Enable/disable Open and Uninstall buttons based on selection."""
        selected_app = self._get_selected_app_data()
        has_selection = selected_app is not None
        self.open_button.setEnabled(has_selection and bool(selected_app.get("executable_path")))
        self.uninstall_button.setEnabled(has_selection)

    def _open_selected_app(self):
        """Launch the selected application."""
        app_data = self._get_selected_app_data()
        if not app_data:
            return
            
        exe_path = app_data.get("executable_path")
        if exe_path and os.path.exists(exe_path):
            try:
                self.update_status_signal.emit(f"Launching {app_data.get('name', 'app')}...")
                subprocess.Popen([exe_path], start_new_session=True)
                # Reset status after a short delay
                QTimer.singleShot(2000, lambda: self.update_status_signal.emit(self.translator.get_text("status_ready")))
            except Exception as e:
                logger.error(f"Error launching application {exe_path}: {e}")
                QMessageBox.critical(self, "Launch Error", f"Failed to launch application: {e}")
                self.update_status_signal.emit("Launch failed!")
        else:
            QMessageBox.warning(self, "Launch Error", "Application executable not found or path is invalid.")
            self.update_status_signal.emit("Launch failed!")

    def _uninstall_selected_app(self):
        """Start the uninstallation process for the selected app."""
        app_data = self._get_selected_app_data()
        if not app_data:
            return
            
        app_name = app_data.get("name", "Unknown")
        reply = QMessageBox.question(self,
                                   "Confirm Uninstall",
                                   self.translator.get_text("msg_confirm_uninstall").format(app_name),
                                   QMessageBox.Yes | QMessageBox.No,
                                   QMessageBox.No)
                                   
        if reply == QMessageBox.No:
            return

        # --- Get Sudo Password (if needed for this specific app) ---
        uninstaller = AppImageUninstaller(app_data)
        requires_root = uninstaller.requires_root
        
        if requires_root and not self.sudo_password:
             # Ask for password specifically for this uninstall action
             dialog = PasswordDialog(self, prompt=f"Enter password to uninstall {app_name} (system app):")
             if dialog.exec_() == QDialog.Accepted:
                 password = dialog.get_password()
                 if not password or not sudo_helper.check_sudo_password(password):
                     QMessageBox.critical(self, "Authentication Failed", self.translator.get_text("msg_password_incorrect"))
                     return
                 # Use this password *just* for this operation, don't store in self.sudo_password yet
                 current_sudo_password = password
             else:
                 return # User cancelled
        elif requires_root:
             current_sudo_password = self.sudo_password # Use stored password
        else:
             current_sudo_password = None
        
        # --- Disable UI --- 
        self.uninstall_button.setEnabled(False)
        self.open_button.setEnabled(False)
        self.app_list_view.setEnabled(False) # Disable list during operation
        self.update_status_signal.emit(self.translator.get_text("status_uninstalling"))
        
        # --- Show Loading Spinner ---
        self.loading_spinner = LoadingSpinner(self, size=40, color=QColor(234, 67, 53))  # Red spinner for uninstall
        self.loading_spinner.move(
            self.uninstall_button.mapToGlobal(QPoint(0, 0)) - self.mapToGlobal(QPoint(0, 0)) -
            QPoint(self.loading_spinner.width() + 10, 
                  -self.uninstall_button.height()//2 + self.loading_spinner.height()//2)
        )
        self.loading_spinner.start()
        
        # --- Run in Worker Thread ---
        self.current_worker = Worker(self._run_uninstallation_logic, app_data, current_sudo_password)
        self.current_worker.finished.connect(self._finish_uninstallation)
        self.current_worker.error.connect(self._handle_uninstallation_error)
        # self.current_worker.progress.connect(...) # Add progress signal if needed
        self.current_worker.start()

    def _run_uninstallation_logic(self, app_data, sudo_password):
        """Actual uninstallation logic run in worker thread."""
        uninstaller = AppImageUninstaller(app_data)
        success = False
        
        if uninstaller.requires_root:
            if not sudo_password:
                raise Exception("Sudo password required but not provided for uninstall.")
            success = uninstaller.uninstall_with_sudo(sudo_password)
        else:
            success = uninstaller.uninstall()
            
        if success:
            # DO NOT remove from database here
            # db_success = self.db.remove_app(app_data.get("id")) # Moved to main thread
            # if not db_success:
            #     logger.warning(f"Failed to remove app {app_data.get('id')} from database after successful uninstall.")
            return app_data # Return app data on success
        else:
             raise Exception(f"Uninstallation process failed for {app_data.get('name', 'Unknown')}.")
             
    def _finish_uninstallation(self, uninstalled_app_data):
        """Slot called after successful uninstallation."""
        # Stop and remove the loading spinner
        if hasattr(self, 'loading_spinner'):
            self.loading_spinner.stop()
            self.loading_spinner.deleteLater()
            
        self.current_worker = None
        app_name = uninstalled_app_data.get("name", "Unknown")
        app_id = uninstalled_app_data.get("id")
        
        # --- Remove from database in Main Thread --- 
        db_success = False
        if app_id:
            db_success = self.db.remove_app(app_id)
            if not db_success:
                 logger.warning(f"Failed to remove app {app_id} ({app_name}) from database.")
                 # Show a warning to the user, maybe?
                 QMessageBox.warning(self, "Database Warning", f"App files for {app_name} were removed, but failed to update the database record.")
        else:
             logger.error(f"Could not remove app {app_name} from database: ID missing in returned data.")
             QMessageBox.critical(self, "Database Error", f"Could not remove app {app_name} from database: Missing ID.")
             
        # Re-enable UI
        self.app_list_view.setEnabled(True)
        # Buttons will be updated by selection change after reload
        
        self.update_status_signal.emit(self.translator.get_text("status_ready"))
        if db_success: # Only show full success if DB removal worked too
            QMessageBox.information(self, "Uninstall Complete", self.translator.get_text("msg_uninstall_success").format(app_name))
        
        # Reload app list to reflect removal
        self._load_installed_apps()

    def _handle_uninstallation_error(self, error_message):
        """Slot called if uninstallation fails."""
        # Stop and remove the loading spinner
        if hasattr(self, 'loading_spinner'):
            self.loading_spinner.stop()
            self.loading_spinner.deleteLater()
            
        self.current_worker = None
        
        # Re-enable UI
        self.app_list_view.setEnabled(True)
        self._update_manager_buttons() # Re-enable buttons based on current selection (if any)
        
        self.update_status_signal.emit("Uninstallation failed!")
        QMessageBox.critical(self, "Uninstallation Failed", f"Error: {error_message}")

    def _create_about_tab(self):
        """Create the UI for the About tab."""
        try:
            logger.debug("Creating about tab - start")
            
            # Remove any placeholder label if exists
            if self.tab_about.layout():
                logger.debug("Checking for placeholder text in existing layout")
                for i in range(self.tab_about.layout().count()):
                    item = self.tab_about.layout().itemAt(i)
                    if item and item.widget() and isinstance(item.widget(), QLabel):
                        text = item.widget().text()
                        if "placeholder" in text.lower():
                            logger.debug(f"Removing placeholder text: {text}")
                            item.widget().deleteLater()
            
            # First ensure any existing layout is cleared properly
            if self.tab_about.layout():
                logger.debug("Clearing existing about tab layout")
                try:
                    # Take all widgets from layout and delete them
                    while self.tab_about.layout().count():
                        item = self.tab_about.layout().takeAt(0)
                        if item.widget():
                            item.widget().deleteLater()
                    
                    # Delete the old layout itself
                    old_layout = self.tab_about.layout()
                    self.tab_about.setLayout(None)
                    old_layout.deleteLater()
                    logger.debug("Old layout cleared successfully")
                except Exception as e:
                    logger.error(f"Error clearing about tab layout: {e}")
            
            # Create new layout
            logger.debug("Creating new about tab layout")
            layout = QVBoxLayout(self.tab_about)
            layout.setSpacing(20)
            layout.setContentsMargins(30, 30, 30, 30)
            
            # App logo and title section
            logger.debug("Creating header widget")
            header_widget = QWidget()
            header_layout = QHBoxLayout(header_widget)
            
            # App logo
            logo_label = QLabel()
            logo_label.setObjectName("about_logo")  # Give it an ID for debugging
            logo_size = 96
            if config.WINDOW_ICON:
                logo_pixmap = QPixmap(config.WINDOW_ICON).scaled(
                    logo_size, logo_size, Qt.KeepAspectRatio, Qt.SmoothTransformation
                )
                logo_label.setPixmap(logo_pixmap)
            else:
                # Create a simple app icon
                logo_pixmap = QPixmap(logo_size, logo_size)
                logo_pixmap.fill(Qt.transparent)
                painter = QPainter(logo_pixmap)
                painter.setRenderHint(QPainter.Antialiasing)
                painter.setBrush(QColor("#1a73e8"))
                painter.setPen(Qt.NoPen)
                painter.drawRoundedRect(8, 8, logo_size-16, logo_size-16, 12, 12)
                
                # Draw "A" text in the center
                painter.setPen(QColor("white"))
                font = QFont()
                font.setPointSize(40)
                font.setBold(True)
                painter.setFont(font)
                painter.drawText(logo_pixmap.rect(), Qt.AlignCenter, "A")
                painter.end()
                logo_label.setPixmap(logo_pixmap)
                
            header_layout.addWidget(logo_label)
            
            # App title and version
            logger.debug("Creating title section")
            title_layout = QVBoxLayout()
            title_label = QLabel(f"<h1>{config.APP_NAME}</h1>")
            title_label.setObjectName("about_title")  # Give it an ID for debugging
            
            # Parse version into semantic components if it follows semver pattern
            version_parts = config.APP_VERSION.split('.')
            if len(version_parts) >= 3:
                major, minor, patch = version_parts[0], version_parts[1], version_parts[2]
                # Check if patch contains build info
                if '-' in patch:
                    patch_parts = patch.split('-')
                    patch = patch_parts[0]
                    build = '-' + '-'.join(patch_parts[1:])
                else:
                    build = ''
                
                version_text = f"<h3>v{major}.{minor}.{patch}<span style='font-size:80%;'>{build}</span></h3>"
            else:
                version_text = f"<h3>v{config.APP_VERSION}</h3>"
                
            version_label = QLabel(version_text)
            version_label.setObjectName("about_version")  # Give it an ID for debugging
            title_layout.addWidget(title_label)
            title_layout.addWidget(version_label)
            title_layout.setAlignment(Qt.AlignVCenter)
            header_layout.addLayout(title_layout, 1)
            
            layout.addWidget(header_widget)
            
            # Description
            logger.debug("Creating description section")
            desc_label = QLabel(_(
                "about_description", 
                "AppImage Manager helps you integrate AppImage applications with your Ubuntu system. "
                "It extracts the contents and creates system links rather than running AppImages as portable files."
            ))
            desc_label.setObjectName("about_description")  # Give it an ID for debugging
            desc_label.setWordWrap(True)
            desc_label.setAlignment(Qt.AlignJustify)
            layout.addWidget(desc_label)
            
            # Features
            logger.debug("Creating features section")
            features_group = QGroupBox(_("about_features", "Features"))
            features_group.setObjectName("about_features_group")  # Give it an ID for debugging
            features_layout = QVBoxLayout(features_group)
            
            features = [
                _("about_feature_extract", "• Extract AppImage contents for system integration"),
                _("about_feature_desktop", "• Create desktop entries and menu items"),
                _("about_feature_icon", "• Install application icons"),
                _("about_feature_manage", "• Easily manage installed AppImages"),
                _("about_feature_launch", "• Launch applications directly from the manager")
            ]
            
            for i, feature in enumerate(features):
                feature_label = QLabel(feature)
                feature_label.setObjectName(f"about_feature_{i}")  # Give it an ID for debugging
                features_layout.addWidget(feature_label)
            
            layout.addWidget(features_group)
            
            # Developer information
            logger.debug("Creating developer section")
            developer_group = QGroupBox(_("about_developer_info", "Developer Information"))
            developer_group.setObjectName("about_developer_group")  # Give it an ID for debugging
            developer_layout = QVBoxLayout(developer_group)
            
            developer_info = [
                f'<b>{_("about_developer_name", "Developer")}:</b> Tuncay Eşsiz',
                f'<b>{_("about_github_profile", "GitHub Profile")}:</b> <a href="https://github.com/tunjayoff">github.com/tunjayoff</a>',
                f'<b>{_("about_github_project", "GitHub Project")}:</b> <a href="https://github.com/tunjayoff/appimagemanager">github.com/tunjayoff/appimagemanager</a>',
                f'<b>{_("about_license", "License")}:</b> MIT',
            ]
            
            for i, info in enumerate(developer_info):
                info_label = QLabel(info)
                info_label.setObjectName(f"about_dev_info_{i}")  # Give it an ID for debugging
                info_label.setOpenExternalLinks(True)  # Allow clicking links
                developer_layout.addWidget(info_label)
            
            layout.addWidget(developer_group)
            
            # System info
            logger.debug("Creating system info section")
            system_group = QGroupBox(_("about_system_info", "System Information"))
            system_group.setObjectName("about_system_group")  # Give it an ID for debugging
            system_layout = QVBoxLayout(system_group)
            
            # Get system info
            system_checks = check_system_compatibility()
            distro_name = system_checks.get("distro_name", "Unknown")
            distro_version = system_checks.get("ubuntu_version", "Unknown")
            
            system_info = [
                f'<b>{_("about_os", "Operating System")}:</b> {distro_name} {distro_version}',
                f'<b>{_("about_python", "Python Version")}:</b> Python {subprocess.check_output(["python3", "--version"]).decode().strip().split()[1]}',
                f'<b>{_("about_qt", "Qt Version")}:</b> Qt {QApplication.instance().applicationVersion()}'
            ]
            
            for i, info in enumerate(system_info):
                info_label = QLabel(info)
                info_label.setObjectName(f"about_sys_info_{i}")  # Give it an ID for debugging
                system_layout.addWidget(info_label)
            
            layout.addWidget(system_group)
            
            # Add buttons for website, report issues, etc.
            logger.debug("Creating buttons section")
            button_layout = QHBoxLayout()
            button_layout.setSpacing(10)
            
            website_btn = QPushButton(_("about_website", "Website"))
            website_btn.setObjectName("about_website_btn")  # Give it an ID for debugging
            website_btn.clicked.connect(lambda: webbrowser.open("https://github.com/tunjayoff/appimagemanager"))
            
            report_btn = QPushButton(_("about_report_issue", "Report Issue"))
            report_btn.setObjectName("about_report_btn")  # Give it an ID for debugging
            report_btn.clicked.connect(lambda: webbrowser.open("https://github.com/tunjayoff/appimagemanager/issues"))
            
            button_layout.addStretch()
            button_layout.addWidget(website_btn)
            button_layout.addWidget(report_btn)
            button_layout.addStretch()
            
            layout.addLayout(button_layout)
            layout.addStretch()
            
            # Force layout update and repaint
            self.tab_about.updateGeometry()
            self.tab_about.update()
            
            logger.debug("About tab creation completed successfully")
            self._debug_tab_content(self.tab_about, "About (after creation)")
            
            return True
            
        except Exception as e:
            logger.error(f"Error creating about tab: {e}")
            logger.error(traceback.format_exc())
            
            # Add a simple message for debugging if the normal about tab fails
            if not self.tab_about.layout():
                error_layout = QVBoxLayout(self.tab_about)
            else:
                error_layout = self.tab_about.layout()
                # Clear any existing widgets
                while error_layout.count():
                    item = error_layout.takeAt(0)
                    if item.widget():
                        item.widget().deleteLater()
                
            # Create an error message that's clearly visible
            error_label = QLabel(f"<h3>Error loading About tab</h3><p>{str(e)}</p>")
            error_label.setWordWrap(True)
            error_label.setAlignment(Qt.AlignCenter)
            error_label.setStyleSheet("color: red;")
            error_layout.addWidget(error_label)
            
            return False

    def _check_system(self):
        """Check system compatibility and show warnings if needed."""
        system_checks = check_system_compatibility()
        warnings = []
        
        if not system_checks["is_ubuntu"]:
            warnings.append(
                "This application is primarily designed for Ubuntu. Compatibility with your system ({}) is not guaranteed.".format(
                    system_checks.get("distro_name", "Unknown")
                )
            )
        elif system_checks["ubuntu_version"] != config.SUPPORTED_UBUNTU_VERSION:
            warnings.append(
                self.translator.get_text("msg_not_ubuntu").format(
                    config.SUPPORTED_UBUNTU_VERSION, 
                    system_checks["ubuntu_version"] or "Unknown"
                )
            )
        
        if not system_checks["libfuse_installed"]:
            warnings.append(self.translator.get_text("msg_missing_libfuse").format(config.LIBFUSE_PACKAGE))

        if warnings:
            QMessageBox.warning(self, "System Compatibility Check", "\n".join(warnings))
            
    def _load_installed_apps(self):
        """Load installed applications from the database and update the UI."""
        try:
            self.installed_apps = self.db.get_all_apps()
            logger.info(f"Loaded {len(self.installed_apps)} installed applications")
            self.update_status_signal.emit(f"{self.translator.get_text('status_ready')} | {len(self.installed_apps)} apps installed")
            
            # Update the manager tab UI 
            self._update_manager_list() 
            
            # Update statistics in the welcome widget
            self._update_stats()
                
        except Exception as e:
            logger.error(f"Error loading installed applications: {e}")
            QMessageBox.critical(self, self.translator.get_text("error_db_access"), f"Failed to load apps: {e}")
            self.update_status_signal.emit(self.translator.get_text("error_db_access"))

    def _change_language_triggered(self):
        """Handle language change from the menu."""
        action = self.sender()
        if action and action.isChecked():
            lang_code = action.data()
            logger.info(f"Attempting to change language to {lang_code}")
            
            if self.translator.set_language(lang_code):
                logger.info(f"Language changed to {lang_code}")
                
                # Store current tab index
                current_tab = self.tab_widget.currentIndex()
                
                # Perform full UI translation update
                self._retranslate_ui()
                
                # Force repaint of all widgets
                for widget in self.findChildren(QWidget):
                    widget.update()
                
                # Switch back to the same tab to force refresh of content
                self.tab_widget.setCurrentIndex((current_tab + 1) % 3)  # Switch to next tab
                QApplication.processEvents()  # Process pending events
                self.tab_widget.setCurrentIndex(current_tab)  # Switch back
                
                # Notify user about the language change
                QMessageBox.information(
                    self,
                    _("Language Changed", "Language Changed"),
                    _("Language changed to {0}. Please restart the application for all changes to take full effect.", 
                      "Language changed to {0}. Please restart the application for all changes to take full effect.").format(
                        self.translator.get_languages()[lang_code]
                    )
                )
            else:
                logger.warning(f"Failed to set language to {lang_code}")
                
    def _retranslate_ui(self):
        """Update all UI text after language change."""
        # Update window title
        self.setWindowTitle(f"{config.APP_NAME} v{config.APP_VERSION}")
        
        # Update tab titles
        self.tab_widget.setTabText(0, _("tab_install", "Install"))
        self.tab_widget.setTabText(1, _("tab_manage", "Manage"))
        self.tab_widget.setTabText(2, _("tab_about", "About"))
        
        # Update status bar
        self.statusBar().showMessage(_("status_ready", "Ready"))
        
        # Update installer tab
        if hasattr(self, 'select_file_button'):
            self.select_file_button.setText(_("btn_select_appimage", "Select AppImage"))
            self.select_file_button.setToolTip(_("tip_select_appimage", "Browse your files to select an AppImage file to install"))
        if hasattr(self, 'appimage_path_edit'):
            self.appimage_path_edit.setToolTip(_("tip_appimage_path", "Shows the path to the selected AppImage file"))
        if hasattr(self, 'system_radio'):
            self.system_radio.setText(_("install_mode_system", "System-wide (all users)"))
            self.system_radio.setToolTip(_("tip_install_system", "Install for all users (requires administrator privileges)"))
        if hasattr(self, 'user_radio'):
            self.user_radio.setText(_("install_mode_user", "Current user only"))
            self.user_radio.setToolTip(_("tip_install_user", "Install only for your user account (recommended)"))
        if hasattr(self, 'custom_radio'):
            self.custom_radio.setText(_("install_mode_custom", "Custom location"))
            self.custom_radio.setToolTip(_("tip_install_custom", "Specify a custom installation location"))
        if hasattr(self, 'custom_path_edit'):
            self.custom_path_edit.setToolTip(_("tip_custom_path", "Specify the directory where you want to install the AppImage"))
        if hasattr(self, 'browse_button'):
            self.browse_button.setText(_("btn_browse", "Browse"))
            self.browse_button.setToolTip(_("tip_browse", "Browse for a custom installation directory"))
        if hasattr(self, 'install_button'):
            self.install_button.setText(_("btn_install", "Install"))
            self.install_button.setToolTip(_("tip_install", "Start the installation process for the selected AppImage"))
        if hasattr(self, 'cancel_button'):
            self.cancel_button.setText(_("btn_cancel", "Cancel"))
            self.cancel_button.setToolTip(_("tip_cancel", "Clear the form and cancel the installation process"))
            
        # Update manager tab
        if hasattr(self, 'search_entry'):
            self.search_entry.setToolTip(_("tip_search", "Filter the list of installed applications"))
        if hasattr(self, 'sort_combo'):
            current_index = self.sort_combo.currentIndex()
            self.sort_combo.clear()
            self.sort_combo.addItems([
                _("sort_name", "Name"),
                _("sort_date", "Install Date"),
                # _("sort_size", "Size")
            ])
            if current_index >= 0 and current_index < self.sort_combo.count():
                self.sort_combo.setCurrentIndex(current_index)
            self.sort_combo.setToolTip(_("tip_sort", "Sort the list of installed applications"))
        if hasattr(self, 'app_list_view'):
            self.app_list_view.setToolTip(_("tip_app_list", "List of installed AppImage applications"))
        if hasattr(self, 'open_button'):
            self.open_button.setText(_("btn_open", "Open"))
            self.open_button.setToolTip(_("tip_open", "Launch the selected application"))
        if hasattr(self, 'uninstall_button'):
            self.uninstall_button.setText(_("btn_uninstall", "Uninstall"))
            self.uninstall_button.setToolTip(_("tip_uninstall", "Uninstall the selected application"))
            
        # Recreate about tab - it needs to be completely rebuilt
        self._create_about_tab()
        
        # Update menu bar
        self._update_menu_translations()
        
        # Update welcome widget
        if hasattr(self, 'welcome_widget'):
            # It's easier to recreate the welcome widget
            if self.welcome_widget and not self.welcome_widget.isHidden():
                old_widget = self.welcome_widget
                self.welcome_widget = self._create_welcome_widget()
                main_layout = self.centralWidget().layout()
                main_layout.replaceWidget(old_widget, self.welcome_widget)
                old_widget.deleteLater()
                
        # Update stats
        self._update_stats()
        
        # Force update of all widgets to show the new translations
        self.centralWidget().update()
        
        # Emit signal that UI has been updated
        logger.info("UI texts updated for new language")
        
    def _update_menu_translations(self):
        """Update menu translations."""
        # Find and update all menus by their object names or titles
        menubar = self.menuBar()
        
        # Go through all actions in the menubar
        for menu in menubar.findChildren(QMenu):
            # We'll try to identify menus by their title to update them
            if menu.title() == "File" or menu.objectName() == "menu_file":
                menu.setTitle(_("menu_file", "File"))
                for action in menu.actions():
                    if action.text() == "Refresh" or action.objectName() == "action_refresh":
                        action.setText(_("menu_refresh", "Refresh"))
                    elif action.text() == "Exit" or action.objectName() == "action_exit":
                        action.setText(_("menu_exit", "Exit"))
                        
            elif menu.title() == "Tools" or menu.objectName() == "menu_tools":
                menu.setTitle(_("menu_tools", "Tools"))
                for action in menu.actions():
                    if action.text() == "Settings" or action.objectName() == "action_settings":
                        action.setText(_("menu_settings", "Settings"))
                        
            elif menu.title() == "Language" or menu.objectName() == "menu_language":
                menu.setTitle(_("menu_language", "Language"))
                
            elif menu.title() == "Help" or menu.objectName() == "menu_help":
                menu.setTitle(_("menu_help", "Help"))
                for action in menu.actions():
                    if action.text() == "About" or action.objectName() == "action_about":
                        action.setText(_("menu_about", "About"))

    def _handle_tab_changed(self, index):
        """Handle tab changed event to ensure content is updated."""
        # Log which tab was selected
        logger.debug(f"Switched to page index: {index}")
        
        # Update the UI based on which tab is selected
        if index == 0:  # Install tab
            # Update installer tab if needed
            pass
        elif index == 1:  # Manage tab
            # Refresh the list of installed applications
            self._update_manager_list()
        elif index == 2:  # About tab
            # Log the current state of the About tab for debugging
            logger.debug("About tab selected, checking content")
            self._debug_tab_content(self.tab_about, "About (before check)")
            
            # Check if the About tab is properly filled
            try:
                # Check for specific placeholder text or empty tab
                recreate_needed = False
                placeholder_found = False
                
                if not self.tab_about.layout():
                    logger.debug("About tab has no layout")
                    recreate_needed = True
                elif self.tab_about.layout().count() <= 1:
                    logger.debug("About tab has only one or zero items")
                    recreate_needed = True
                else:
                    # Search for placeholder text
                    for i in range(self.tab_about.layout().count()):
                        item = self.tab_about.layout().itemAt(i)
                        if item and item.widget() and isinstance(item.widget(), QLabel):
                            label_text = item.widget().text()
                            if "placeholder" in label_text.lower() or label_text == "about page content (placeholder)":
                                logger.debug(f"Found placeholder text: {label_text}")
                                placeholder_found = True
                                recreate_needed = True
                                break
                    
                    # If no placeholder found, check for required content
                    if not placeholder_found:
                        has_features = False
                        has_developer = False
                        has_description = False
                        
                        # Look for key elements that should be in the about tab
                        for i in range(self.tab_about.layout().count()):
                            item = self.tab_about.layout().itemAt(i)
                            if item and item.widget():
                                if isinstance(item.widget(), QGroupBox):
                                    title = item.widget().title()
                                    if _("about_features", "Features") in title:
                                        has_features = True
                                    elif _("about_developer_info", "Developer Information") in title:
                                        has_developer = True
                                elif isinstance(item.widget(), QLabel) and isinstance(item.widget().text(), str):
                                    if "AppImage Manager" in item.widget().text():
                                        has_description = True
                        
                        # If missing key sections, recreate the tab
                        if not (has_features and has_developer):
                            logger.debug("About tab missing expected content")
                            recreate_needed = True
                
                # Recreate if needed
                if recreate_needed:
                    logger.debug("Recreating about tab")
                    success = self._create_about_tab()
                    if not success:
                        logger.error("Failed to create about tab!")
            except Exception as e:
                logger.error(f"Error checking about tab content: {e}")
                logger.error(traceback.format_exc())
                # Force recreation of about tab if there was an error
                self._create_about_tab()
            
            # Log the updated state after potential recreation
            logger.debug("After potential recreation:")
            self._debug_tab_content(self.tab_about, "About (after check)")
            
        # Update status bar with appropriate message for the selected tab
        tab_names = ["tab_install", "tab_manage", "tab_about"]
        if index < len(tab_names):
            # Update status bar with the name of the current tab
            status_message = f"{_('status_ready', 'Ready')} | {_(tab_names[index])}"
            self.statusBar().showMessage(status_message)

    def _create_welcome_widget(self):
        """Create a welcome widget with app statistics."""
        widget = QWidget()
        layout = QHBoxLayout(widget)
        layout.setContentsMargins(15, 10, 15, 10)
        
        # Left side - greeting message
        greeting_widget = QWidget()
        greeting_layout = QVBoxLayout(greeting_widget)
        greeting_layout.setContentsMargins(0, 0, 0, 0)
        
        greeting_label = QLabel(f"<h3>{_('welcome_greeting', 'Welcome to AppImage Manager')}</h3>")
        greeting_label.setStyleSheet("color: #1a73e8; font-weight: bold;")
        greeting_layout.addWidget(greeting_label)
        
        description = QLabel(_('welcome_desc', 'Easily install, manage, and integrate AppImage applications with your system.'))
        description.setWordWrap(True)
        greeting_layout.addWidget(description)
        
        layout.addWidget(greeting_widget, 2)  # Larger proportion to left side
        
        # Right side - quick stats
        stats_widget = QWidget()
        stats_widget.setObjectName("stats_widget")  # For styling
        stats_layout = QHBoxLayout(stats_widget)
        
        # Stats counters
        self.stats_installed = self._create_stat_box(_('stat_installed', 'Installed'), '0')
        self.stats_system = self._create_stat_box(_('stat_system', 'System Apps'), '0')
        self.stats_user = self._create_stat_box(_('stat_user', 'User Apps'), '0')
        
        stats_layout.addWidget(self.stats_installed)
        stats_layout.addWidget(self.stats_system)
        stats_layout.addWidget(self.stats_user)
        
        layout.addWidget(stats_widget, 1)  # Smaller proportion to right side
        
        # Add close button
        close_btn = QPushButton("×")
        close_btn.setObjectName("welcome_close_btn")
        close_btn.setFixedSize(24, 24)
        close_btn.setToolTip(_('tip_close_welcome', 'Hide welcome message'))
        close_btn.clicked.connect(lambda: widget.setVisible(False))
        layout.addWidget(close_btn)
        
        # Additional styling
        widget.setObjectName("welcome_widget")
        
        # More prominent styling with stronger colors and border
        widget.setStyleSheet("""
            #welcome_widget {
                background-color: rgba(26, 115, 232, 0.15);
                border-radius: 8px;
                border: 2px solid rgba(26, 115, 232, 0.5);
                margin-bottom: 10px;
            }
            
            #stats_widget QWidget {
                background-color: rgba(255, 255, 255, 0.8);
                border-radius: 8px;
                border: 1px solid rgba(26, 115, 232, 0.3);
                padding: 5px;
                margin: 0 5px;
            }
            
            QMainWindow[darkMode="true"] #stats_widget QWidget {
                background-color: rgba(51, 51, 51, 0.8);
                border: 1px solid rgba(77, 171, 247, 0.3);
            }
            
            #welcome_close_btn {
                background-color: transparent;
                border: none;
                color: #777777;
                font-weight: bold;
                font-size: 16px;
            }
            
            #welcome_close_btn:hover {
                color: #333333;
            }
            
            QMainWindow[darkMode="true"] #welcome_widget {
                background-color: rgba(77, 171, 247, 0.15);
                border: 2px solid rgba(77, 171, 247, 0.5);
            }
            
            QMainWindow[darkMode="true"] #welcome_close_btn:hover {
                color: #cccccc;
            }
        """)
        
        # Ensure visibility
        widget.setVisible(True)
        
        return widget
        
    def _create_stat_box(self, title, value):
        """Create a box to display a statistic."""
        box = QWidget()
        layout = QVBoxLayout(box)
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(5)
        
        # Title
        title_label = QLabel(title)
        title_label.setAlignment(Qt.AlignCenter)
        font = title_label.font()
        font.setPointSize(font.pointSize() - 1)
        title_label.setFont(font)
        title_label.setStyleSheet("color: #666666;")
        
        # Value
        value_label = QLabel(value)
        value_label.setAlignment(Qt.AlignCenter)
        font = value_label.font()
        font.setPointSize(font.pointSize() + 2)
        font.setBold(True)
        value_label.setFont(font)
        value_label.setStyleSheet("color: #1a73e8;")
        
        # Add to layout
        layout.addWidget(title_label)
        layout.addWidget(value_label)
        
        return box
        
    def _update_stats(self):
        """Update the statistics in the welcome widget."""
        try:
            # Get counts from database or calculate them
            apps = self.db.get_all_apps()
            total_count = len(apps)
            system_count = 0
            user_count = 0
            
            for app in apps:
                install_mode = app.get("install_mode", "")
                if install_mode == "system":
                    system_count += 1
                elif install_mode == "user":
                    user_count += 1
            
            # Update the stat boxes - find the second label in each box (the value label)
            for box, value in [
                (self.stats_installed, str(total_count)),
                (self.stats_system, str(system_count)),
                (self.stats_user, str(user_count))
            ]:
                # Find all child labels and update the second one (value label)
                labels = box.findChildren(QLabel)
                if len(labels) >= 2:
                    labels[1].setText(value)
            
        except Exception as e:
            logger.error(f"Error updating statistics: {e}")
            # Don't show an error message, just log it

    def _debug_tab_content(self, tab_widget, tab_name):
        """Debug helper to log the content of a tab widget.
        
        Args:
            tab_widget: The tab widget to inspect
            tab_name: Name of the tab for logging
        """
        try:
            logger.debug(f"Debugging {tab_name} tab content:")
            
            if not tab_widget.layout():
                logger.debug(f"  {tab_name} has no layout")
                return
                
            layout = tab_widget.layout()
            logger.debug(f"  Layout type: {type(layout).__name__}")
            logger.debug(f"  Item count: {layout.count()}")
            
            for i in range(layout.count()):
                item = layout.itemAt(i)
                if item.widget():
                    logger.debug(f"  Item {i}: {type(item.widget()).__name__}")
                    if isinstance(item.widget(), QGroupBox):
                        logger.debug(f"    GroupBox title: {item.widget().title()}")
                elif item.layout():
                    logger.debug(f"  Item {i}: {type(item.layout()).__name__} (nested layout)")
                else:
                    logger.debug(f"  Item {i}: {type(item).__name__}")
                    
        except Exception as e:
            logger.error(f"Error debugging {tab_name} tab: {e}")
