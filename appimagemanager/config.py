"""
AppImage Manager - Configuration File
Contains constant values and configuration settings used throughout the application.
"""

import os
from pathlib import Path
import json
import logging

# --- Setup Logger for config module --- 
# Use a basic logger setup here, assuming main setup handles file/console
logger = logging.getLogger(__name__)
if not logger.hasHandlers():
    logger.addHandler(logging.NullHandler()) # Prevent 'No handler found' warnings
# You might want to configure a more specific logger if needed

# Application information
APP_NAME = "appimagemanager"
APP_VERSION = "1.0.3"
APP_DESCRIPTION = "Install, manage and remove AppImage applications on Linux"

# System constants
LIBFUSE_PACKAGE = "fuse2"  # For most Linux distributions

# Directory configuration
USER_HOME = str(Path.home())
CONFIG_DIR = os.path.join(USER_HOME, ".config", "appimage-manager")
DATABASE_PATH = os.path.join(CONFIG_DIR, "installed.json")
LOG_PATH = os.path.join(CONFIG_DIR, "appimage-manager.log")
SETTINGS_PATH = os.path.join(CONFIG_DIR, "settings.json")
APP_DIR_NAME = "appimage-manager-apps"

# System Installation Paths (Adjust if needed)
SYSTEM_INSTALL_DIR = "/opt/appimage-manager-apps" # Example system-wide install location
SYSTEM_BIN_DIR = "/usr/local/bin" # Directory for executable links
SYSTEM_DESKTOP_DIR = "/usr/local/share/applications" # Directory for .desktop files
# SYSTEM_ICON_DIR = "/usr/local/share/icons" # Base for icons (less commonly used directly?)

# Application preferences
DEFAULT_LANGUAGE = "en"  # Default language code (en, tr)
DEFAULT_INSTALL_MODE = "user"  # "system" (/usr) or "user" (~/.local) or "custom"

# Installation destinations
# DEPRECATED - We will handle modes directly in the UI and utils
# INSTALL_DESTINATIONS = { ... }

# Management Types (New)
MGMT_TYPE_INSTALLED = "installed" # App files extracted, symlinked
MGMT_TYPE_REGISTERED = "registered" # Original AppImage file used, only registered in DB (+optional desktop/icon)

# Default Management Type (Can be used if needed, but likely install page decides)
# DEFAULT_MGMT_TYPE = MGMT_TYPE_INSTALLED

# GUI settings
WINDOW_WIDTH = 850
WINDOW_HEIGHT = 600
WINDOW_ICON = None  # We'll create our own icon in the code instead of relying on a file path

# Logging settings
LOG_LEVEL = "DEBUG"  # Changed to DEBUG temporarily
MAX_LOG_SIZE = 1024 * 1024 * 5  # 5 MB
MAX_LOG_BACKUPS = 3

# Feature flags
ENABLE_AUTO_UPDATES = True  # Check for updates to installed AppImages
ENABLE_DESKTOP_INTEGRATION = True  # Create .desktop files
ENABLE_CONTEXT_MENU = False  # Add right-click context menu (not implemented yet) 

# Installation Directories
USER_INSTALL_BASE = os.path.join(USER_HOME, ".local/share")
USER_INSTALL_DIR = os.path.join(USER_INSTALL_BASE, APP_DIR_NAME) # Dir for extracted installs
# --->>> Add Directory for Copied AppImages <<<---
MANAGED_APPIMAGES_DIR = os.path.join(USER_INSTALL_BASE, "appimage-manager-library") 

# Integration Directories (Examples - might vary by system)

# --- Settings Functions --- 

# Cache for loaded settings to avoid repeated file reads
_settings_cache = None

def _ensure_config_dir():
    """Ensures the main configuration directory exists."""
    if not os.path.exists(CONFIG_DIR):
        try:
            os.makedirs(CONFIG_DIR, exist_ok=True)
            logger.info(f"Configuration directory created: {CONFIG_DIR}")
        except Exception as e:
            logger.error(f"Failed to create configuration directory {CONFIG_DIR}: {e}")
            # Depending on severity, you might want to raise this

def _load_settings():
    """Loads settings from the JSON file into cache, creating defaults if needed."""
    global _settings_cache
    _ensure_config_dir() # Make sure directory exists before reading/writing
    
    # Default settings structure
    defaults = {
        'language': DEFAULT_LANGUAGE,
        'default_install_mode': DEFAULT_INSTALL_MODE,
        'dark_mode': False
        # Add other settings keys here as needed
    }
    
    if not os.path.exists(SETTINGS_PATH):
        logger.info(f"Settings file not found ({SETTINGS_PATH}). Creating with defaults.")
        _settings_cache = defaults.copy()
        _save_settings(_settings_cache) # Save the defaults immediately
        return _settings_cache

    try:
        with open(SETTINGS_PATH, 'r', encoding='utf-8') as f:
            loaded_settings = json.load(f)
            # Merge defaults with loaded settings to handle missing keys
            _settings_cache = defaults.copy()
            _settings_cache.update(loaded_settings) 
            logger.debug(f"Settings loaded from {SETTINGS_PATH}")
            return _settings_cache
    except json.JSONDecodeError:
        logger.error(f"Settings file ({SETTINGS_PATH}) is corrupted. Using defaults.")
        _settings_cache = defaults.copy()
        # Optionally backup corrupted file before overwriting
        # os.rename(SETTINGS_PATH, SETTINGS_PATH + ".corrupt") 
        _save_settings(_settings_cache) # Overwrite with defaults
        return _settings_cache
    except Exception as e:
        logger.error(f"Failed to load settings from {SETTINGS_PATH}: {e}. Using defaults.")
        _settings_cache = defaults.copy() # Use defaults in case of other errors
        return _settings_cache

def _save_settings(settings_dict):
    """Saves the given settings dictionary to the JSON file."""
    _ensure_config_dir() # Ensure directory exists
    try:
        with open(SETTINGS_PATH, 'w', encoding='utf-8') as f:
            json.dump(settings_dict, f, ensure_ascii=False, indent=4)
        logger.debug(f"Settings saved to {SETTINGS_PATH}")
        return True
    except Exception as e:
        logger.error(f"Failed to save settings to {SETTINGS_PATH}: {e}")
        return False

def get_setting(key, default=None):
    """Gets a setting value by key, loading from file if not cached."""
    global _settings_cache
    if _settings_cache is None:
        _settings_cache = _load_settings()
    
    # Determine the actual default value if not provided
    actual_default = default
    if actual_default is None:
         # Look up default from the structure defined in _load_settings
         defaults = {
             'language': DEFAULT_LANGUAGE,
             'default_install_mode': DEFAULT_INSTALL_MODE,
             'dark_mode': False
         }
         actual_default = defaults.get(key)
         
    return _settings_cache.get(key, actual_default)

def set_setting(key, value):
    """Sets a setting value by key and saves to file."""
    global _settings_cache
    if _settings_cache is None:
        _settings_cache = _load_settings()
        
    _settings_cache[key] = value
    return _save_settings(_settings_cache) 