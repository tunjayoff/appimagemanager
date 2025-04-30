# Installation Guide: Getting AppImage Manager Ready!

This part of the guide will show you how to put AppImage Manager on your computer. It works best with Ubuntu version 24.04, but might work on similar systems too.

## Before You Start: What You Need

Think of this like gathering ingredients before cooking! You need a few things on your computer first:

*   **Computer Operating System:** You need **Ubuntu 24.04**. Imagine it like needing the right game console to play a specific game. This app is made especially for Ubuntu 24.04.
*   **Python (The Engine):** Your computer needs a program called Python (version 3.10 or newer is best). Python is like the engine that makes AppImage Manager run. Ubuntu usually comes with Python, so you probably already have this.
*   **PyQt6 (The Look):** This is a helper program that lets AppImage Manager show windows, buttons, and text on your screen. If you use the recommended installation method below, this will usually be taken care of automatically.
*   **libfuse2 (Optional Helper):** AppImage files sometimes need a helper called FUSE to run correctly, especially if you run them directly without *installing* them using AppImage Manager. AppImage Manager mostly avoids needing this by installing the apps properly. But, just in case, having `libfuse2t64` installed is a good idea for the best experience with all AppImages. The app might show a warning if it's missing, but it will still try to work.
    *   **How to get libfuse2 (if you want it):**
        1.  Open the **Terminal** (it looks like a black box where you type commands).
        2.  Type `sudo apt update` and press Enter. (You might need to type your password).
        3.  Then, type `sudo apt install libfuse2t64` and press Enter.

## How to Install AppImage Manager

There are two main ways to get the app running:

### Method 1: Using the `.deb` File (Easiest Way! 👍)

This is like getting a ready-made toy in a box. It's the simplest method for most users.

1.  **Get the File:** Find the file named something like `appimagemanager_1.0.0_amd64.deb`. You might find this file on the project's website or download page.
2.  **Install It:** Once you have the `.deb` file, you can usually just **double-click** it. Your computer should open a program (like "Software Install" or "GDebi Package Installer") that asks if you want to install it. Click "Install" and enter your password if asked.
    *   **Or, use the Terminal:**
        1.  Open the **Terminal**.
        2.  Type `sudo apt update` and press Enter.
        3.  Type `sudo dpkg -i ` (make sure to include the space after `-i`), then **drag the `.deb` file from your file manager into the Terminal window**. This will paste the full path to the file. Press Enter.
        4.  If the terminal mentions any errors about "dependencies", type `sudo apt --fix-broken install` and press Enter. This usually fixes it.

**What happens when you install this way?** The computer puts all the application's parts in the right system folders (like `/opt/appimagemanager` and `/usr/bin/appimagemanager`) and adds it to your application menu, just like a regular program.

### Method 2: Running from the Source Code (For Techies and Developers 🤓)

This is like building the toy yourself from parts. It's useful if you want to test the very latest (maybe unfinished) version or if you want to help improve the program's code.

1.  **Get the Code:** You'll need `git` installed. Open the **Terminal** and type:
    ```bash
    # Replace the URL with the actual web address of the code
    git clone https://github.com/your-username/appimagemanager.git 
    cd appimagemanager 
    ```
2.  **Make a Safe Space (Virtual Environment):** It's a good idea to keep the parts for this app separate from your other computer programs. In the Terminal, type:
    ```bash
    python3 -m venv .venv
    source .venv/bin/activate 
    ```
    (You should see `(.venv)` appear at the start of your terminal line).
3.  **Install the Parts (Dependencies):** In the Terminal (make sure you still see `(.venv)`), type:
    ```bash
    pip install -r requirements.txt
    ```
    This reads a list of required helper programs and installs them into your safe space.
4.  **Run the App!** In the Terminal (with `(.venv)` still active), type:
    ```bash
    python -m appimagemanager 
    ```
    The application should start!

(If you want to know more about building and changing the code, look at the **[Development Guide](./development.md)**).

## How to Uninstall AppImage Manager

If you installed using **Method 1 (the `.deb` file)** and want to remove the application:

1.  Open the **Terminal**.
2.  Type `sudo apt remove appimagemanager` and press Enter. Enter your password if asked.

That's it! The main application parts will be removed.

**Important Note:** Uninstalling **does not** automatically delete the settings or the list of AppImages you managed. These are kept safe in a hidden folder (`~/.config/appimage-manager/`) just in case you want to reinstall later. If you are **sure** you want to delete everything, including your settings and app list, you can manually delete that folder using the Terminal (be very careful with this command!):

```bash
# Only run this if you are SURE you want to delete all settings and data!
rm -rf ~/.config/appimage-manager
``` 