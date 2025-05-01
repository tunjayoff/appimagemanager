# Configuration Guide: How AppImage Manager Remembers Things

Like many apps, AppImage Manager needs to remember your preferences (like language or theme) and keep track of the AppImages you've added. It does this using special text files. This guide explains where these files are and what they do (but you usually don't need to change them yourself!).

## Where Does It Keep Its Stuff? (The Configuration Directory)

AppImage Manager stores all its important information in a hidden folder inside your personal home folder. The location is:

```
~/.config/appimage-manager/
```

(The `~` symbol means your home folder, and the `.` at the beginning of `.config` means it's usually hidden from normal view in your file manager unless you tell it to show hidden files.)

Inside this `appimage-manager` folder, you'll find a few key files:

*   `settings.json`: This file remembers your choices from the Settings page.
*   `installed.json`: This is like the app's address book, listing all the AppImages it's managing.
*   `appimage-manager.log`: This is the activity log, like a diary where the app writes down what it's doing, especially if something goes wrong (see **[Troubleshooting Guide](./troubleshooting.md)**).

## Changing Settings (The Easy Way - Settings Page)

The best and safest way to change how AppImage Manager behaves is by using the **Settings** page inside the application itself (click "Settings" in the left sidebar):

*   **Language:** Choose the language you want the app's text to appear in. You'll need to restart the app after changing this.
*   **Appearance (Theme):** Pick between the "Light Theme" (bright) or "Dark Theme" (dark). You'll also need to restart the app for this change to look right everywhere.
*   **Default Installation Mode:** Remember the choices when adding an AppImage ("For this user only", "System-wide", etc.)? This setting lets you pick which one is automatically selected by default when you go to the Install page. ("Add to Manager (Keep Original)" usually can't be the default).

When you make changes here and click "Save" or close the window, the app automatically updates the `settings.json` file for you.

## Looking Inside the Files (Advanced - Be Careful!)

**Heads up!** It's usually **not a good idea** to open and edit these `.json` files directly with a text editor unless you are very comfortable with how they work. Making a mistake (like deleting a comma or a quote) can stop the app from working correctly!

### `settings.json` (Your Preferences)

This file uses a simple format called JSON to store your choices. It looks something like this:

```json
{
    "language": "en",
    "default_install_mode": "user",
    "dark_mode": false
}
```

*   `"language"`: Stores the two-letter code for your chosen language (like "en" for English, "tr" for Turkish).
*   `"default_install_mode"`: Remembers which installation type is the default ("user", "system", or "custom").
*   `"dark_mode"`: Is `true` (meaning yes) if you picked the dark theme, and `false` (meaning no) if you picked the light theme.

If you ever delete this file, the app will just create a new one with the standard default settings the next time you start it.

### `installed.json` (The App List / Database)

This is the most important file for keeping track of your AppImages. It's also a JSON file, and it basically contains one big list called `"installed_apps"`. Each item in the list is an object representing one AppImage you've added.

Here's what the information for **one** app might look like inside that list:

```json
{
    "id": "some_random_letters_and_numbers",
    "name": "CoolApp",
    "version": "1.0",
    "description": "This app does cool things.",
    "categories": ["Graphics", "Utility"],
    "icon_path": "/home/user/.local/share/icons/hicolor/256x256/apps/coolapp_icon.png",
    "desktop_file_path": "/home/user/.local/share/applications/coolapp.desktop",
    "executable_path": "/home/user/.local/bin/CoolApp",
    "original_appimage_path": "/home/user/Downloads/CoolApp-x86_64.AppImage",
    "install_location": "/home/user/.local/share/appimagemanager/apps/coolapp_some_random",
    "install_date": "2024-05-01 10:30:00",
    "management_type": "installed"
}
```

Let's break that down:

*   `id`: A unique code the manager gives each app so it doesn't mix them up.
*   `name`, `version`, `description`, `categories`: Information about the app, usually read from inside the AppImage.
*   `icon_path`: Where the app's icon image is stored so it can be shown in the menu.
*   `desktop_file_path`: The location of the special shortcut file that makes the app appear in your main application menu.
*   `executable_path`: *How* to run the app. If it was **installed**, this points to a shortcut (symlink). If it was **registered**, this points directly to your original AppImage file.
*   `original_appimage_path`: Where the `.AppImage` file you originally selected is located on your computer.
*   `install_location`: If the app was **installed**, this is the folder where its contents were unpacked. If it was only **registered**, this might be empty or `null`.
*   `install_date`: When you added the app.
*   `management_type`: Very important! Tells how the app is being handled:
    *   `"installed"`: Means the app's contents were unpacked and put into system folders (either user-local, system-wide, or custom). Corresponds to the "Install (Copy files...)", "System-wide", or "Custom Location" options.
    *   `"registered"`: Means the original AppImage file is being used, and the manager just created menu shortcuts/icons. Corresponds to the "Add to Manager (Keep Original)" option.

The "Manage Apps" page reads this file to show you the list. When you install or uninstall apps, AppImage Manager updates this file automatically. 