# Localization Guide

<p align="center">
  <img src="../resources/icon.png" alt="AppImage Manager Logo" width="100" />
</p>

<p align="center"><strong>Using and Contributing to Multi-Language Support</strong></p>

This guide explains how AppImage Manager handles different languages and how you can contribute translations.

## 📋 Table of Contents

- [Changing Language](#changing-language)
- [Translation System Overview](#translation-system-overview)
- [Contributing Translations](#contributing-translations)
- [Testing Translations](#testing-translations)
- [Translation Guidelines](#translation-guidelines)

## Changing Language

AppImage Manager offers multiple language options that can be changed through the Settings interface:

1. Click "Settings" in the left sidebar
2. In the "Language" section, select your preferred language
3. Click "Save"
4. Restart the application to apply the change

Currently supported languages include:
- English (en)
- Turkish (tr)

## Translation System Overview

AppImage Manager uses a straightforward JSON-based translation system:

### Dictionary Files

Each language has its own dictionary file located in the application resources directory:
- `translations_en.json` (English)
- `translations_tr.json` (Turkish)
- etc.

### Translation Mechanism

The application uses a key-based translation strategy:

1. Instead of hardcoding text, the code references translation keys
2. The translation system looks up the key in the appropriate language file
3. If the key exists, the translated text is displayed
4. If the key is missing, the system falls back to English
5. If the key doesn't exist in any language file, the key itself is displayed

#### Example:

English Dictionary (`translations_en.json`):
```json
{
    "app_name": "AppImage Manager",
    "btn_install": "Install"
}
```

Turkish Dictionary (`translations_tr.json`):
```json
{
    "app_name": "AppImage Yöneticisi",
    "btn_install": "Kur"
}
```

The code references these keys rather than direct text, enabling seamless language switching.

## Contributing Translations

You can help translate AppImage Manager into your language by following these steps:

### Creating a New Language File

1. Determine your language's ISO code (e.g., "fr" for French, "de" for German)
2. Copy the English dictionary file (`translations_en.json`)
3. Rename it to `translations_<language_code>.json` (e.g., `translations_fr.json`)
4. Translate the values (right side) while preserving the keys (left side)

### Translation Guidelines

- **Only translate values**, never modify the keys
- Preserve any formatting placeholders (e.g., `{0}`, `{app_name}`)
- Maintain any HTML tags if present
- Ensure your file uses UTF-8 encoding to support special characters
- Add an entry for your language's name in its native form:
  ```json
  "language_name": "Français"
  ```

### JSON Format Rules

- Each entry should follow this format: `"key": "translated value"`
- Every line except the last one must end with a comma
- All text must be enclosed in double quotes
- Special characters in strings must be escaped properly

## Testing Translations

To test your translation:

1. Place your translation file in the application's resources directory
2. Restart the application
3. Go to Settings and select your language
4. Restart again to apply
5. Navigate through all screens to verify your translations

### Common Issues

- **Untranslated Elements**: May indicate missing translation keys
- **Formatting Problems**: Check for missing placeholders
- **Application Crashes**: Verify JSON syntax (missing commas, quotes)

## Submitting Your Translation

Once you've created and tested your translation:

1. Make sure your JSON file has valid syntax
2. Submit it to the project according to the contribution guidelines (usually via a pull request on GitHub)

---

<p align="center">
  <em>For information about other customization options, see the <a href="configuration.md">Configuration Guide</a></em>
</p> 