#!/usr/bin/env bash
set -euo pipefail
flutter clean
flutter pub get
flutter analyze
flutter build apk --debug
