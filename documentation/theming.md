# Theming Guide

<p align="center">
  <img src="../resources/icon.png" alt="AppImage Manager Logo" width="100" />
</p>

<p align="center"><strong>Customizing AppImage Manager's Appearance</strong></p>

This guide explains how to change AppImage Manager's visual theme and understand how theming works.

## 📋 Table of Contents

- [Changing Themes](#changing-themes)
- [Theme Implementation](#theme-implementation)
- [Custom Theming](#custom-theming)

## Changing Themes

AppImage Manager offers two visual themes: Light and Dark. You can switch between them in two ways:

### Via Settings Page

1. Click "Settings" in the left sidebar
2. Navigate to the "Appearance" section
3. Select your preferred theme (Light or Dark)
4. Click "Save"
5. Restart the application for the changes to fully apply

### Via Quick Toggle

AppImage Manager includes a convenient theme toggle button:

1. Look for the Sun (☀️) or Moon (🌙) icon in the application toolbar
2. Click this button to instantly switch between Light and Dark themes
3. Restart the application to ensure all elements update properly

**Note**: Some interface elements may not immediately reflect the theme change until the application is restarted.

## Theme Implementation

AppImage Manager implements theming through a stylesheet-based approach:

1. The application defines a base stylesheet with placeholders for color values
2. Two color palettes are defined:
   - **Light Theme**: Bright backgrounds with dark text
   - **Dark Theme**: Dark backgrounds with light text
3. When a theme is selected, the application:
   - Substitutes the appropriate color values into the stylesheet
   - Applies the completed stylesheet to the interface
   - Saves the preference in the configuration file

This approach allows for consistent styling across the entire application while maintaining flexibility.

## Custom Theming

While AppImage Manager currently only provides Light and Dark themes without built-in customization options, advanced users familiar with the codebase could modify the theme definitions.

The color palettes are defined in the `main.py` file as `LIGHT_THEME` and `DARK_THEME` dictionaries. Modifying these values would allow for custom color schemes, but this is not officially supported and should be approached with caution.

---

<p align="center">
  <em>For information about other customization options, see the <a href="configuration.md">Configuration Guide</a></em>
</p> 