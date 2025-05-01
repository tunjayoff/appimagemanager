# Welcome to the AppImage Manager Help Center! 👋

Hello! This is the user guide for the AppImage Manager application. AppImage Manager is a helpful tool for your computer (especially Ubuntu version 24.04) that makes it easy to install, organize, and remove applications that come as ".AppImage" files.

**What is an AppImage?**

Think of an AppImage like a backpack for a computer program. Normally, when you install a program, its files get spread out in different places on your computer. An AppImage puts everything the program needs to run (all its files and parts) into just **one single file**. It's like packing everything for a trip into one bag! This means you often don't need to "install" the program in the traditional way; you can just double-click the AppImage file to run it.

**What Does AppImage Manager Do?**

While AppImage files are cool because they are self-contained, sometimes they don't fit perfectly into your system. They might not show up in your main application menu like other programs, or their icons might look strange. That's where AppImage Manager comes in to help!

This application takes the AppImage files you choose and does the following:

*   It can **install** them like a normal program. This means it carefully takes the contents out of the AppImage backpack and puts them in the right places on your computer (either just for you, system-wide, or in a custom location), creating menu shortcuts and icons so they feel like any other app.
*   Or, it can just **register** them. This means it leaves the original AppImage file (the backpack) wherever you put it, but it still adds a shortcut to your application menu so you can easily find and launch it.
*   It helps you **manage** all the AppImages you've installed or registered in one convenient place.
*   It lets you easily **uninstall** AppImages you no longer need and even helps **clean up** any leftover configuration files they might have left behind.
*   It can scan for and help you remove **leftover installations** if the manager somehow forgets about apps that are still installed (e.g., if its database is lost).

This guide will walk you through all the features of the application, step by step.

## What's Inside This Guide?

You can click on the links below to jump to the topic you're interested in:

*   **[Installation Guide](./installation.md):**
    *   Explains how to get AppImage Manager onto your computer.
    *   Tells you what you need *before* you install (like the correct Ubuntu version).
    *   Shows the different ways you can install it (including the build script).
*   **[Usage Guide](./usage.md):**
    *   Shows you around the main screen and explains what the buttons do.
    *   Gives step-by-step instructions on how to pick an AppImage file and choose whether to install or register it.
    *   Explains how to manage the apps you've added (running them, removing them, scanning for leftovers).
    *   Describes how to find and delete any leftover configuration files after uninstalling an app.
*   **[Settings and Configuration](./configuration.md):**
    *   Explains the options in the Settings menu (like changing the language or theme).
    *   Tells you about the hidden files the app uses to save your settings and list of apps (`settings.json`, `installed.json`) - you usually don't need to touch these!
*   **[Themes (Look and Feel)](./theming.md):**
    *   Shows how to switch between the Light (bright) and Dark (dimmed) look for the application.
    *   Briefly explains how this theme switching works behind the scenes.
*   **[Language Support (Translation)](./localization.md):**
    *   Explains how the application can be shown in different languages.
    *   Tells you how you could help translate the app into a new language if you wanted to.
*   **[For Developers](./development.md):**
    *   This section is a bit more technical. It's for people interested in the programming code.
    *   It explains how to get the app's code, run it, understand how it's organized, and build the installation package (.deb).
*   **[Troubleshooting (Fixing Problems)](./troubleshooting.md):**
    *   Lists common problems you might run into when using the app and how to solve them.
    *   Explains how to use the "Scan for Leftovers" feature to recover from a lost database.
    *   Explains how to find the app's activity log file, which can help figure out problems if you need to ask for help.

We hope this guide helps you enjoy using AppImage Manager!