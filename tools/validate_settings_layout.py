#!/usr/bin/env python3
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
assert "NavKey.routes" in bottom_nav
assert "context.go('/routes')" in bottom_nav
assert "context.go('/routes')" in search

print("settings_layout_contract_ok")
