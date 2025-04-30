# appimagemanager

> Easily install, manage, and remove AppImage applications on Ubuntu 24.04, with full JSON-based multi-language support.

[![PyPI version](https://badge.fury.io/py/appimagemanager.svg)](https://badge.fury.io/py/appimagemanager)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

GitHub: [https://github.com/tunjayoff/appimagemanager](https://github.com/tunjayoff/appimagemanager)

---

## 📸 Screenshots

![Main Window](docs/screenshot.png)

## English

## Table of Contents

- [Description](#description)
- [Features](#features)
- [Installation](#installation)
- [Usage](#usage)
- [Configuration](#configuration)
- [Translations](#translations)
- [Theming](#theming)
- [Build & Installation Script](#build--installation-script)
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

## Build & Installation Script

A convenience script `build_and_install.sh` automates creating a standalone executable, packaging it into a Debian `.deb`, and installing it system-wide.

Prerequisites:
```bash
sudo apt update
sudo apt install -y python3-venv python3-pip build-essential dpkg-dev libxcb-cursor0
```

Usage:
```bash
chmod +x build_and_install.sh
./build_and_install.sh
# Then launch with:
appimagemanager
```

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

## Türkçe

## Açıklama
AppImage Manager, Ubuntu 24.04 ve üzeri için kullanıcı dostu bir masaüstü uygulamasıdır. AppImage uygulamalarının sistem çapında veya kullanıcı bazında yüklenmesi, düzenlenmesi, başlatılması ve kaldırılmasını kolaylaştırır. Dinamik PyQt6 arayüzü, JSON tabanlı çoklu dil desteği ve açık/koyu tema seçenekleriyle iş akışınıza sorunsuzca uyum sağlar.

## Özellikler

- Sistem çapında ve kullanıcı bazında AppImage yüklemeleri
- Yüklü AppImage'ları keşfetme, arama, filtreleme ve başlatma
- Masaüstü kısayolları ve menü girdileri otomatik oluşturma
- Tek tıklamayla kaldırma ve temizlik
- Yeniden başlatma gerektirmeden gerçek zamanlı dil değişimi
- Animasyonlu açık/kapalı tema geçişi
- Sürükle-bırak ile kolay yükleme

## Kurulum
1. Repoyu klonlayın:
   ```bash
   git clone https://github.com/tunjayoff/appimagemanager.git
   cd appimagemanager
   ```
2. Bağımlılıkları yükleyin:
   ```bash
   pip install -r requirements.txt
   ```
3. Uygulamayı başlatın:
   ```bash
   python3 main.py
   ```

## Kullanım
Uygulamayı başlattıktan sonra kenar çubuğunu kullanarak gezinin:
- **Install**: Yeni AppImage dosyalarını seçip yükleyin.
- **Manage**: Yüklü uygulamaları göz atın, arayın, başlatın veya kaldırın.
- **Settings**: Dil, tema ve varsayılanları yapılandırın.
- **About**: Sürüm, geliştirici ve sistem bilgilerini görüntüleyin.

## Yapılandırma
Kullanıcı ayarları `~/.config/appimage-manager/settings.json` içinde saklanır. Bu dosyayı elle düzenleyebilir veya UI üzerindeki Ayarlar sayfasını kullanabilirsiniz.

## Çeviriler
Tüm arayüz metinleri `resources/translations_<lang>.json` dosyalarında bulunur. Yeni dil eklemek için:
1. Var olan bir JSON dosyasını `translations_<new>.json` olarak kopyalayın.
2. Anahtar-değer çiftlerini çevirin.
3. Uygulamayı yeniden başlatın veya dil değiştirin.

## Tema
Araç çubuğundaki anahtar ile açık/kapalı tema arasında geçiş yapın. Tema tercihleri otomatik kaydedilir.

## Geliştirme & Test
Birim testlerini pytest ile çalıştırın:
```bash
pytest tests/
```
Flake8 ile lint kontrolü yapın:
```bash
flake8 appimagemanager/
```

## Teşekkürler
- PyQt6 ve Python 3 ile geliştirildi.
- Yerel Linux paket yöneticilerinden ilham alındı.

## İletişim
- Bakımcı: [tunjayoff](https://github.com/tunjayoff)
- Depo: https://github.com/tunjayoff/appimagemanager 