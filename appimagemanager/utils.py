"""
AppImage Yöneticisi - Yardımcı Araçlar
Loglama, hata işleme ve diğer yardımcı fonksiyonlar.
"""

import os
import logging
from logging.handlers import RotatingFileHandler
from . import config

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
    file_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    file_handler.setFormatter(file_formatter)
    root_logger.addHandler(file_handler)
    
    # Konsol handler'ı ekle
    console_handler = logging.StreamHandler()
    console_formatter = logging.Formatter(
        '%(levelname)s: %(message)s'
    )
    console_handler.setFormatter(console_formatter)
    root_logger.addHandler(console_handler)
    
    return root_logger 