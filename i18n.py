"""
Translation module for AppImage Manager.
Handles loading and switching language resources.
"""

import json
import os
import logging
from pathlib import Path
from functools import lru_cache

# --- Setup Logger for i18n module ---
logger = logging.getLogger(__name__)
if not logger.hasHandlers():
    logger.addHandler(logging.NullHandler())

# --- Translation Files Path ---
# Default directory where translation files are located
_TRANSLATIONS_DIR = os.path.dirname(os.path.abspath(__file__))

# --- Available Languages (scanned from translation files) ---
def _scan_translation_files():
    """Scan the translations directory for available language codes and names."""
    langs = {}
    for fname in os.listdir(_TRANSLATIONS_DIR):
        if fname.startswith("translations_") and fname.endswith(".json"):
            code = fname[len("translations_"):-len(".json")]
            try:
                with open(os.path.join(_TRANSLATIONS_DIR, fname), 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    # Use provided language_name or fall back to code
                    name = data.get("language_name", code)
            except Exception:
                name = code
            langs[code] = name
    return langs

AVAILABLE_LANGUAGES = _scan_translation_files()

# --- Module Variables ---
_translations = {}  # Stores loaded translation dictionaries by language code
_current_language = "en"  # Default language

def set_translations_directory(path):
    """Set the directory where translation files are located."""
    global _TRANSLATIONS_DIR
    if os.path.isdir(path):
        _TRANSLATIONS_DIR = path
        logger.info(f"Translations directory set to: {path}")
        # Clear the cache when changing directory
        _load_translation_file.cache_clear()
        # Rescan available languages from the new directory
        global AVAILABLE_LANGUAGES
        AVAILABLE_LANGUAGES = _scan_translation_files()
        return True
    else:
        logger.error(f"Invalid translations directory: {path}")
        return False

@lru_cache(maxsize=None)  # Cache the loaded translation files
def _load_translation_file(lang_code):
    """Load a translation file for the given language code."""
    if not lang_code or lang_code not in AVAILABLE_LANGUAGES:
        logger.warning(f"Invalid language code: {lang_code}, using fallback")
        lang_code = "en"  # Fallback to English
    
    file_path = os.path.join(_TRANSLATIONS_DIR, f"translations_{lang_code}.json")
    
    try:
        if not os.path.exists(file_path):
            logger.error(f"Translation file not found: {file_path}")
            if lang_code != "en":
                # Try to fall back to English if another language file is missing
                return _load_translation_file("en")
            return {}  # Empty dictionary as last resort
        
        with open(file_path, 'r', encoding='utf-8') as f:
            translations = json.load(f)
            logger.info(f"Loaded translations for {lang_code}: {len(translations)} keys")
            return translations
    except json.JSONDecodeError:
        logger.error(f"Invalid JSON in translation file: {file_path}")
        if lang_code != "en":
            return _load_translation_file("en")  # Fall back to English
        return {}
    except Exception as e:
        logger.error(f"Error loading translation file {file_path}: {e}")
        if lang_code != "en":
            return _load_translation_file("en")  # Fall back to English
        return {}

class Translator:
    """Class to handle translations with built-in fallback mechanism."""
    
    def __init__(self, default_lang="en"):
        self.current_lang = default_lang
        self._translations = {}
        self._load_language(default_lang)
    
    def _load_language(self, lang_code):
        """Load a language's translations."""
        if lang_code not in self._translations:
            self._translations[lang_code] = _load_translation_file(lang_code)
        return self._translations[lang_code]
    
    def get_languages(self):
        """Return available languages dict."""
        return AVAILABLE_LANGUAGES
    
    def set_language(self, lang_code):
        """Set the current language."""
        if lang_code not in AVAILABLE_LANGUAGES:
            logger.warning(f"Language {lang_code} not available, using default")
            return False
        
        if lang_code != self.current_lang:
            # Force reload of translations to ensure we get the latest version
            _load_translation_file.cache_clear()
            self._translations[lang_code] = _load_translation_file(lang_code)
            self.current_lang = lang_code
            logger.info(f"Language changed to {AVAILABLE_LANGUAGES[lang_code]} ({lang_code})")
        return True
    
    def get_text(self, key, default=None, **replacements):
        """Get translated text for a key with optional replacements."""
        if key is None:
            return ''
            
        # Get text from current language with fallback to English
        translations = self._translations.get(self.current_lang, {})
        text = translations.get(key)
        
        # Fallback to English if not found in current language
        if text is None and self.current_lang != "en":
            en_translations = self._load_language("en")
            text = en_translations.get(key)
            if text:
                logger.debug(f"Fallback to English for key: {key}")
        
        # Use default or key itself if not found anywhere
        if text is None:
            if default is not None:
                text = default
                logger.debug(f"Using default text for key: {key}")
            else:
                logger.debug(f"Translation key not found: {key}")
                text = key  # Use the key itself as fallback
                
        # Apply any replacement arguments
        if replacements and text:
            try:
                text = text.format(**replacements)
            except KeyError as e:
                logger.warning(f"Invalid replacement key in '{key}': {e}")
            except Exception as e:
                logger.error(f"Error applying replacements to '{key}': {e}")
                
        return text

# --- Global translator instance ---
_translator = None

def set_language(lang_code):
    """Set the current language globally."""
    global _translator
    if _translator is None:
        _translator = Translator()
    return _translator.set_language(lang_code)

def get_translator():
    """Get the global translator instance."""
    global _translator
    if _translator is None:
        _translator = Translator()
    return _translator

def _(key, default=None, **replacements):
    """Shortcut function for get_text with improved fallback mechanism.
    
    Args:
        key: The translation key to look up
        default: Default text if key is not found in any translation file
        replacements: Format string parameters
        
    Returns:
        Translated text or fallback
    """
    global _translator
    if _translator is None:
        _translator = Translator()
    
    # Get the translated text or fallback to default
    text = _translator.get_text(key, default, **replacements)
    
    # If the text returned is just the key itself, it means translation failed
    # and default was None, so we'll log this for debugging
    if text == key and default is None:
        logger.debug(f"Missing translation for key: {key}")
    
    return text

# --- Force initial load of default language ---
get_translator() 