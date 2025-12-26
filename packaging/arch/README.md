# AUR Package: appimagemanager

**AUR Page:** https://aur.archlinux.org/packages/appimagemanager

## Installation

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

## Maintainer Notes

### Updating the Package

1. Update `pkgver` in PKGBUILD
2. Generate new checksums:
   ```bash
   updpkgsums
   ```
3. Regenerate .SRCINFO:
   ```bash
   makepkg --printsrcinfo > .SRCINFO
   ```
4. Commit and push:
   ```bash
   git add PKGBUILD .SRCINFO
   git commit -m "Update to version X.Y.Z"
   git push
   ```

### Testing the Build

```bash
makepkg -si
```
