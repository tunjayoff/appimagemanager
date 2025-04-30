"""
AppImage Yöneticisi - Veritabanı Yöneticisi
Kurulu AppImage uygulamalarını JSON tabanlı bir veritabanında takip eder.
"""

import json
import os
import datetime
import logging
import uuid
from pathlib import Path

from . import config

logger = logging.getLogger(__name__)

class DBManager:
    """Kurulu AppImage'leri bir JSON dosyasında takip eder."""

    def __init__(self):
        """Veritabanı bağlantısını başlatır."""
        self.db_path = config.DATABASE_PATH
        self._ensure_db_exists()
        self.data = self._load_db()

    def _ensure_db_exists(self):
        """Veritabanı dosyasının ve dizinin varlığını kontrol eder ve gerekirse oluşturur."""
        db_dir = os.path.dirname(self.db_path)
        if not os.path.exists(db_dir):
            try:
                os.makedirs(db_dir, exist_ok=True)
                logger.info(f"Veritabanı dizini oluşturuldu: {db_dir}")
            except Exception as e:
                logger.error(f"Veritabanı dizini oluşturulamadı: {e}")
                raise

        if not os.path.exists(self.db_path):
            initial_data = {
                "installed_apps": [],
                "last_updated": datetime.datetime.now().isoformat()
            }
            try:
                with open(self.db_path, 'w', encoding='utf-8') as f:
                    json.dump(initial_data, f, ensure_ascii=False, indent=4)
                logger.info(f"Veritabanı dosyası oluşturuldu: {self.db_path}")
            except Exception as e:
                logger.error(f"Veritabanı dosyası oluşturulamadı: {e}")
                raise

    def _load_db(self):
        """Veritabanı dosyasını yükler."""
        try:
            with open(self.db_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                # --- Backward compatibility: Add management_type if missing --- 
                updated_apps = []
                made_changes = False
                for app in data.get("installed_apps", []):
                    if "management_type" not in app:
                        app["management_type"] = config.MGMT_TYPE_INSTALLED # Default old entries to installed
                        logger.debug(f"Added default management_type to app: {app.get('name')}")
                        made_changes = True
                    updated_apps.append(app)
                data["installed_apps"] = updated_apps
                # Save immediately if we added default types
                if made_changes:
                    logger.info("Updating database with default management types for older entries...")
                    self._save_db(data) # Pass data to save
                # ---------------------------------------------------------------
                logger.debug(f"Veritabanı yüklendi: {len(data.get('installed_apps', [])) if data else 0} uygulama var")
                return data
        except json.JSONDecodeError:
            logger.error(f"Veritabanı bozuk: {self.db_path}")
            # Bozuk veritabanını yedekleyip yeni bir tane oluşturalım
            os.rename(self.db_path, f"{self.db_path}.corrupt.{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}")
            self._ensure_db_exists()
            return self._load_db()
        except Exception as e:
            logger.error(f"Veritabanı yüklenirken hata: {e}")
            raise

    def _save_db(self, data_to_save=None):
        """Veritabanı değişikliklerini kaydeder."""
        # Use provided data if available (for initial load saving), otherwise use self.data
        current_data = data_to_save if data_to_save is not None else self.data
        
        current_data["last_updated"] = datetime.datetime.now().isoformat()
        try:
            with open(self.db_path, 'w', encoding='utf-8') as f:
                json.dump(current_data, f, ensure_ascii=False, indent=4)
            # If we saved data passed as argument, update self.data as well
            if data_to_save is not None:
                self.data = current_data
            logger.debug("Veritabanı değişiklikleri kaydedildi")
            return True
        except Exception as e:
            logger.error(f"Veritabanı kaydedilirken hata: {e}")
            return False

    def add_app(self, app_info):
        """Yeni bir AppImage uygulamasını veritabanına ekler.
        
        Args:
            app_info (dict): Uygulama bilgilerini içeren dictionary.
                             MUST contain 'management_type' (installed/registered).
                             Other fields depend on the type.
                             Example keys: id, name, version, appimage_path, 
                             app_install_dir, symlinks_created, desktop_file, icon_path, 
                             install_date, management_type
        
        Returns:
            bool: İşlem başarılıysa True, değilse False
        """
        try:
            # Ensure management_type is present
            if "management_type" not in app_info or app_info["management_type"] not in [config.MGMT_TYPE_INSTALLED, config.MGMT_TYPE_REGISTERED]:
                logger.error(f"Cannot add app: Missing or invalid management_type in app_info for {app_info.get('name')}")
                return False
            
            # Check for duplicates based on different criteria depending on type
            existing_app = None
            if app_info["management_type"] == config.MGMT_TYPE_INSTALLED:
                # For installed apps, check install directory
                check_key = "app_install_dir"
                check_val = app_info.get(check_key)
            else: # Registered apps
                # For registered apps, check original AppImage path
                check_key = "appimage_path"
                check_val = app_info.get(check_key)

            if check_val: # Only check if the relevant key exists and has a value
                for app in self.data["installed_apps"]:
                    if app.get(check_key) == check_val and app.get("management_type") == app_info["management_type"]:
                        logger.warning(f"Uygulama ({app_info['management_type']}) zaten kayıtlı görünüyor: {app_info.get('name')} ({check_key}: {check_val})")
                        existing_app = app
                        break
            
            if existing_app:
                # Update existing entry
                app_id = existing_app.get("id")
                # Preserve important fields if they exist and aren't in new info
                for key_to_preserve in ["id", "install_date"]:
                    if key_to_preserve in existing_app and key_to_preserve not in app_info:
                        app_info[key_to_preserve] = existing_app[key_to_preserve]
                
                existing_app.update(app_info)
                # Ensure ID is still present
                if "id" not in existing_app:
                    existing_app["id"] = str(uuid.uuid4())
                logger.info(f"Mevcut uygulama kaydı güncellendi: {existing_app['name']}")
            else:
                # Add new entry
                app_info["id"] = str(uuid.uuid4())
                app_info["install_date"] = datetime.datetime.now().isoformat()
                # Ensure all essential keys have default values if missing?
                # Example: version might be missing
                app_info.setdefault("version", "unknown")
                self.data["installed_apps"].append(app_info)
                logger.info(f"Yeni uygulama ({app_info['management_type']}) eklendi: {app_info['name']} (ID: {app_info['id']})")

            return self._save_db()
        except Exception as e:
            logger.error(f"Uygulama eklenirken hata: {e}")
            return False

    def remove_app(self, app_id):
        """Bir uygulamayı veritabanından ID kullanarak kaldırır.
        
        Args:
            app_id (str): Kaldırılacak uygulamanın benzersiz ID'si
            
        Returns:
            bool: İşlem başarılıysa True, değilse False
        """
        if not app_id:
            logger.error("Uygulama kaldırılamadı: Geçersiz ID sağlandı.")
            return False
            
        try:
            initial_len = len(self.data["installed_apps"])
            # Filter out the app with the matching ID
            self.data["installed_apps"] = [
                app for app in self.data["installed_apps"] if app.get("id") != app_id
            ]
            
            if len(self.data["installed_apps"]) < initial_len:
                logger.info(f"Uygulama veritabanından kaldırıldı (ID: {app_id})")
                return self._save_db()
            else:
                logger.warning(f"Kaldırılacak uygulama bulunamadı (ID: {app_id})")
                return False # App with that ID wasn't found
        except Exception as e:
            logger.error(f"Uygulama kaldırılırken hata (ID: {app_id}): {e}")
            return False

    def get_app(self, app_id):
        """Belirli bir uygulamanın bilgilerini ID kullanarak getirir.
        
        Args:
            app_id (str): Uygulamanın benzersiz ID'si
            
        Returns:
            dict: Uygulama bilgileri veya None
        """
        if not app_id:
             return None
        try:
            for app in self.data["installed_apps"]:
                if app.get("id") == app_id:
                    return app
            return None
        except Exception as e:
            logger.error(f"Uygulama bilgisi alınırken hata (ID: {app_id}): {e}")
            return None

    def get_all_apps(self):
        """Tüm kurulu uygulamaların listesini döndürür.
        
        Returns:
            list: Kurulu uygulamaların bilgilerini içeren liste
        """
        try:
            return self.data.get("installed_apps", [])
        except Exception as e:
            logger.error(f"Tüm uygulamalar alınırken hata: {e}")
            return []

    def update_app(self, app_id, updated_info):
        """Bir uygulamanın bilgilerini ID kullanarak günceller.
        
        Args:
            app_id (str): Güncellenecek uygulamanın benzersiz ID'si
            updated_info (dict): Güncellenecek alanlar ve değerleri
            
        Returns:
            bool: İşlem başarılıysa True, değilse False
        """
        if not app_id:
             logger.error("Uygulama güncellenemedi: Geçersiz ID sağlandı.")
             return False
             
        try:
            app_found = False
            for app in self.data["installed_apps"]:
                if app.get("id") == app_id:
                    # Ensure the ID itself is not overwritten by updated_info
                    original_id = app.get("id")
                    app.update(updated_info)
                    app["id"] = original_id # Restore ID just in case
                    app_found = True
                    logger.info(f"Uygulama bilgileri güncellendi (ID: {app_id})")
                    break
            
            if app_found:
                return self._save_db()
            else:
                logger.warning(f"Güncellenecek uygulama bulunamadı (ID: {app_id})")
                return False
        except Exception as e:
            logger.error(f"Uygulama güncellenirken hata (ID: {app_id}): {e}")
            return False 