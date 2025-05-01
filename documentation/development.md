# Developer Guide

<p align="center">
  <img src="../resources/icon.png" alt="AppImage Manager Logo" width="100" />
</p>

<p align="center"><strong>Technical Documentation for Contributors</strong></p>

This guide is intended for developers who want to understand, modify, or contribute to the AppImage Manager codebase.

## 📋 Table of Contents

- [Development Environment Setup](#development-environment-setup)
- [Project Structure](#project-structure)
- [Running from Source](#running-from-source)
- [Building the Application](#building-the-application)
- [Key Components](#key-components)
- [Contribution Guidelines](#contribution-guidelines)

## Development Environment Setup

### Prerequisites

To work with the AppImage Manager codebase, you'll need:

- **Git**: For version control
- **Python**: Version 3.8 or higher (3.10+ recommended)
- **Python venv**: For creating virtual environments
- **Build tools**: For packaging (optional)

### Setting Up the Environment

1. **Clone the repository**
   ```bash
   git clone https://github.com/tunjayoff/appimagemanager.git
   cd appimagemanager
   ```

2. **Create a virtual environment**
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

## Project Structure

The AppImage Manager codebase is organized as follows:

```
appimagemanager/
├── appimagemanager/          # Main Python package
│   ├── __init__.py           # Package initialization
│   ├── main.py               # Application entry point
│   ├── config.py             # Configuration settings
│   ├── utils.py              # Utility functions
│   ├── i18n.py               # Internationalization
│   ├── db_manager.py         # Database management
│   ├── appimage_utils.py     # AppImage handling utilities
│   ├── sudo_helper.py        # Privileged operations helper
│   ├── widgets.py            # Custom UI components
│   ├── pages/                # UI pages
│   │   ├── install_page.py   # Installation UI
│   │   ├── manage_page.py    # Application management UI
│   │   ├── settings_page.py  # Settings UI
│   │   └── about_page.py     # About page UI
│   └── resources/            # Application resources
│       ├── translations_*.json  # Translation files
│       └── icons/            # UI icons
├── build_and_install.sh      # Build and installation script
├── requirements.txt          # Python dependencies
├── LICENSE                   # License information
├── README.md                 # Project overview
└── documentation/            # User documentation
```

## Running from Source

To run the application from source code:

```bash
# Ensure you're in the project root with the virtual environment activated
python -m appimagemanager
```

This launches the application directly from the source code, which is useful for development and testing.

## Building the Application

### Building a .deb Package

The included build script automates the creation of a Debian package:

1. **Install build dependencies**
   ```bash
   sudo apt update
   sudo apt install build-essential devscripts debhelper python3-setuptools
   ```

2. **Run the build script**
   ```bash
   chmod +x build_and_install.sh
   ./build_and_install.sh
   ```

The script performs the following tasks:
- Creates necessary build directories
- Compiles Python files
- Packages the application with proper dependencies
- Creates a .deb file in the project directory or a `dist/` subfolder

## Key Components

### Main Application (main.py)

The entry point for the application. It initializes the main window, sets up the theme system, and manages page navigation.

### AppImage Utilities (appimage_utils.py)

Handles core functionality related to AppImage files:
- Extracting metadata from AppImages
- Installing/registering AppImages
- Creating desktop integration files
- Managing file permissions
- Uninstalling applications

### Database Management (db_manager.py)

Manages the database of installed applications:
- Reading/writing the `installed.json` file
- Adding new application entries
- Removing application records
- Querying application information

### Internationalization (i18n.py)

Implements the translation system:
- Loading language files
- Translating UI strings
- Dynamically switching languages

### Sudo Helper (sudo_helper.py)

Handles operations requiring elevated privileges:
- Single-sudo approach for system-wide installations
- Secure execution of privileged commands
- Use of pkexec for authentication

## Contribution Guidelines

If you'd like to contribute to AppImage Manager:

1. **Fork the repository** on GitHub
2. **Create a new branch** for your feature or fix
3. **Implement your changes** following the existing code style
4. **Add or update tests** if applicable
5. **Ensure all tests pass**
6. **Submit a pull request** with a clear description of your changes

### Coding Standards

- Follow PEP 8 Python style guidelines
- Include docstrings for functions and classes
- Use type hints where appropriate
- Keep functions focused on a single responsibility
- Add comments for complex logic
- Update documentation when changing functionality

---

<p align="center">
  <em>For user-focused documentation, see the <a href="index.md">main documentation page</a></em>
</p> 