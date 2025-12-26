"""
AppImage Yöneticisi - Yardımcı Araçlar
Loglama, hata işleme ve diğer yardımcı fonksiyonlar.
"""

import os
import logging
from logging.handlers import RotatingFileHandler
from . import config
import re
import shutil

logger = logging.getLogger(__name__)

def setup_logging():
    """Uygulama için loglama yapılandırmasını ayarlar."""
    # Log dizinini oluştur
    log_dir = os.path.dirname(config.LOG_PATH)
    if not os.path.exists(log_dir):
        os.makedirs(log_dir, exist_ok=True)
    
    # Root logger'ı yapılandır
    root_logger = logging.getLogger()
    
    # Log seviyesini ayarla
    level = getattr(logging, config.LOG_LEVEL.upper(), logging.INFO)
    root_logger.setLevel(level)
    
    # Dosya handler'ı ekle
    file_handler = RotatingFileHandler(
        config.LOG_PATH, 
        maxBytes=config.MAX_LOG_SIZE, 
        backupCount=config.MAX_LOG_BACKUPS
    )
    # Include function name in the log format
    file_formatter = logging.Formatter(
        '%(asctime)s - %(name)s.%(funcName)s - %(levelname)s - %(message)s'
    )
    file_handler.setFormatter(file_formatter)
    root_logger.addHandler(file_handler)
    
    # Konsol handler'ı ekle
    console_handler = logging.StreamHandler()
    # Keep console format simpler, without function name for brevity
    console_formatter = logging.Formatter(
        '%(levelname)s: [%(name)s] %(message)s' 
    )
    console_handler.setFormatter(console_formatter)
    root_logger.addHandler(console_handler)
    
    return root_logger 

def sanitize_name(name):
    """Sanitizes an application name for use in directory or file names.
    Removes special characters and replaces spaces.
    SECURITY: Prevents path traversal attacks.
    """
    if not name:
        return None
        
    try:
        # Convert to lowercase
        name = name.lower()
        
        # SECURITY: URL decode potential encoded characters first
        # This prevents bypassing sanitization with %2F, %2E, etc.
        import urllib.parse
        try:
            name = urllib.parse.unquote(name)
        except Exception:
            pass  # If decoding fails, continue with original
        
        # SECURITY: Remove all path separators and traversal patterns
        # This MUST happen before any other processing
        name = name.replace('/', '_')
        name = name.replace('\\', '_')
        name = name.replace('..', '')  # Remove directory traversal
        
        # Pre-check if the name is already clean and simple (only letters, no spaces or special chars)
        if re.match(r'^[a-z0-9]+$', name):
            # Name is already clean and simple, return as is
            return name
            
        # Remove version numbers or similar patterns (e.g., -1.2.3, _v2)
        name = re.sub(r'[-_ ]?v?[0-9]+(\.[0-9]+)*([-_].*)?$', '', name)
        # Replace spaces and common separators with underscore
        name = re.sub(r'[\s/:]+', '_', name)
        # Remove characters not suitable for filenames (allow letters, numbers, underscore, hyphen, dot)
        # SECURITY: Explicitly disallow / and \ even though regex should catch them
        name = re.sub(r'[^a-z0-9_\-\.]', '', name)
        # Remove leading/trailing underscores/hyphens/dots
        name = name.strip('_-.')
        
        # SECURITY: Final check - remove any remaining path traversal attempts
        while '..' in name:
            name = name.replace('..', '')
        
        # Ensure name is not empty after sanitization
        if not name:
            logger.warning("Sanitization resulted in an empty name.")
            # Fallback to a generic name or raise an error?
            return "sanitized_app"
        
        # Fix names with multiple consecutive underscores
        name = re.sub(r'_+', '_', name)
        
        return name
    except Exception as e:
        logger.error(f"Error sanitizing name '{name}': {e}")
        # Fallback in case of unexpected error
        return "sanitization_error"


# --- System Checks ---

def check_libfuse():
    """Checks if libfuse (fusermount command) seems to be installed."""
    # Check for fusermount or fusermount3
    fusermount_cmd = shutil.which("fusermount") or shutil.which("fusermount3")
    if fusermount_cmd:
        logger.info(f"FUSE check passed (found {os.path.basename(fusermount_cmd)}).")
        return True
    else:
        logger.warning(f"FUSE check failed: Neither 'fusermount' nor 'fusermount3' found in PATH.")
        return False 