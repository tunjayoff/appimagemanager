# AppImage Manager: Comprehensive Guide

<p align="center">
  <img src="../resources/icon.png" alt="AppImage Manager Logo" width="150" />
</p>

<p align="center"><strong>Powerful, User-Friendly AppImage Management Solution for Linux</strong></p>

## 🌟 What is AppImage Manager?

AppImage Manager is a modern, user-friendly tool developed to manage AppImage applications on Linux. With just a single click, you can install, manage, and uninstall your AppImage files. It helps you keep all your applications organized without the complexity of traditional package managers.

### 🚀 Why Use AppImage Manager?

AppImages are fantastic tools – they run without installing dependencies or modifying your system. However, managing them manually can become challenging:

- You might forget where you placed them
- Integrating them into your menu requires extra steps
- Tracking updates is cumbersome
- Clean uninstallation requires manual intervention

AppImage Manager solves all these issues and makes AppImage usage effortless.

## 📋 What's in This Documentation?

This guide is divided into the following sections:

| Section | Content |
|---------|---------|
| [**Installation**](installation.md) | How to install AppImage Manager on your system |
| [**Usage Guide**](usage.md) | Using basic and advanced features of the application |
| [**Configuration**](configuration.md) | Customizing AppImage Manager |
| [**Troubleshooting**](troubleshooting.md) | Common issues and their solutions |
| [**Localization**](localization.md) | Support for different languages |
| [**Theming**](theming.md) | Customizing the interface theme |
| [**Developer Guide**](development.md) | Technical details for contributors |

## ✨ Highlighted Features

- **One-Click Installation**: Securely and organizedly installs AppImage files into hidden folders
- **System-wide or User-level Installation**: Options for both system-wide and user-specific installations
- **Enhanced Desktop Integration**: Your applications automatically appear in the start menu
- **Single Sudo Instance**: System-wide installation and removal operations with just one sudo prompt (no more repeated sudo queries!)
- **Application Management**: Monitor and manage installed applications from a central location
- **Automatic Icon Management**: Icons for each application are automatically configured
- **Clean Removal**: Cleanly removes applications along with all their components
- **Multi-language Support**: Use in your local language
- **Light and Dark Themes**: Interface customization according to your preference

## 🎯 Target Audience

AppImage Manager is ideal for these users:

- 🖥️ Newcomers to Linux
- 🧙‍♂️ Experienced users wanting to keep system configuration simple and organized
- 🏢 System administrators wanting to standardize AppImages in multi-user environments

## 💻 System Requirements

- **Officially Supported**: Arch Linux, Ubuntu, Debian, and other Linux distributions
- **Package Formats**: AUR (Arch), DEB (Debian/Ubuntu), pip (universal)
- **Compatible With**: Most Linux distributions with Python 3.8+
- **Python**: Python 3.8 or higher
- **Dependencies**: PyQt6, fuse2 (or fuse3)
- **Disk Space**: Approximately 10 MB (you'll need more space for your applications)
- **RAM**: Minimum 50 MB

## 📊 Technical Summary

AppImage Manager is a Python and Qt-based application. It features a robust database system, error management, and application integration mechanism. It uses YAML or SQLite format for data storage and includes validation mechanisms for security.

## 🚀 Get Started!

Start experiencing AppImage Manager right away with the [installation guide](installation.md)!

---

<p align="center">
  <em>Developed, maintained, and lovingly crafted by AppImage Manager © 2024-2025</em><br>
  <small>Developer: Tuncay EŞSİZ (tunjayoff)</small>
</p>