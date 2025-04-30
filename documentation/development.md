# Development Guide: A Look Under the Hood

This part of the guide is for people who like to tinker with code, maybe want to help improve AppImage Manager, or want to build the application themselves from the source code instead of using the pre-built `.deb` file. If you're not interested in programming, you can probably skip this section!

## Getting Ready to Code

To work with the application's code, you need a few tools on your computer:

1.  **Must-Haves:**
    *   **Git:** A tool used to copy and manage source code from websites like GitHub.
    *   **Python:** The programming language the app is written in (version 3.10 or newer is best). You likely already have this.
    *   **`python3-venv`:** A tool that comes with Python for creating "virtual environments" (like a clean workspace for each project). You might need to install it separately (`sudo apt install python3-venv`).
    *   **`pip`:** Python's tool for installing other helper code libraries.
2.  **Get the Code:** Use Git to download the source code. Open your **Terminal** and type:
    ```bash
    # Find the correct web address (URL) for the project's code!
    git clone https://github.com/your-username/appimagemanager.git 
    # Go into the folder that was just created
    cd appimagemanager 
    ```
3.  **Create a Safe Workspace (Virtual Environment):** This is super important! It keeps the helper libraries needed for *this* project separate from other Python stuff on your computer. In the Terminal, type:
    ```bash
    # Create the environment (named '.venv')
    python3 -m venv .venv
    # Activate it (turn it on for this terminal session)
    source .venv/bin/activate 
    ```
    You should see `(.venv)` appear at the beginning of your Terminal prompt, showing the workspace is active.
4.  **Install Helper Libraries (Dependencies):** Now, tell Python to install all the extra code pieces AppImage Manager needs. In the Terminal (make sure `(.venv)` is still showing), type:
    ```bash
    pip install -r requirements.txt
    ```
    This reads the `requirements.txt` file and installs things like `PyQt6` (for the user interface) into your `.venv` workspace.

## Running the App from Code

If you followed the steps above, running the app is easy! Just type this in the Terminal (while the `.venv` workspace is active):

```bash
python -m appimagemanager
```

This tells Python to find the main starting point inside the `appimagemanager` folder and run the application.

## How the Code is Organized (Folder Map)

Understanding where things are helps if you want to change something:

*   **`appimagemanager/`**: This is the main folder holding the Python code.
    *   `main.py`: The boss file! It starts the app, creates the main window, handles themes.
    *   `config.py`: Stores important settings like folder paths, default options.
    *   `utils.py`: Contains general helper tools, like setting up the log file.
    *   `i18n.py`: Manages the language translations (see **[Localization Guide](./localization.md)**).
    *   `db_manager.py`: Takes care of reading and writing the list of apps in `installed.json`.
    *   `appimage_utils.py`: The real workhorse! Has the code for installing, registering, uninstalling AppImages, and getting info out of them.
    *   `sudo_helper.py`: Handles asking for your password (using `pkexec`) when the app needs administrator permission.
    *   `widgets.py`: Contains code for any special custom buttons or controls used in the interface (like the cool theme toggle switch).
    *   `pages/`: A sub-folder containing a separate file for each main screen (or "page") you see in the app: `install_page.py`, `manage_page.py`, `settings_page.py`, `about_page.py`.
    *   `resources/`: A sub-folder for non-code things.
        *   `translations_*.json`: The language dictionary files.
        *   `icons/`: Image files for icons (though some icons come from your system).
*   `build_and_install.sh`: A script (a list of commands) to automatically build the `.deb` installation file.
*   `requirements.txt`: The shopping list of helper Python libraries needed.
*   `LICENSE`: The legal information about how you can use the code.
*   `README.md`: The front page description of the project.
*   `documentation/`: Where these help files live!

## Making the `.deb` Installer File

If you want to create the `.deb` file yourself (the one used in the "Easiest Way" installation):

1.  **Tools Needed:** Building `.deb` files requires some special tools used for packaging software on Debian/Ubuntu systems.
    ```bash
    # Install tools if you don't have them
    sudo apt update
    sudo apt install build-essential devscripts debhelper 
    ```
2.  **Run the Script:** Go to the main project folder in your Terminal and run:
    ```bash
    bash build_and_install.sh
    ```

This script does a bunch of things automatically:

*   Creates temporary folders (`build/`, `dist/`, etc.).
*   Copies the Python code, language files, icons, and special files (like the menu shortcut `.desktop` file) into a specific structure that Debian understands.
*   Creates control files that tell the system what the package is, what version, and what other software it needs.
*   Uses a tool called `dpkg-deb` to bundle everything into the final `.deb` file (usually puts it in the main project folder or a `dist/` folder).
*   It might even ask if you want to install the `.deb` file it just created.

Look inside the `build_and_install.sh` file itself if you want to see the exact commands it runs.

## Want to Help Improve the App?

That's great! Most open-source projects welcome help. Look at the main `README.md` file or a file named `CONTRIBUTING.md` (if it exists) in the project's code repository. These files usually explain the best way to report bugs you find, suggest new ideas, or share code changes you've made. 