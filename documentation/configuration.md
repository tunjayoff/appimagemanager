# Configuration Guide

<p align="center">
  <img src="../resources/icon.png" alt="AppImage Manager Logo" width="100" />
</p>

<p align="center"><strong>Understanding AppImage Manager's Configuration System</strong></p>

This guide explains how AppImage Manager stores and manages configuration settings and application data.

## 📋 Table of Contents

- [Configuration Directory](#configuration-directory)
- [Settings Management](#settings-management)
- [Application Database](#application-database)
- [Log Files](#log-files)
- [Advanced Configuration](#advanced-configuration)

## Configuration Directory

AppImage Manager stores all its configuration data in a dedicated directory in your home folder:

```
~/.config/appimage-manager/
```

This directory contains several important files:

| File | Purpose |
|------|---------|
| `settings.json` | Stores your application preferences |
| `installed.json` | Contains the database of managed AppImages |
| `appimage-manager.log` | Records application activity and errors |

## Settings Management

### Using the Settings Interface

The recommended way to change AppImage Manager's behavior is through the Settings page:

1. Click "Settings" in the left sidebar
2. Adjust your preferences:
   - **Language**: Choose your preferred interface language
   - **Theme**: Select between Light and Dark themes
   - **Default Installation Mode**: Set your preferred installation type
3. Click "Save" to apply changes

**Note**: Some settings (like language and theme) require restarting the application to take full effect.

### Settings File Structure

The `settings.json` file uses JSON format to store preferences:

```json
{
    "language": "en",
    "default_install_mode": "user",
    "dark_mode": false
}
```

Key settings include:

- `language`: Two-letter language code (e.g., "en" for English, "tr" for Turkish)
- `default_install_mode`: Preferred installation type ("user", "system", or "custom")
- `dark_mode`: Theme preference (true = dark theme, false = light theme)

If this file is deleted, the application will recreate it with default settings.

## Application Database

### Understanding the Database File

The `installed.json` file is crucial for tracking your AppImages. It contains a list of all applications managed by AppImage Manager.

Each application entry contains metadata such as:

```json
{
    "id": "unique_identifier",
    "name": "Application Name",
    "version": "1.0",
    "description": "Application description",
    "categories": ["Category1", "Category2"],
    "icon_path": "/path/to/icon.png",
    "desktop_file_path": "/path/to/desktop/file.desktop",
    "executable_path": "/path/to/executable",
    "original_appimage_path": "/path/to/original.AppImage",
    "install_location": "/path/to/installation",
    "install_date": "2024-05-01 10:30:00",
    "management_type": "installed"
}
```

**Important fields:**

- `id`: Unique identifier for the application
- `management_type`: How the application is managed:
  - `"installed"`: Application is extracted and installed
  - `"registered"`: Application is registered without extraction

### Database Recovery

If your database becomes corrupted or is accidentally deleted:

1. Use the "Scan for Leftovers" feature to find installed applications
2. The application will create a new database file if needed
3. You'll need to re-add any applications that were previously managed

## Log Files

AppImage Manager maintains a detailed log file that records all operations:

```
~/.config/appimage-manager/appimage-manager.log
```

This log is valuable for troubleshooting and contains:

- `INFO`: Normal operations
- `WARNING`: Potential issues
- `ERROR`: Operation failures
- `DEBUG`: Detailed diagnostic information

See the [Troubleshooting Guide](./troubleshooting.md) for more information on using log files.

## Advanced Configuration

**Warning**: Directly editing configuration files is not recommended unless you understand JSON format. Incorrect syntax can prevent the application from starting properly.

If you need to manually edit configuration files:

1. Make a backup of the file first
2. Use a text editor that preserves UTF-8 encoding
3. Validate JSON syntax before saving
4. Restart AppImage Manager after making changes

For most users, using the built-in Settings interface is the safest approach.

---

<p align="center">
  <em>For help with specific issues, see the <a href="troubleshooting.md">Troubleshooting Guide</a></em>
</p> 