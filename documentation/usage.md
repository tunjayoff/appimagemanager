# AppImage Manager: Usage Guide

<p align="center">
  <img src="../resources/icon.png" alt="AppImage Manager Logo" width="100" />
</p>

<p align="center"><strong>Mastering AppImage Manager's Features</strong></p>

This guide will walk you through all the features of AppImage Manager, from basic operations to advanced functionality.

## 📋 Table of Contents

- [Main Interface Overview](#main-interface-overview)
- [Installing AppImages](#installing-appimages)
- [Managing Installed Applications](#managing-installed-applications)
- [System vs User Installation](#system-vs-user-installation)
- [Single-Sudo System Operations](#single-sudo-system-operations)
- [Scanning for Leftovers](#scanning-for-leftovers)

## Main Interface Overview

When you launch AppImage Manager, you'll see a clean, intuitive interface divided into these main sections:

- **Left Sidebar**: Contains navigation menu for different sections
- **Main Content Area**: Displays the currently selected section's content
- **Top Actions Bar**: Contains action buttons specific to the current section
- **Status Bar**: Provides feedback on operations and application state

<p align="center">
  <em>The main interface showing installed applications</em>
</p>

## Installing AppImages

### Adding a New AppImage

1. Click the **Add** button in the toolbar
2. Browse and select your `.AppImage` file
3. Choose an installation method:

### Installation Methods

AppImage Manager offers four distinct methods for handling AppImage files:

- **User Installation**: Extracts and installs for the current user only
- **System-wide Installation**: Extracts and installs for all users on the system  
- **Custom Location Installation**: Extracts and installs to a location of your choice
- **Register Only**: Registers the AppImage in the application database and creates menu shortcuts without extraction

### Installation Options

When installing, depending on the method chosen, you'll have these options:

- **Integration Options**:
  - Desktop menu integration (on by default)
  - Create desktop shortcut
  - Extract application icon

## Managing Installed Applications

### Running Applications

Double-click any application in the list to launch it, or select it and click the **Run** button.

### Application Details

Select any application to see its details:
- Installation path
- Integration status
- Installation date
- Application icon

### Removing Applications

1. Select the application from the list
2. Click the **Remove** button
3. Confirm the removal
4. For system-wide applications, enter your password when prompted (only once)

## System vs User Installation

AppImage Manager supports two primary installation modes:

### User Installation
- Installed to: `~/.local/share/appimages/`
- Desktop integration: `~/.local/share/applications/`
- Only accessible to the current user
- No administrator privileges required

### System Installation
- Installed to: `/opt/appimages/`
- Desktop integration: `/usr/share/applications/`
- Available to all users on the system
- Requires administrator privileges (now with single-sudo feature)

## Single-Sudo System Operations

One of AppImage Manager's most convenient features is the single-sudo system operations. Previously, system-wide operations could require multiple password prompts, but now:

- One sudo permission request handles all necessary operations
- All system operations are bundled into a single privileged script
- This improves security and user experience
- Application names are properly sanitized for better desktop integration

## Scanning for Leftovers

If you've uninstalled applications outside of AppImage Manager or if database inconsistencies occur:

1. Click **Tools** → **Scan for Leftovers**
2. The application will scan common installation locations for AppImages
3. Any found AppImages not in the database will be listed
4. You can choose to:
   - **Register**: Add them to AppImage Manager's database
   - **Remove**: Properly uninstall them from your system
   - **Ignore**: Leave them as they are

---

<p align="center">
  <em>For more information about settings and customization, see the <a href="configuration.md">Configuration Guide</a></em> 