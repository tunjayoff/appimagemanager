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

AppImage Manager is designed for Ubuntu 24.04 (and other Debian-based distributions). Three installation methods are available:

### Method 1: Using the .deb Package (Recommended)

1. Download the latest release from the [Releases Page](https://github.com/tunjayoff/appimagemanager/releases)
2. Install via graphical interface:
   - Double-click the downloaded .deb file
   - Follow the prompts to install

   OR via terminal:
   ```bash
   sudo dpkg -i appimagemanager_*.deb
   sudo apt --fix-broken install  # If needed
   ```

### Method 2: Using the Build Script

```bash
# Install dependencies
sudo apt update
sudo apt install -y git python3-venv python3-pip build-essential dpkg-dev libxcb-cursor0

# Clone the repository
git clone https://github.com/tunjayoff/appimagemanager.git
cd appimagemanager

# Run the build script
chmod +x build_and_install.sh
./build_and_install.sh
```

### Method 3: Running from Source

```bash
# Install dependencies
sudo apt update
sudo apt install -y git python3-venv python3-pip

# Clone the repository
git clone https://github.com/tunjayoff/appimagemanager.git
cd appimagemanager

# Create and activate virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install Python dependencies
pip install -r requirements.txt

# Run the application
python -m appimagemanager
```

For more detailed installation instructions, see the [Installation Guide](documentation/installation.md).

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

- **Operating System**: Ubuntu 24.04 (officially supported) or other Debian-based distributions
- **Package Format**: Available as .deb package only (officially)
- **Python**: 3.8 or higher (3.10+ recommended)
- **Dependencies**: PyQt6, libfuse2 (recommended)
- **Disk Space**: ~10 MB (plus space for your applications)

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

AppImage Manager, Linux sistemlerinde AppImage uygulamalarını yönetmek için güçlü ve kullanıcı dostu bir çözümdür. Ubuntu 24.04 ve diğer Debian tabanlı dağıtımlar için tasarlanmıştır.

### Özellikler

- Kolay kurulum (kullanıcı seviyesi, sistem geneli, özel konum)
- Tek sudo istemi ile sistem genelinde kurulum
- Merkezi uygulama yönetimi
- Masaüstü entegrasyonu
- Açık ve koyu tema desteği
- Türkçe ve İngilizce dil desteği

Ayrıntılı bilgi için [belgeler klasörüne](documentation/index.md) bakabilirsiniz. 