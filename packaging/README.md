# Packaging

This directory contains packaging files for distributing AppImage Manager.

## Available Packages

| Distribution | Format | Directory |
|-------------|--------|-----------|
| Arch Linux | AUR (PKGBUILD) | [arch/](arch/) |
| Ubuntu/Debian | DEB | Use `build_and_install.sh` |

## Installation

### Arch Linux (AUR)

```bash
# Using yay
yay -S appimagemanager

# Using paru
paru -S appimagemanager

# Manual
git clone https://aur.archlinux.org/appimagemanager.git
cd appimagemanager
makepkg -si
```

### Ubuntu / Debian

Download the `.deb` package from the [Releases](https://github.com/tunjayoff/appimagemanager/releases) page:

```bash
# Download and install
wget https://github.com/tunjayoff/appimagemanager/releases/latest/download/appimagemanager_1.0.1_amd64.deb
sudo dpkg -i appimagemanager_*.deb
sudo apt --fix-broken install
```

Or build from source:

```bash
git clone https://github.com/tunjayoff/appimagemanager.git
cd appimagemanager
./build_and_install.sh
```

### Other Distributions

Install via pip:

```bash
pip install appimagemanager
```

Or run from source:

```bash
git clone https://github.com/tunjayoff/appimagemanager.git
cd appimagemanager
pip install -r requirements.txt
python -m appimagemanager
```
