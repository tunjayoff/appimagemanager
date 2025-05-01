#!/bin/bash
# Clean script to remove previous Converseen installation

# Remove database entry
echo "Removing from database..."
rm -f ~/.config/appimage-manager/installed.json

# Remove system installation components
echo "Removing system installation files..."
sudo rm -rf /opt/appimage-manager-apps/conver_een_1.0
sudo rm -f /usr/local/bin/conver_een
sudo rm -f /usr/local/share/applications/appimagekit_conver_een.desktop

# Update system databases
echo "Updating system databases..."
sudo update-desktop-database /usr/local/share/applications
sudo ldconfig

echo "Cleanup complete! Now you can reinstall the application." 