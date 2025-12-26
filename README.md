# AppImage Manager

<p align="center">
  <img src="resources/icon.png" alt="AppImage Manager Logo" width="150" />
</p>

<p align="center">
  <strong>A powerful, user-friendly AppImage management solution for Linux</strong>
</p>

<p align="center">
  <a href="LICENSE"><img src="https://img.shields.io/badge/License-MIT-blue.svg" alt="License: MIT"></a>
  <img src="https://img.shields.io/badge/Platform-Linux-green.svg" alt="Platform: Linux">
  <img src="https://img.shields.io/badge/Python-3.8+-yellow.svg" alt="Python: 3.8+">
</p>

---

## 📖 Overview

AppImage Manager simplifies the process of installing, organizing, and managing AppImage applications on Linux. With an intuitive interface and powerful features, it helps you keep your AppImage collection organized and integrated with your desktop environment.

### 📸 Screenshot

![Main Window](images/screenshot.png)

---

## ✨ Key Features

- **Multiple Installation Methods**
  - User-level installation
  - System-wide installation (with single sudo prompt)
  - Custom location installation
  - Registration without extraction

- **Effortless Management**
  - Centralized application dashboard
  - Easy launching of installed applications
  - Clean uninstallation process
  - Leftover detection and cleanup

- **Desktop Integration**
  - Automatic menu entries creation
  - Application icon extraction
  - Improved name sanitization for better desktop integration

- **User-Friendly Interface**
  - Light and dark themes
  - Multi-language support (English and Turkish)
  - Intuitive navigation

---

## 🚀 Installation

### Arch Linux (AUR)

```bash
# Using yay
yay -S appimagemanager

# Using paru
paru -S appimagemanager
```

### Ubuntu / Debian (.deb Package)

Download the `.deb` package from the [Releases](https://github.com/tunjayoff/appimagemanager/releases) page:

```bash
wget https://github.com/tunjayoff/appimagemanager/releases/latest/download/appimagemanager_1.0.0_all.deb
sudo dpkg -i appimagemanager_*.deb
sudo apt --fix-broken install
```

### Other Distributions (pip)

```bash
pip install appimagemanager
```

### From Source

```bash
git clone https://github.com/tunjayoff/appimagemanager.git
cd appimagemanager
pip install -r requirements.txt
python -m appimagemanager
```

For more details, see the [Installation Guide](documentation/installation.md).

---

## 📝 Usage

### Installing AppImages

1. Launch AppImage Manager
2. Click the "Add" button or navigate to the installation section
3. Browse for or drag-and-drop your AppImage file
4. Choose your installation method:
   - User installation (for current user only)
   - System-wide installation (for all users)
   - Custom location installation
   - Register only (without extraction)
5. Click "Install" to complete the process

### Managing Applications

- View all installed applications in the management section
- Launch applications with a single click
- Remove applications when no longer needed
- Scan for leftover files from previous installations

For more detailed usage instructions, see the [Usage Guide](documentation/usage.md).

---

## ⚙️ Configuration

AppImage Manager stores its configuration and data in `~/.config/appimage-manager/`:

- `settings.json`: Application preferences
- `installed.json`: Database of managed applications
- `appimage-manager.log`: Activity log

For more information about configuration options, see the [Configuration Guide](documentation/configuration.md).

---

## 📋 System Requirements

- **Operating System**: 
  - Arch Linux (via AUR)
  - Ubuntu / Debian (via .deb package)
  - Any Linux (via pip or from source)
- **Python**: 3.8 or higher (3.10+ recommended)
- **Dependencies**: PyQt6, python-packaging, libfuse2 (recommended)
- **Disk Space**: ~10 MB (plus space for your applications)

---

## 📦 Packaging

Distribution-specific packaging files are available in the [packaging/](packaging/) directory:

| Distribution | Package Format | Status |
|-------------|----------------|--------|
| Arch Linux | AUR | ✅ Available |
| Ubuntu/Debian | DEB | ✅ Available |
| Any Linux | pip | ✅ Available |

---

## 📚 Documentation

Comprehensive documentation is available in the `documentation` directory:

- [Installation Guide](documentation/installation.md)
- [Usage Guide](documentation/usage.md)
- [Configuration Guide](documentation/configuration.md)
- [Troubleshooting Guide](documentation/troubleshooting.md)
- [Localization Guide](documentation/localization.md)
- [Theming Guide](documentation/theming.md)
- [Developer Guide](documentation/development.md)

---

## 🌍 Localization

AppImage Manager supports multiple languages. Currently available:

- English (en)
- Turkish (tr)

To contribute a new translation, see the [Localization Guide](documentation/localization.md).

---

## 👨‍💻 Development

Interested in contributing to AppImage Manager? Check out the [Developer Guide](documentation/development.md) for information on:

- Setting up a development environment
- Project structure
- Building the application
- Contribution guidelines

---

## 📜 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## 👤 Author

- **Tuncay EŞSİZ** - [@tunjayoff](https://github.com/tunjayoff)
- Email: tuncayessiz9@gmail.com

---

## 🇹🇷 Türkçe

AppImage Manager, Linux sistemlerinde AppImage uygulamalarını yönetmek için güçlü ve kullanıcı dostu bir çözümdür. Arch Linux, Debian/Ubuntu ve diğer Linux dağıtımlarıyla uyumludur.

### Özellikler

- Kolay kurulum (kullanıcı seviyesi, sistem geneli, özel konum)
- Tek sudo istemi ile sistem genelinde kurulum
- Merkezi uygulama yönetimi
- Masaüstü entegrasyonu
- Açık ve koyu tema desteği
- Türkçe ve İngilizce dil desteği

Ayrıntılı bilgi için [belgeler klasörüne](documentation/index.md) bakabilirsiniz. 