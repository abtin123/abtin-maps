"""Static contract checks for the redesigned Abtin Maps settings flow."""

from pathlib import Path


root = Path(__file__).resolve().parents[2]
settings = (root / "lib/features/settings/presentation/settings_screen.dart").read_text(encoding="utf-8")
appearance = (root / "lib/features/settings/presentation/appearance_settings_screen.dart").read_text(encoding="utf-8")
about = (root / "lib/features/settings/presentation/legal_screens.dart").read_text(encoding="utf-8")

assert "class _SettingsBrandHeader" in settings
assert "height: 228" in settings
assert "assets/images/abtinmaps_settings_logo.png" in settings
assert "const BottomNav(currentPage: NavKey.settings)" in settings
assert "AboutAppScreen" in settings

assert "String _openSection = '';" in appearance
assert "_openSection = 'appearance'" not in appearance

assert "abtinmaps@gmail.com" in about
assert "alimohammad1238@gmail.com" in about
assert "سید علی محمد موسوی" in about
assert "دستیار هوشمند" in about
assert "Icons.auto_awesome_rounded" in about
assert "package:url_launcher/url_launcher.dart" in about
assert "Uri(scheme: 'mailto', path: email)" in about

bottom_nav = (root / "lib/shared/widgets/bottom_nav.dart").read_text(encoding="utf-8")
search = (root / "lib/features/search/presentation/search_screen.dart").read_text(encoding="utf-8")
router = (root / "lib/core/router/app_router.dart").read_text(encoding="utf-8")
map_settings = (root / "lib/features/settings/presentation/map_settings_screen.dart").read_text(encoding="utf-8")
downloads = (root / "lib/features/downloads/downloads_root_screen.dart").read_text(encoding="utf-8")
voice = (root / "lib/features/voice_settings/presentation/voice_settings_screen.dart").read_text(encoding="utf-8")
localizations = (root / "lib/core/localization/app_localizations.dart").read_text(encoding="utf-8")
assert "NavKey.routes" in bottom_nav
assert "context.go('/routes')" in bottom_nav
assert "context.go('/routes')" in search

assert "path: '/map-settings'" in router
assert "MapSettingsScreen" in router
assert "context.push('/map-settings')" in settings
assert "MapSettingsContent" not in appearance
assert "BackdropFilter" in map_settings
assert "_AccentSwatches" in map_settings
assert "MapPerspective.threeD" in map_settings
assert "abmPoiVisibilityProvider" in map_settings
assert "mapDownloadEntriesProvider" in map_settings
assert "downloadMapRegion(ref, region)" in map_settings
assert "length: 3" not in downloads
assert "_VoiceTab" not in downloads
assert "_MapsTab" not in downloads
assert "const _LanguageTab()" in downloads
assert "downloadVoicePack(ref, pack)" in voice
assert "pack.title" in voice
assert "playDownloadedSample(activeVoice)" in voice
assert voice.count("playDownloadedSample(") == 1
for key in ["map_display", "poi_map_title", "offline_maps_download", "voice_download_packs"]:
    assert f"'{key}'" in localizations

print("settings_layout_contract_ok")
