# Theming Guide: Changing AppImage Manager's Look

Do you prefer your apps bright and light, or cool and dark? AppImage Manager lets you choose! This guide explains how to change the application's theme (its colors and overall look).

## How to Switch Themes

There are two easy ways to change the look:

1.  **Using the Settings Page:**
    *   Click "Settings" in the sidebar menu on the left.
    *   Look for the "Appearance" or "Theme" section.
    *   You'll see options like "Light Theme" and "Dark Theme". Click the one you want!
    *   Click "Save" if there's a save button.
2.  **Using the Quick Toggle Button (☀️/🌙):**
    *   Look at the very top of the main window (in the toolbar area).
    *   If you see a little button that looks like a **Sun (☀️)** or a **Moon (🌙)**, that's the quick theme toggle!
    *   Clicking this button instantly switches between the Light and Dark themes.

**Important Note:** Sometimes, after changing the theme, not *everything* might update its look instantly. For the new theme to apply perfectly everywhere, it's often best to **close and reopen** the AppImage Manager application.

## How Do Themes Work? (A Peek Behind the Scenes)

It's like changing the paint and wallpaper in a room!

1.  **Basic Rules (The Blueprint):** The application has a set of basic rules (called a stylesheet) that describe how things *should* look in general. For example, "buttons should have rounded corners" or "the background should be color X". This blueprint uses placeholders for the actual colors, like `%BACKGROUND_COLOR%` or `%BUTTON_COLOR%`.
2.  **Color Palettes (Paint Cans):** There are two lists of colors defined in the code:
    *   `LIGHT_THEME`: Contains all the bright color values (like white backgrounds, dark text).
    *   `DARK_THEME`: Contains all the dark color values (like dark grey backgrounds, light text).
3.  **Applying the Paint:**
    *   When you start the app or choose a theme, the app looks at which theme you picked (Light or Dark).
    *   It takes the basic blueprint (the stylesheet).
    *   It replaces all the color placeholders (like `%BACKGROUND_COLOR%`) with the actual color codes from the chosen palette (Light or Dark).
    *   This finished set of rules with real colors is then applied to the whole application, changing how everything looks.
    *   The app also remembers your choice (light or dark) by saving it in the `settings.json` file (see the **[Configuration Guide](./configuration.md)**), so it starts with your preferred theme next time.

## Can I Make My Own Theme?

Right now, the application only comes with the built-in Light and Dark themes. There isn't a menu option to pick custom colors for buttons or text.

If you are comfortable with programming, you *could* technically change the color codes directly inside the `LIGHT_THEME` and `DARK_THEME` lists within the `main.py` source code file to create your own look. However, this is an advanced step and not recommended for regular users. 