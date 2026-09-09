# Localization coverage

The application UI localization now contains **30 locales and 713 canonical keys**. Persian (`fa`) and English (`en`) are bundled in the application; the remaining 28 locales are distributed as downloadable `.abl` language packs through the `langpacks-latest` GitHub Release.

Legacy literal UI labels are mapped to canonical localization keys before lookup. This covers older settings screens, including marker settings, vehicle settings, arrow settings, weather and battery widgets, route-card options, diagnostics, and other screens that previously could fall back to English.

The map renderer and map-provider labels are intentionally not translated by this UI layer. Map language remains locale/provider-controlled: for example, Iran uses Persian map labels, Iraq uses Arabic labels, and Türkiye uses Turkish labels.

Validation commands:

```bash
python3 tool/l10n/parity.py
python3 tool/l10n/build_release.py
python3 tests/validate_language_pack_contract.py --require-complete
flutter analyze --no-pub
```

The workflow `.github/workflows/langpacks-build.yml` rebuilds and publishes all 30 packs whenever localization source files change.
