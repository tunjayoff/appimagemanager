# appimagemanager

> Easily install, manage, and remove AppImage applications on Ubuntu 24.04, with full JSON-based multi-language support.

[![CI](https://github.com/tunjayoff/appimagemanager/actions/workflows/ci.yml/badge.svg)](https://github.com/tunjayoff/appimagemanager/actions)
[![PyPI version](https://badge.fury.io/py/appimagemanager.svg)](https://badge.fury.io/py/appimagemanager)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

GitHub: [https://github.com/tunjayoff/appimagemanager](https://github.com/tunjayoff/appimagemanager)

---

## 📸 Screenshots

![Main Window](docs/screenshot.png)

## Table of Contents

- [Description](#description)
- [Features](#features)
- [Installation](#installation)
- [Usage](#usage)
- [Configuration](#configuration)
- [Translations](#translations)
- [Theming](#theming)
- [Development & Testing](#development--testing)
- [Contributing](#contributing)
- [License](#license)
- [Acknowledgements](#acknowledgements)
- [Contact](#contact)

## Description

AppImage Manager is a user-friendly desktop application for Ubuntu 24.04 and above. It streamlines the process of installing, organizing, launching, and removing AppImage applications, offering both system-wide and per-user installations. With a dynamic PyQt6 interface, JSON-based multi-language support, and light/dark theming, it adapts seamlessly to your workflow.

## Features

- System-wide and per-user AppImage installations
- Discover, search, filter, and launch installed AppImages
- Create desktop shortcuts and menu entries automatically
- One-click uninstall with associated cleanup
- Real-time language switching without restart
- Light and dark themes with animated toggle
- Drag-and-drop support for easy installation

## Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/tunjayoff/appimagemanager.git
   cd appimagemanager
   ```
2. Install required dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Launch the application:
   ```bash
   python3 main.py
   ```

## Usage

After starting the app, use the sidebar to navigate:
- **Install**: Choose and install new AppImage files.
- **Manage**: Browse, search, and launch or remove installed apps.
- **Settings**: Configure language, theme, and defaults.
- **About**: View version, credits, and system info.

## Configuration

User settings (theme, language) are stored in `~/.config/appimage-manager/settings.json`. You can manually edit this file or use the Settings page in the UI.

## Translations

All UI strings reside in `resources/translations_<lang>.json`. To add a new language:
1. Copy an existing JSON file to `resources/translations_<new>.json`.
2. Translate each key-value pair.
3. Restart or switch language in-app.

## Theming

Toggle light/dark mode via the switch in the toolbar. Theme preferences are saved automatically.

## Development & Testing

Run unit tests with pytest:
```bash
pytest tests/
```
Lint with Flake8:
```bash
flake8 appimagemanager/
```

## Acknowledgements

- Built with PyQt6 and Python 3.
- Inspired by native Linux package managers.

## Contact

- Maintainer: [tunjayoff](https://github.com/tunjayoff)
- Repository: https://github.com/tunjayoff/appimagemanager

## English

`appimagemanager` is a tool for Ubuntu to easily install, manage, and remove AppImage applications.

### Features

- Install AppImages system-wide or for the current user
- List, search, and filter installed applications
- Create desktop entries and menu items
- Launch and uninstall applications directly from the manager
- Multi-language support (JSON-based translation files)

### Installation

```bash
# Clone the repository
git clone https://github.com/tunjayoff/appimagemanager.git
cd appimagemanager

# Install dependencies
pip install -r requirements.txt

# Run the application
python3 main.py
```

### Contributing

1. Fork the repository and create a branch (`git checkout -b feature/YourFeature`)
2. Commit your changes (`git commit -m "Add some feature"`)
3. Push to your branch (`git push origin feature/YourFeature`)
4. Open a Pull Request

### License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## Türkçe

`appimagemanager`, Ubuntu üzerinde AppImage uygulamalarını kolayca yüklemenize, yönetmenize ve kaldırmanıza yardımcı olan bir araçtır.

### Özellikler

- AppImage dosyalarını sistem geneline veya kullanıcı bazında kurma
- Yüklenen uygulamaların listelenmesi, arama ve filtreleme
- Masaüstü girdileri ve menü öğeleri oluşturma
- Uygulamaları doğrudan yönetici üzerinden başlatma ve kaldırma
- Çoklu dil desteği (JSON tabanlı çeviri dosyaları)

### Kurulum

```bash
# Depoyu klonlayın
git clone https://github.com/tunjayoff/appimagemanager.git
cd appimagemanager

# Gerekli paketleri yükleyin
pip install -r requirements.txt

# Uygulamayı çalıştırın
python3 main.py
```

### Katkıda Bulunma

1. Depoyu forkladıktan sonra kendi dalınızı oluşturun (`git checkout -b feature/Özellikiniz`)
2. Değişikliklerinizi commit edin (`git commit -m "Yeni özellik eklendi"`)
3. Branch'i pushlayın (`git push origin feature/Özellikiniz`)
4. Pull Request açın

### Lisans

Bu proje MIT lisansı ile lisanslanmıştır - detaylar için [LICENSE](LICENSE) dosyasına bakın. 