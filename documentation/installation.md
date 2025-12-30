# Installation Guide

<p align="center">
  <img src="../resources/icon.png" alt="AppImage Manager Logo" width="100" />
</p>

<p align="center"><strong>Setting Up AppImage Manager on Your System</strong></p>

This guide walks you through the process of installing AppImage Manager on your Linux system.

## 📋 Table of Contents

- [System Requirements](#system-requirements)
- [Installation Methods](#installation-methods)
  - [Method 1: Using the .deb Package](#method-1-using-the-deb-package)
  - [Method 2: Using the Build Script](#method-2-using-the-build-script)
  - [Method 3: Running from Source](#method-3-running-from-source)
- [Uninstallation](#uninstallation)
- [User Data Handling](#user-data-handling)

## System Requirements

Before installing AppImage Manager, ensure your system meets these requirements:

- **Operating System**: Arch Linux, Ubuntu, Debian, or other Linux distributions
- **Dependencies**:
  - Python 3.8 or higher (Python 3.10+ recommended)
  - PyQt6 (installed automatically with packages)
  - fuse2 (recommended for maximum compatibility)

To install fuse on Arch Linux:

```bash
sudo pacman -S fuse2
```

To install fuse on Ubuntu/Debian:

```bash
sudo apt update
sudo apt install libfuse2
```

## Installation Methods

AppImage Manager can be installed in multiple ways, depending on your preferences and distribution.

### Method 1: Arch Linux (AUR)

This is the recommended method for Arch Linux users:

```bash
# Using yay
yay -S appimagemanager

# Using paru
paru -S appimagemanager

# Manual installation
git clone https://aur.archlinux.org/appimagemanager.git
cd appimagemanager
makepkg -si
```

### Method 2: Using the .deb Package (Debian/Ubuntu)

This is the recommended method for Ubuntu and Debian-based systems:

1. **Download the .deb package**:
   - Find the latest release on the [GitHub Releases](https://github.com/tunjayoff/appimagemanager/releases) page
   - Look for a file named `appimagemanager_X.Y.Z_amd64.deb`

2. **Install via graphical interface**:
   - Double-click the downloaded .deb file
   - Your system's package installer will open
   - Click "Install" and enter your password when prompted

3. **Or install via terminal**:
   ```bash
   sudo dpkg -i /path/to/appimagemanager_X.Y.Z_amd64.deb
   
   # If you encounter dependency errors:
   sudo apt --fix-broken install
   ```

4. **Launch the application**:
   - Find AppImage Manager in your application menu, or
   - Run `appimagemanager` in a terminal

### Method 3: Using the Build Script (Debian/Ubuntu)

If you prefer to build from source but still want the convenience of a .deb package:

1. **Install build dependencies**:
   ```bash
   sudo apt update
   sudo apt install -y git python3-venv python3-pip build-essential dpkg-dev libxcb-cursor0
   ```

2. **Clone the repository**:
   ```bash
   git clone https://github.com/tunjayoff/appimagemanager.git
   cd appimagemanager
   ```

3. **Run the build script**:
   ```bash
   chmod +x build_and_install.sh
   ./build_and_install.sh
   ```

   This script will:
   - Set up a Python virtual environment
   - Install required dependencies
   - Build the application
   - Create and install the .deb package

4. **Launch the application**:
   - Find AppImage Manager in your application menu, or
   - Run `appimagemanager` in a terminal

### Method 3: Running from Source

This method is ideal for development or testing:

1. **Install dependencies**:
   ```bash
   sudo apt update
   sudo apt install -y git python3-venv python3-pip
   ```

2. **Clone the repository**:
   ```bash
   git clone https://github.com/tunjayoff/appimagemanager.git
   cd appimagemanager
   ```

3. **Create and activate a virtual environment**:
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   ```

4. **Install Python dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

5. **Run the application**:
   ```bash
   python -m appimagemanager
   ```

For more information on development, see the [Developer Guide](development.md).

## Uninstallation

### Removing a Package Installation

If you installed using Method 1 or Method 2:

```bash
sudo apt remove appimagemanager
```

### Removing a Source Installation

If you installed using Method 3:

1. If the virtual environment is active, deactivate it:
   ```bash
   deactivate
   ```

2. Delete the cloned repository:
   ```bash
   rm -rf /path/to/appimagemanager
   ```

## User Data Handling

AppImage Manager stores user settings and application data in:

```
~/.config/appimage-manager/
```

### Important Notes:

- **Uninstalling the application does not remove this directory**
- Your settings and list of managed applications remain intact
- If you want to completely remove all data, manually delete this directory:

```bash
# Only run this if you want to delete ALL settings and application data!
rm -rf ~/.config/appimage-manager
```

---

<p align="center">
  <em>To learn how to use AppImage Manager, see the <a href="usage.md">Usage Guide</a></em> 