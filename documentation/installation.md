# Installation Guide: Getting AppImage Manager Ready!

This part of the guide will show you how to put AppImage Manager on your computer. It works best with Ubuntu version 24.04, but might work on similar systems too.

## Before You Start: What You Need

Think of this like gathering ingredients before cooking! You need a few things on your computer first:

*   **Computer Operating System:** You need **Ubuntu 24.04**. Imagine it like needing the right game console to play a specific game. This app is made especially for Ubuntu 24.04.
*   **Python (The Engine):** Your computer needs a program called Python (version 3.10 or newer is best). Python is like the engine that makes AppImage Manager run. Ubuntu usually comes with Python, so you probably already have this.
*   **PyQt6 (The Look):** This is a helper program that lets AppImage Manager show windows, buttons, and text on your screen. If you use the recommended installation method below, this will usually be taken care of automatically.
*   **libfuse2 (Recommended Helper):** While AppImage Manager primarily works by *installing* AppImages (extracting their contents), which often bypasses the need for FUSE, having `libfuse2t64` installed is still **recommended** for maximum compatibility. Some AppImage operations (like quick metadata extraction) might still rely on it. The application may function without it but might show warnings or encounter issues with specific AppImages.
    *   **How to get libfuse2 (if you want it):**
        1.  Open the **Terminal** (it looks like a black box where you type commands).
        2.  Type `sudo apt update` and press Enter. (You might need to type your password).
        3.  Then, type `sudo apt install libfuse2t64` and press Enter.

## How to Install AppImage Manager

There are a few ways to get the app running:

### Method 1: Using the Pre-built `.deb` File (Easiest Way! 👍)

This is like getting a ready-made toy in a box. It's the simplest method for most users if a `.deb` file is provided.

1.  **Get the File:** Find the file named something like `appimagemanager_X.Y.Z_amd64.deb` (where X.Y.Z is the version number). You might find this file on the project's release page (e.g., on GitHub).
2.  **Install It:** Once you have the `.deb` file, you can usually just **double-click** it. Your computer should open a program (like "Software Install" or "GDebi Package Installer") that asks if you want to install it. Click "Install" and enter your password if asked.
    *   **Or, use the Terminal:**
        1.  Open the **Terminal**.
        2.  Type `sudo apt update` and press Enter.
        3.  Type `sudo dpkg -i ` (make sure to include the space after `-i`), then **drag the `.deb` file from your file manager into the Terminal window**. This will paste the full path to the file. Press Enter.
        4.  If the terminal mentions any errors about "dependencies", type `sudo apt --fix-broken install` and press Enter. This usually fixes it.

**What happens when you install this way?** The computer puts all the application's parts in the right system folders (like `/opt/appimagemanager` and `/usr/bin/appimagemanager`) and adds it to your application menu, just like a regular program.

### Method 2: Using the Build & Install Script (Recommended for Users Building from Source)

This method uses a script included with the source code to automatically build the app and install it using a `.deb` package, similar to Method 1 but done directly from the code.

1.  **Get the Code:** You'll need `git` installed. Open the **Terminal** and type:
    ```bash
    # Replace the URL with the actual web address of the code
    git clone https://github.com/tunjayoff/appimagemanager.git 
    cd appimagemanager 
    ```
2.  **Install Build Tools:** Make sure you have the necessary tools to build the package. In the Terminal, run:
    ```bash
    sudo apt update
    sudo apt install -y python3-venv python3-pip build-essential dpkg-dev libxcb-cursor0
    ```
3.  **Run the Script:** Execute the provided script:
    ```bash
    chmod +x build_and_install.sh
    ./build_and_install.sh
    ```
    This script will:
    *   Set up a Python virtual environment.
    *   Install required Python packages.
    *   Use `pyinstaller` to create a standalone executable.
    *   Package everything into a `.deb` file.
    *   Install the `.deb` file using `dpkg` (it might ask for your password).
4.  **Launch:** After the script finishes, you should be able to launch the application from your system menu or by typing `appimagemanager` in the Terminal.

### Method 3: Running Directly from Source (For Developers 🤓)

This is like building the toy yourself and playing with the parts. It's mainly for testing changes or developing the application.

1.  **Get the Code:** (Same as step 1 in Method 2).
    ```bash
    git clone https://github.com/tunjayoff/appimagemanager.git 
    cd appimagemanager 
    ```
2.  **Make a Safe Space (Virtual Environment):**
    ```bash
    python3 -m venv .venv
    source .venv/bin/activate 
    ```
3.  **Install the Parts (Dependencies):**
    ```bash
    pip install -r requirements.txt
    ```
4.  **Run the App!**
    ```bash
    python -m appimagemanager 
    ```
    The application should start directly from the code.

(If you want to know more about building and changing the code, look at the **[Development Guide](./development.md)**).

## How to Uninstall AppImage Manager

How you uninstall depends on how you installed it:

*   **If you used Method 1 (Pre-built `.deb`) or Method 2 (Build Script):**
    1.  Open the **Terminal**.
    2.  Type `sudo apt remove appimagemanager` and press Enter. Enter your password if asked.
*   **If you used Method 3 (Running Directly from Source):**
    1.  If the virtual environment (`.venv`) is active, type `deactivate` in the Terminal and press Enter.
    2.  Simply delete the `appimagemanager` folder that you cloned.

That's it! The main application parts will be removed.

**Important Note about User Data:** Uninstalling the application **does not** automatically delete your settings or the list of AppImages you managed. These are kept safe in `~/.config/appimage-manager/` in case you reinstall. If you are **sure** you want to delete everything, including your settings and app list, manually delete that folder:

```bash
# Only run this if you are SURE you want to delete all settings and data!
rm -rf ~/.config/appimage-manager
``` 