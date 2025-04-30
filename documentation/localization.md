# Localization Guide: Speaking Your Language!

AppImage Manager tries to be friendly and speak different languages! This is called "localization". This guide explains how the app knows what language to use and how you could even help teach it a new one.

## How Does the App Know What Language to Use?

It's like the app has different dictionaries for different languages.

1.  **The Dictionary Files (`translations_*.json`):** Inside the application's code, there's a special folder (`appimagemanager/resources/`). This folder contains files named like `translations_en.json` (for English), `translations_tr.json` (for Turkish), and maybe others.
    *   Each file is like a dictionary for one language. It contains a list of special code words (called "keys") and the matching word or phrase in that specific language.
    *   **Example (English dictionary `translations_en.json`):**
        ```json
        {
            "app_name": "AppImage Manager", 
            "btn_install": "Install"
        }
        ```
    *   **Example (Turkish dictionary `translations_tr.json`):**
        ```json
        {
            "app_name": "AppImage Yöneticisi", 
            "btn_install": "Kur"
        }
        ```
2.  **The Translator Helper (`i18n.py`):** The app has a helper module that acts like a translator. When the app needs to show some text (like a button label or a menu item):
    *   It doesn't use the English text directly in its code.
    *   Instead, it tells the translator helper the special **key** for the text it wants (e.g., `"btn_install"`).
    *   The translator helper looks at which language you selected in the Settings.
    *   It opens the dictionary file for that language (e.g., `translations_tr.json`).
    *   It finds the key (`"btn_install"`) in the dictionary and gets the matching translated word (`"Kur"`).
    *   It gives that translated word back to the main app to display on the screen.
3.  **What if a Translation is Missing?**
    *   The app always uses English as a backup. If the translator helper can't find a key in your selected language's dictionary, it will automatically look for it in the English dictionary (`translations_en.json`).
    *   If it can't even find the key in the English dictionary (maybe it's a very new button), it will usually just display the key itself (like `btn_install`) as a last resort, and it might make a note in the log file.
4.  **Updating the Screen (`retranslateUi`):** When you change the language in the Settings page, the app needs to tell all the visible buttons and labels to ask the translator helper for their text again using the *new* language dictionary. Many parts of the app have a special function called `retranslateUi` that does exactly this.

## How to Help Translate AppImage Manager (Adding a New Language)

Do you speak a language that AppImage Manager doesn't support yet? You can help translate it! Here's how:

1.  **Find the Language Code:** Every language has a short code (usually two letters, based on a standard called ISO 639-1). For example, German is `de`, French is `fr`, Spanish is `es`.
2.  **Copy the English Dictionary:**
    *   Find the application's code folder. Inside it, go to the `appimagemanager/resources/` subfolder.
    *   Find the file `translations_en.json`.
    *   Make a **copy** of this file.
3.  **Rename Your Copy:** Rename the copied file using the language code you found in step 1. It should look like `translations_<your_code>.json`. For example, if you are translating to German, rename it to `translations_de.json`.
4.  **Translate!**
    *   Open your new `translations_<your_code>.json` file with a plain text editor (like Notepad on Windows, TextEdit on Mac, or Gedit/Kate on Linux). Make sure the editor saves in **UTF-8** format (this is important for special characters).
    *   Now, go through the file line by line. For each line, you will see a "key" in quotes, then a colon `:`, then the English translation in quotes.
    *   **ONLY translate the English part** (the value after the colon). **DO NOT change the key** (the part before the colon).
    *   **Example:** Change this:
        ```json
        "btn_install": "Install",
        ```
        To this (for German):
        ```json
        "btn_install": "Installieren",
        ```
    *   **Be careful with JSON rules:** Make sure every line except the very last one inside the `{ }` ends with a comma (`,`). All text must be inside double quotes (`"`).
    *   **Language Name:** It's helpful to add a line near the beginning to specify the language's name in its own language, like this for German:
        ```json
        "language_name": "Deutsch",
        ```
5.  **Test Your Translation:**
    *   If you have the development setup (see **[Development Guide](./development.md)**), run the app (`python -m appimagemanager`).
    *   Go to Settings -> Language.
    *   Your new language should now appear in the list!
    *   Select it and Save.
    *   Restart the application.
    *   Click through all the pages and menus. Does everything look correct in the new language?
6.  **Share Your Work:** If you translated the file and want to share it so everyone can use it, you'll need to send the new `translations_<your_code>.json` file back to the project developers. Check the project's main page (like on GitHub) for instructions on how to contribute.

**Things to Watch Out For:**

*   **Save as UTF-8:** This encoding helps make sure special characters in different languages display correctly.
*   **JSON Rules:** One missing comma or quote can stop the file from working.
*   **Placeholders:** Sometimes you'll see things like `{app_name}` or `{0}` inside the English text. These are placeholders where the app will insert dynamic information (like the actual name of an app). Make sure you keep these placeholders exactly as they are in your translation!
    *   Example English: `"status_installing": "Installing {app_name}..."`
    *   Example German: `"status_installing": "Installiere {app_name}..."` 