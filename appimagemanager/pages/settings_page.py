"""
AppImage Manager - Settings Page UI
Provides the graphical interface for configuring application settings.
"""

from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                             QPushButton, QGroupBox, QRadioButton, QComboBox, 
                             QSpacerItem, QSizePolicy, QFormLayout, QMessageBox)
from PyQt6.QtCore import Qt

from .. import config
from ..i18n import get_translator, AVAILABLE_LANGUAGES # Import AVAILABLE_LANGUAGES dict

# Get the translator instance
translator = get_translator()

class SettingsPage(QWidget):
    """UI elements for the application settings page."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("settingsPage")
        
        # --- Main Layout ---
        main_layout = QVBoxLayout(self)
        main_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        # --- Language Settings ---
        language_group = QGroupBox(translator.get_text("Language Settings"))
        language_group.setObjectName("language_group")
        language_layout = QFormLayout()
        language_layout.setContentsMargins(10, 15, 10, 10)
        language_layout.setSpacing(10)
        
        self.language_combo = QComboBox()
        # Populate language options
        for lang_code, lang_name in AVAILABLE_LANGUAGES.items():
            self.language_combo.addItem(f"{lang_name} ({lang_code})", lang_code)
            
        # Select current language (implement loading logic later)
        # current_lang = config.get_setting('language', config.DEFAULT_LANGUAGE)
        # index = self.language_combo.findData(current_lang)
        # if index != -1:
        #     self.language_combo.setCurrentIndex(index)
            
        language_layout.addRow(translator.get_text("Application Language:"), self.language_combo)
        language_group.setLayout(language_layout)
        main_layout.addWidget(language_group)
        main_layout.addSpacing(15)

        # --- Default Installation Settings ---
        install_group = QGroupBox(translator.get_text("Default Installation Mode"))
        install_group.setObjectName("install_group")
        install_layout = QVBoxLayout()
        install_layout.setContentsMargins(10, 15, 10, 10)
        install_layout.setSpacing(10)

        self.default_user_radio = QRadioButton(translator.get_text("User Installation") + f" (~/.local/share)")
        self.default_system_radio = QRadioButton(translator.get_text("System Installation") + f" (/opt)")
        
        # Load current default (implement loading logic later)
        # current_default_mode = config.get_setting('default_install_mode', config.DEFAULT_INSTALL_MODE)
        # self.default_user_radio.setChecked(current_default_mode == 'user')
        # self.default_system_radio.setChecked(current_default_mode == 'system')

        install_layout.addWidget(self.default_user_radio)
        install_layout.addWidget(self.default_system_radio)
        install_group.setLayout(install_layout)
        main_layout.addWidget(install_group)
        main_layout.addSpacing(15)

        # --- Theme Settings ---
        theme_group = QGroupBox(translator.get_text("Theme Settings"))
        theme_group.setObjectName("theme_group")
        theme_layout = QVBoxLayout()
        theme_layout.setContentsMargins(10, 15, 10, 10)
        theme_layout.setSpacing(10)

        self.light_theme_radio = QRadioButton(translator.get_text("Light Theme"))
        self.dark_theme_radio = QRadioButton(translator.get_text("Dark Theme"))
        
        theme_layout.addWidget(self.light_theme_radio)
        theme_layout.addWidget(self.dark_theme_radio)
        theme_group.setLayout(theme_layout)
        main_layout.addWidget(theme_group)
        main_layout.addSpacing(15)

        # --- Spacer --- 
        main_layout.addSpacerItem(QSpacerItem(20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding))

        # --- Save Button --- 
        button_layout = QHBoxLayout()
        button_layout.addStretch(1)
        self.save_button = QPushButton(translator.get_text("Save Settings"))
        self.save_button.clicked.connect(self.save_settings)
        button_layout.addWidget(self.save_button)
        main_layout.addLayout(button_layout)
        
        # Load settings when page is created
        self.load_settings()

    def load_settings(self):
        """Loads current settings from config and updates UI."""
        logger.info("Loading settings...")
        try:
            current_lang = config.get_setting('language', config.DEFAULT_LANGUAGE)
            index = self.language_combo.findData(current_lang)
            if index != -1:
                self.language_combo.setCurrentIndex(index)
            else:
                 logger.warning(f"Saved language '{current_lang}' not found in options, using default.")
                 # Optionally set to default index
                 index = self.language_combo.findData(config.DEFAULT_LANGUAGE)
                 if index != -1: self.language_combo.setCurrentIndex(index)
            
            current_default_mode = config.get_setting('default_install_mode', config.DEFAULT_INSTALL_MODE)
            self.default_user_radio.setChecked(current_default_mode == 'user')
            self.default_system_radio.setChecked(current_default_mode == 'system')

            # Load theme setting
            dark_mode = config.get_setting('dark_mode', False)
            self.dark_theme_radio.setChecked(dark_mode)
            self.light_theme_radio.setChecked(not dark_mode)
        except Exception as e:
             logger.error(f"Error loading settings: {e}", exc_info=True)
             # Keep default UI values

    def save_settings(self):
        """Saves the selected settings to config."""
        logger.info("Saving settings...")
        try:
            settings_changed = False
            
            # --- Save Theme Setting First ---
            # Önce temayı kaydediyoruz ki dil değişiminden etkilenmesin
            new_dark_mode = self.dark_theme_radio.isChecked()
            current_dark_mode = config.get_setting('dark_mode', False)
            if new_dark_mode != current_dark_mode:
                if config.set_setting('dark_mode', new_dark_mode):
                    logger.info(f"Theme setting saved: {'dark' if new_dark_mode else 'light'}")
                    settings_changed = True
                    # Apply theme immediately
                    if hasattr(self.window(), 'dark_mode') and hasattr(self.window(), 'update_theme'):
                        self.window().dark_mode = new_dark_mode
                        self.window().update_theme()
                else:
                    logger.error("Failed to save theme setting.")
                    QMessageBox.warning(self, translator.get_text("Error"), translator.get_text("Could not save theme setting."))
            else:
                logger.debug("Theme setting unchanged.")

            # --- Save Default Install Mode --- 
            new_default_mode = 'user' if self.default_user_radio.isChecked() else 'system'
            current_default_mode = config.get_setting('default_install_mode', config.DEFAULT_INSTALL_MODE)
            if new_default_mode != current_default_mode:
                if config.set_setting('default_install_mode', new_default_mode):
                    logger.info(f"Default install mode saved: {new_default_mode}")
                    settings_changed = True
                else:
                    logger.error("Failed to save default install mode setting.")
                    QMessageBox.warning(self, translator.get_text("Error"), translator.get_text("Could not save default install mode setting."))
            else:
                 logger.debug("Default install mode unchanged.")

            # --- Save Language (Last) --- 
            selected_lang_index = self.language_combo.currentIndex()
            selected_lang_code = self.language_combo.itemData(selected_lang_index)
            language_changed = False
            if selected_lang_code:
                 # Check if language actually changed
                 current_lang = config.get_setting('language', config.DEFAULT_LANGUAGE)
                 if selected_lang_code != current_lang:
                     if config.set_setting('language', selected_lang_code):
                         logger.info(f"Language setting saved: {selected_lang_code}")
                         # Update translator immediately
                         translator.set_language(selected_lang_code)
                         language_changed = True
                         settings_changed = True
                         
                         # Update all UI text in real-time
                         if hasattr(self.window(), 'update_ui_texts'):
                             self.window().update_ui_texts()
                     else:
                         logger.error("Failed to save language setting.")
                         QMessageBox.warning(self, translator.get_text("Error"), translator.get_text("Could not save language setting."))
                 else:
                      logger.debug("Language setting unchanged.")
            else:
                 logger.error("Could not determine selected language code.")

            # Show appropriate messages
            if settings_changed:
                if language_changed:
                    # Restart artık gerekli değil, UI anında güncelleniyor
                    QMessageBox.information(self, 
                        translator.get_text("Settings Saved"),
                        translator.get_text("Settings saved, language has been changed."))
                else:
                    QMessageBox.information(self, 
                        translator.get_text("Settings Saved"),
                        translator.get_text("Settings saved successfully."))

        except Exception as e:
            logger.error(f"Error saving settings: {e}", exc_info=True)
            QMessageBox.critical(self, translator.get_text("Error"), translator.get_text("An error occurred while saving settings."))

    def retranslateUi(self):
        """Update all UI texts for language changes"""
        translator = get_translator()  # Get fresh translator
        
        # Update group box titles based on objectName
        for widget in self.findChildren(QGroupBox):
            name = widget.objectName()
            if name == "language_group":
                widget.setTitle(translator.get_text("Language Settings"))
            elif name == "install_group":
                widget.setTitle(translator.get_text("Default Installation Mode"))
            elif name == "theme_group":
                widget.setTitle(translator.get_text("Theme Settings"))
        
        # Update radio buttons
        self.default_user_radio.setText(translator.get_text("install_mode_user") + " (~/.local/share)")
        self.default_system_radio.setText(translator.get_text("install_mode_system") + " (/opt)")
        self.light_theme_radio.setText(translator.get_text("Light Theme"))
        self.dark_theme_radio.setText(translator.get_text("Dark Theme"))
        
        # Update language label
        language_layout = self.language_combo.parent().layout()
        if language_layout and isinstance(language_layout, QFormLayout):
            language_layout.labelForField(self.language_combo).setText(translator.get_text("Application Language:"))
        
        # Update save button
        self.save_button.setText(translator.get_text("Save Settings"))

# --- Logger Setup (Example - Adapt as needed) ---
import logging
logger = logging.getLogger(__name__)
if not logger.hasHandlers():
    handler = logging.StreamHandler()
    formatter = logging.Formatter('%(levelname)s: %(name)s: %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.setLevel(logging.DEBUG) 