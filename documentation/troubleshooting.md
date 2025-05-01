# Troubleshooting Guide: Common Issues & Solutions

<p align="center">
  <img src="../resources/icon.png" alt="AppImage Manager Logo" width="100" />
</p>

<p align="center"><strong>Resolving Common Issues with AppImage Manager</strong></p>

This guide helps you identify and resolve common problems you might encounter while using AppImage Manager.

## 📋 Table of Contents

- [Installation Issues](#installation-issues)
- [System-wide Installation Problems](#system-wide-installation-problems)
- [Application Integration Issues](#application-integration-issues)
- [Database and Management Issues](#database-and-management-issues)
- [Log File Analysis](#log-file-analysis)
- [Getting Additional Help](#getting-additional-help)

## Installation Issues

### AppImage File Not Executable

**Problem:** Error indicating the AppImage file isn't executable.

**Solution:**
1. In your file manager, right-click the AppImage file
2. Select "Properties"
3. Go to "Permissions" tab
4. Check "Allow executing file as program"
5. Try installing again

Alternatively, use the terminal:
```bash
chmod +x /path/to/your/file.AppImage
```

### Missing Dependencies

**Problem:** Error about missing dependencies (rare).

**Solution:**
Make sure you have libfuse2 installed:
```bash
sudo apt update
sudo apt install libfuse2
```

## System-wide Installation Problems

### Single Password Prompt Failing

**Problem:** The system-wide installation fails after entering your password.

**Solution:**
1. Ensure you entered your password correctly
2. Check the log file for specific errors related to the sudo helper script
3. Verify you have administrator privileges on your system

**Note:** AppImage Manager now uses a bundled script approach requiring only one password prompt, making the process more reliable than previous versions that requested multiple prompts.

## Application Integration Issues

### Incorrect Application Names

**Problem:** Applications appear with unusual or truncated names in your menu.

**Solution:**
This issue has been fixed in recent versions with improved name sanitization. If you still encounter this:
1. Uninstall the affected application
2. Update to the latest version of AppImage Manager
3. Reinstall the application

### Missing Application Icons

**Problem:** Applications appear without icons or with generic icons.

**Solution:**
1. Ensure the "Extract application icon" option is enabled during installation
2. Try reinstalling the application
3. If the problem persists, the AppImage might not contain a proper icon

## Database and Management Issues

### Missing Applications in Manager

**Problem:** Applications you installed previously don't appear in the manager.

**Solution:**
1. The database file (`~/.config/appimage-manager/installed.json`) might be corrupted or deleted
2. Use the "Scan for Leftovers" tool:
   - Click "Tools" → "Scan for Leftovers"
   - The application will find any installed AppImages not in the database
   - You can choose to register or remove them

### Application Shows as "Missing"

**Problem:** An app in the "Manage Apps" list has the status "Missing".

**Solution:**
- The application files might have been moved or deleted outside the manager
- Select the app and click "Uninstall" to remove it from the database
- If you still need the application, reinstall it from the original AppImage

## Log File Analysis

For more detailed troubleshooting, check the application log file:

**Log Location:**
```
~/.config/appimage-manager/appimage-manager.log
```

**How to Read It:**
- Open with any text editor
- Look for `ERROR` entries that might indicate what went wrong
- Check timestamps to find entries related to your recent actions

**Terminal Commands for Logs:**
```bash
# View the entire log
cat ~/.config/appimage-manager/appimage-manager.log

# View only the last 50 lines
tail -n 50 ~/.config/appimage-manager/appimage-manager.log

# Watch the log in real-time (press Ctrl+C to stop)
tail -f ~/.config/appimage-manager/appimage-manager.log
```

## Getting Additional Help

If you're still having trouble after trying these solutions:

1. Make sure you're using the latest version of AppImage Manager
2. Include the following information when reporting issues:
   - Your Ubuntu version (e.g., Ubuntu 24.04)
   - AppImage Manager version (found in "About" page)
   - Relevant error messages from the log file
   - Steps to reproduce the problem

---

<p align="center">
  <em>For information about application settings, see the <a href="configuration.md">Configuration Guide</a></em>
</p> 