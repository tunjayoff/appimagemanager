# AppImage Manager

**Manage your AppImage files with ease on Ubuntu 24.04 and above! (may works for other debian based distros)**

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

GitHub: [https://github.com/tunjayoff/appimagemanager](https://github.com/tunjayoff/appimagemanager)

AppImage Manager provides a user-friendly interface to install, organize, launch, and remove AppImage applications. It integrates them into your system menu and helps keep things tidy.

---

## 📸 Screenshot

![Main Window](documentation/screenshot.png)

---

## ✨ Features

*   **Effortless Installation:**
    *   Install AppImages system-wide or just for your user.
    *   Choose a custom installation location.
    *   Drag & drop `.AppImage` files onto the window.
    *   "Register Only" mode: Add AppImages to the manager and menu without moving the original file.
*   **Simple Management:**
    *   View all managed AppImages in a sortable list.
    *   Search and filter your applications.
    *   Launch apps directly from the manager.
*   **Clean Uninstallation:**
    *   Remove installed AppImages and their menu entries with one click.
    *   Optional scan for leftover configuration files after uninstall.
*   **Recovery & Cleanup:**
    *   "Scan for Leftovers" feature helps find and remove installations missed by the database (e.g., after database loss).
*   **User-Friendly Interface:**
    *   Light and Dark themes with a quick toggle.
    *   Multi-language support (English and Turkish included).

---

## 🚀 Installation

There are three primary ways to install AppImage Manager:

**1. Using a Pre-built `.deb` File (Easiest & Recommended for Users)**

This is the simplest way if a `.deb` file is available from a release.

1.  **Download:** Go to the [Project Releases Page](https://github.com/tunjayoff/appimagemanager/releases) and download the latest `.deb` file (e.g., `appimagemanager_X.Y.Z_amd64.deb`).
2.  **Install via GUI:** In most cases, you can simply double-click the downloaded `.deb` file. Your system's software installer should open and allow you to install it (you might need to enter your password).
3.  **Install via Terminal (Alternative):**
    ```bash
    # Navigate to the directory where you downloaded the file
    # cd ~/Downloads 

    # Install the package (replace with the actual filename)
    sudo dpkg -i appimagemanager_X.Y.Z_amd64.deb

    # If you see errors about missing dependencies, run:
    sudo apt --fix-broken install 
    ```
4.  **Launch:** Find AppImage Manager in your application menu or run `appimagemanager` in the terminal.

**2. Using the Build & Install Script (For Building from Source)**

This script compiles the application from the source code and installs it as a system package (`.deb`). Useful if you want the latest code installed system-wide.

```bash
# 1. Clone the repository
# git clone https://github.com/tunjayoff/appimagemanager.git
# cd appimagemanager

# 2. Install build dependencies
# sudo apt update
# sudo apt install -y python3-venv python3-pip build-essential dpkg-dev libxcb-cursor0

# 3. Run the script
chmod +x build_and_install.sh
./build_and_install.sh # Might ask for sudo password

# 4. Launch!
appimagemanager
```

**3. Running Directly from Source (For Development/Testing)**

```bash
# 1. Clone the repository (if not done already)
# git clone https://github.com/tunjayoff/appimagemanager.git
# cd appimagemanager

# 2. Create a virtual environment
# python3 -m venv .venv
# source .venv/bin/activate

# 3. Install requirements
# pip install -r requirements.txt

# 4. Run
# python -m appimagemanager
```

---

## 📖 Usage

1.  Launch AppImage Manager.
2.  **Install Tab:**
    *   Click "Browse..." or drag & drop an `.AppImage` file.
    *   Select an installation mode (Copy files, System-wide, Custom, or Register Only).
    *   Click "Install AppImage".
3.  **Manage Tab:**
    *   View, search, and sort your managed AppImages.
    *   Select an app and click "Run Application" or "Uninstall Selected".
    *   Click "Scan for Leftovers" to find untracked installations.
4.  **Settings Tab:**
    *   Change language or theme.

For more detailed information, please refer to the **[Full Documentation](documentation/index.md)**.

---

## ⚙️ Configuration & Data

*   **Settings:** Stored in `~/.config/appimage-manager/settings.json`
*   **App Database:** Stored in `~/.config/appimage-manager/installed.json`
*   **Logs:** Recorded in `~/.config/appimage-manager/appimage-manager.log`

(See the **[Configuration Guide](documentation/configuration.md)** for details.)

---

## 🌍 Translations

UI text is stored in `resources/translations_<lang>.json`. Contributions for new languages are welcome!

(See the **[Localization Guide](documentation/localization.md)** for details.)

---

## 🤝 Contributing

Contributions, issues, and feature requests are welcome. Please check the repository issues page.

---

## 📜 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## 🙏 Acknowledgements

- Built with Python 3 and PyQt6.
- Inspired by other Linux package and AppImage management tools.

---

## 🇹🇷 Türkçe

**AppImage dosyalarınızı Ubuntu 24.04 ve üzeri sistemlerde kolayca yönetin! (diğer debian tabanlı dağıtımlarda da çalışabilir)**

AppImage Manager, AppImage uygulamalarını yüklemek, düzenlemek, başlatmak ve kaldırmak için kullanıcı dostu bir arayüz sunar. Uygulamaları sistem menünüze entegre eder ve düzeni korumanıza yardımcı olur.

---

## ✨ Özellikler

*   **Zahmetsiz Kurulum:**
    *   AppImage'ları sistem geneline veya sadece kullanıcınıza özel kurun.
    *   Özel bir kurulum konumu seçin.
    *   `.AppImage` dosyalarını pencereye sürükleyip bırakın.
    *   "Sadece Kaydet" modu: Orijinal dosyayı taşımadan AppImage'ları yöneticiye ve menüye ekleyin.
*   **Basit Yönetim:**
    *   Yönetilen tüm AppImage'ları sıralanabilir bir listede görüntüleyin.
    *   Uygulamalarınızı arayın ve filtreleyin.
    *   Uygulamaları doğrudan yöneticiden başlatın.
*   **Temiz Kaldırma:**
    *   Kurulu AppImage'ları ve menü girdilerini tek tıkla kaldırın.
    *   Kaldırma sonrası isteğe bağlı artık yapılandırma dosyası taraması.
*   **Kurtarma ve Temizlik:**
    *   "Artıkları Tara" özelliği, veritabanı tarafından unutulmuş (örn. veritabanı kaybı sonrası) kurulumları bulup kaldırmanıza yardımcı olur.
*   **Kullanıcı Dostu Arayüz:**
    *   Hızlı geçiş düğmeli Açık ve Koyu temalar.
    *   Çoklu dil desteği (İngilizce ve Türkçe dahil).

---

## 🚀 Kurulum

AppImage Manager'ı kurmanın üç ana yolu vardır:

**1. Hazır Derlenmiş `.deb` Dosyası ile (En Kolay ve Kullanıcılar için Önerilen)**

Eğer bir sürümden `.deb` dosyası mevcutsa, bu en basit yöntemdir.

1.  **İndirme:** [Proje Sürümleri Sayfasına](https://github.com/tunjayoff/appimagemanager/releases) gidin ve en son `.deb` dosyasını indirin (örn. `appimagemanager_X.Y.Z_amd64.deb`).
2.  **GUI ile Kurulum:** Çoğu durumda, indirilen `.deb` dosyasına çift tıklamanız yeterlidir. Sisteminizin yazılım yükleyicisi açılmalı ve kurmanıza izin vermelidir (parolanızı girmeniz gerekebilir).
3.  **Terminal ile Kurulum (Alternatif):**
    ```bash
    # Dosyayı indirdiğiniz dizine gidin
    # cd ~/İndirilenler

    # Paketi kurun (gerçek dosya adıyla değiştirin)
    sudo dpkg -i appimagemanager_X.Y.Z_amd64.deb

    # Eksik bağımlılıklarla ilgili hatalar görürseniz, şunu çalıştırın:
    sudo apt --fix-broken install
    ```
4.  **Başlatma:** AppImage Manager'ı uygulama menünüzde bulun veya terminalde `appimagemanager` komutunu çalıştırın.

**2. Derleme ve Kurulum Betiği ile (Kaynaktan Derlemek İçin)**

Bu betik, uygulamayı kaynak koddan derler ve bir sistem paketi (`.deb`) olarak kurar. En son kodu sistem geneline kurmak istiyorsanız kullanışlıdır.

```bash
# 1. Clone the repository (if not done already)
# git clone https://github.com/tunjayoff/appimagemanager.git
# cd appimagemanager

# 2. Create a virtual environment
# python3 -m venv .venv
# source .venv/bin/activate

# 3. Install requirements
# pip install -r requirements.txt

# 4. Run
# python -m appimagemanager
```

**3. Doğrudan Kaynaktan Çalıştırma (Geliştirme/Test için)**

```bash
# 1. Clone the repository (if not done already)
# git clone https://github.com/tunjayoff/appimagemanager.git
# cd appimagemanager

# 2. Create a virtual environment
# python3 -m venv .venv
# source .venv/bin/activate

# 3. Install requirements
# pip install -r requirements.txt

# 4. Run
# python -m appimagemanager
```

---

## 📖 Kullanım

1.  AppImage Manager'ı başlatın.
2.  **Kur Sekmesi:**
    *   "Gözat..." tıklayın veya bir `.AppImage` dosyasını sürükleyip bırakın.
    *   Bir kurulum modu seçin (Dosyaları kopyala, Sistem geneli, Özel veya Sadece Kaydet).
    *   "AppImage Kur" tıklayın.
3.  **Yönet Sekmesi:**
    *   Yönetilen AppImage'larınızı görüntüleyin, arayın ve sıralayın.
    *   Bir uygulama seçin ve "Uygulamayı Çalıştır" veya "Seçileni Kaldır" tıklayın.
    *   Takip edilmeyen kurulumları bulmak için "Artıkları Tara" tıklayın.
4.  **Ayarlar Sekmesi:**
    *   Dili veya temayı değiştirin.

Daha ayrıntılı bilgi için lütfen **[Tam Dokümantasyona](documentation/index.md)** bakın.

---

## ⚙️ Yapılandırma ve Veriler

*   **Ayarlar:** `~/.config/appimage-manager/settings.json` içinde saklanır
*   **Uygulama Veritabanı:** `~/.config/appimage-manager/installed.json` içinde saklanır
*   **Günlükler:** `~/.config/appimage-manager/appimage-manager.log` içine kaydedilir

(Ayrıntılar için **[Yapılandırma Kılavuzuna](documentation/configuration.md)** bakın.)

---

## 🌍 Çeviriler

UI metinleri `resources/translations_<lang>.json` içinde saklanır. Yeni diller için katkılar memnuniyetle karşılanır!

(Ayrıntılar için **[Yerelleştirme Kılavuzuna](documentation/localization.md)** bakın.)

---

## 🤝 Katkıda Bulunma

Katkılar, sorun bildirimleri ve özellik istekleri memnuniyetle karşılanır. Lütfen deponun sorunlar (issues) sayfasını kontrol edin.

---

## 📜 Lisans

Bu proje MIT Lisansı altında lisanslanmıştır - ayrıntılar için [LICENSE](LICENSE) dosyasına bakın.

---

## 🙏 Teşekkürler

- Python 3 ve PyQt6 ile oluşturulmuştur.
- Diğer Linux paket ve AppImage yönetim araçlarından esinlenilmiştir. 