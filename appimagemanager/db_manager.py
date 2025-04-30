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

import config

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

    def _save_db(self):
        """Veritabanı değişikliklerini kaydeder."""
        self.data["last_updated"] = datetime.datetime.now().isoformat()
        try:
            with open(self.db_path, 'w', encoding='utf-8') as f:
                json.dump(self.data, f, ensure_ascii=False, indent=4)
            logger.debug("Veritabanı değişiklikleri kaydedildi")
            return True
        except Exception as e:
            logger.error(f"Veritabanı kaydedilirken hata: {e}")
            return False

    def add_app(self, app_info):
        """Yeni bir AppImage uygulamasını veritabanına ekler.
        
        Args:
            app_info (dict): Uygulama bilgilerini içeren dictionary:
                {
                    "id": "Benzersiz uygulama kimliği",
                    "name": "Uygulama Adı",
                    "appimage_path": "Orijinal AppImage yolu",
                    "install_path": "Kurulum dizini",
                    "extracted_files": ["Çıkarılan dosya ve dizinlerin listesi"],
                    "desktop_file": "Oluşturulan .desktop dosyasının yolu (varsa)",
                    "install_date": "Kurulum tarihi",
                    "install_mode": "Kurulum modu (system, user, custom)"
                }
        
        Returns:
            bool: İşlem başarılıysa True, değilse False
        """
        try:
            # Check if app with the same install path already exists (better than name)
            existing_app = None
            for app in self.data["installed_apps"]:
                # Comparing install_path might be more robust than name
                if app.get("install_path") == app_info.get("install_path"):
                    logger.warning(f"Uygulama zaten kurulu görünüyor: {app_info.get('name')} ({app_info.get('install_path')})")
                    existing_app = app
                    break
            
            if existing_app:
                # Update existing entry instead of adding duplicate
                # Ensure ID is preserved if it exists
                app_id = existing_app.get("id")
                existing_app.update(app_info)
                if app_id: # Keep the original ID
                     existing_app["id"] = app_id
                elif "id" not in existing_app: # Add ID if missing (shouldn't happen ideally)
                     existing_app["id"] = str(uuid.uuid4())
                existing_app["install_date"] = datetime.datetime.now().isoformat() # Update install date on overwrite? Or keep original?
                logger.info(f"Mevcut uygulama güncellendi: {existing_app['name']}")
            else:
                # Add ID to the new app info
                app_info["id"] = str(uuid.uuid4())
                # Set install date
                app_info["install_date"] = datetime.datetime.now().isoformat()
                self.data["installed_apps"].append(app_info)
                logger.info(f"Yeni uygulama eklendi: {app_info['name']} (ID: {app_info['id']})")

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