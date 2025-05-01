# Usage Guide: How to Use AppImage Manager

Okay, you've installed AppImage Manager! 🎉 Now let's learn how to use it to handle your AppImage files.

## Exploring the Main Window

When you open AppImage Manager, you'll see a window with a few main parts:

1.  **Sidebar (Navigation Menu):** This is the menu on the left side. It has buttons like "Install", "Manage Apps", "Settings", and "About". Clicking these buttons changes what you see in the main part of the window.
2.  **Content Area (Main View):** This is the biggest part of the window in the middle/right. It shows the details for whichever section you selected in the sidebar. For example, if you click "Install", this area shows options for adding new AppImages.
3.  **Toolbar (Quick Buttons):** Sometimes there's a small bar at the very top with quick action buttons. The most common one is the **Theme Toggle** (looks like a sun or moon ☀️/🌙) to quickly switch between light and dark modes.
4.  **Status Bar (Message Area):** This is a small area at the very bottom. It shows messages about what the app is doing, like "Installing..." or "Ready" or if there was an error.

## Adding a New AppImage (The "Install" Page)

This is where you tell AppImage Manager about a new AppImage you downloaded.

1.  **Choose Your AppImage File:** You need to tell the manager *which* AppImage file you want to add. You have a few ways:
    *   **"Select AppImage" Button:** Click this big button. A window will pop up allowing you to browse through your computer's folders (like Downloads, Documents, etc.) and pick the `.AppImage` file you want.
    *   **"Recent AppImages" Button:** If you see this button, it's a shortcut! It looks in your Downloads and Desktop folders for any AppImages you might have put there recently. Click it, and a small menu will appear listing them for quick selection.
    *   **Drag and Drop:** You can also just find the AppImage file in your computer's file manager (the window you use to see your files and folders) and simply drag it with your mouse and drop it anywhere onto the AppImage Manager window.
2.  **See App Info:** After you select a file, AppImage Manager will try to peek inside the AppImage and find the application's name and version number. It will show this information in the "Application Information" box so you can double-check it's the right app.
3.  **Pick How to Manage It:** This is the most important step! You need to decide *how* AppImage Manager should handle this AppImage. You have these choices:
    *   ✅ **"For this user only (~/.local)":** (This is usually the best choice for most people). This option treats the AppImage like a normal installed program, but only for your user account. It takes the contents out of the AppImage file and neatly puts them in a hidden folder in your home directory (`~/.local/share/appimagemanager/apps/`). It also creates shortcuts in your application menu and handles icons, so it feels just like any other app you installed. It *doesn't* need your password.
    *   💻 **"System-wide (/opt) - Requires Root!":** This option also installs the AppImage like a normal program, but it makes it available for *all* user accounts on the computer. Because it needs to put files in shared system folders (like `/opt/appimagemanager/apps/` and `/usr/share/applications/`), it **needs administrator permission**. You will be asked for your password to allow this.
    *   📁 **"Custom location":** This option also installs the AppImage by taking its contents out, but *you* choose exactly which folder to put them in. You'll need to click "Browse..." to pick a folder. Make sure it's a folder you have permission to write files into. The app will still try to add menu shortcuts.
    *   📎 **"Add to Manager (Keep Original)":** (This is the "Register Only" option). This is different! It **does not** take the files out of the AppImage. It leaves your original `.AppImage` file exactly where you saved it. It just *registers* the file with AppImage Manager so it shows up in the list, and it tries to create a shortcut in your application menu so you can launch it easily. **Important:** If you choose this option, you **must not move or delete** the original `.AppImage` file, or the shortcut will stop working!
4.  **Click "Install":** Once you've selected your file and chosen the management mode, click the big "Install" button (even if you chose "Add to Manager", the button text might still say "Install"). Watch the progress bar and the status bar at the bottom to see what's happening (like "Extracting...", "Registering...", "Installation successful!").

## Looking After Your Apps (The "Manage Apps" Page)

This page shows you a list of all the AppImage applications that AppImage Manager knows about (the ones you installed or registered).

*   **The List:** You'll see a table with information about each app:
    *   Its icon
    *   Its name
    *   Its version number
    *   Where it's installed (or the path to the original file if registered)
    *   Its status (like "OK" if everything seems fine, or "Missing" if the files can't be found).
*   **Find Apps (Search):** If you have many apps, you can type in the "Search" box at the top to quickly find an app by its name or version.
*   **Change Order (Sort):** Click on the titles at the top of the columns (like "Application Name" or "Version") to sort the list alphabetically or by version number.
*   **Update List (Refresh):** Click the "Refresh List" button if you think the list might be out of date (though it usually updates automatically).
*   **Find Lost Installations (Scan for Leftovers):** This is a helpful tool if you suspect there might be old AppImage installations managed by this tool that are no longer listed (perhaps if the database file was lost or corrupted). Clicking this button scans the standard installation locations (`~/.local/share/appimagemanager/apps` and `/opt/appimage-manager/apps`). It looks for application directories that contain a special marker file (`.aim_managed`) but are *not* listed in the current database. It will present a list of these potential "leftover" installations and allow you to select and remove them. This helps clean up disk space from installations the manager forgot about.
*   **Run an App:** Click on an app in the list to select it, then click the "Run Application" button to start it.
*   **Remove an App (Uninstall):** Click on an app in the list to select it, then click the "Uninstall Selected" button. A confirmation message will ask if you are sure.
    *   If the app was **installed** (using "For this user", "System-wide", or "Custom"), AppImage Manager will remove the files it created, the menu shortcuts, and icons. If it was a system-wide install, it might ask for your password again.
    *   If the app was only **registered** ("Add to Manager (Keep Original)"), uninstalling mainly removes it from the list and deletes the menu shortcut and icon it created. It **does not delete your original `.AppImage` file** – you have to do that yourself if you want to.
    *   ✨ **Bonus - Leftover *Configuration* Check!** After uninstalling an app, AppImage Manager tries to be extra tidy! It looks in common places where programs sometimes leave behind settings or temporary files (like `~/.config`, `~/.cache`). If it finds anything that looks like it belonged to the app you just removed, it will show you a list and ask if you want to delete those leftover files too. Be sure to look carefully before deleting!

## Changing Settings (The "Settings" Page)

This page lets you change a few things about how AppImage Manager works:

*   **Language:** Pick a different language for the menus and buttons (you might need to restart the app for the change to show everywhere).
*   **Theme:** Choose between the "Light Theme" (bright background) and "Dark Theme" (dark background) (you might need to restart the app for this too).
*   **Default Install Choice:** You can choose which option ("For this user only", "System-wide", etc.) is automatically selected when you first add a new AppImage on the Install page.

(Want more details on settings? Check the **[Configuration Guide](./configuration.md)**).

## Learning About the App (The "About" Page)

This page just shows information about AppImage Manager itself, like its version number, who made it, the license, and some technical details about your system.

## Quick Theme Switch (The ☀️/🌙 Button)

Remember the toolbar at the top? If you see a button that looks like a sun or a moon, you can click it to instantly switch between the Light and Dark themes without having to go to the Settings page! (You might still need to restart the app for the theme to look perfect everywhere). 