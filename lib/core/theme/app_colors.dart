import 'package:flutter/material.dart';

class AppColors {
  AppColors._();

  static const background = Color(0xFF0A0C10);
  static const frameBackground = Color(0xFF05070A);

  static const homeAccent = Color(0xFF3EE66B);
  static const homeAccentDark = Color(0xFF123A34);
  static const homeDanger = Color(0xFFE5544B);

  static const subAccentA = Color(0xFF2FE6C4);
  static const subAccentB = Color(0xFF2FE6C4);
  static const subGlassBg = Color(0xF014181D);
  static const subGlassBgSoft = Color(0xD01A2026);
  static const subGlassBorder = Color(0x472FE6C4);

  static const subAccentGradient = LinearGradient(
    begin: Alignment.topLeft,
    end: Alignment.bottomRight,
    colors: [subAccentA, subAccentB],
  );

  static const centerButtonGradient = LinearGradient(
    begin: Alignment.topLeft,
    end: Alignment.bottomRight,
    colors: [homeAccent, subAccentA],
  );

  static const textPrimary = Colors.white;
  static const textSecondary = Color(0xFF9AA4B0);
  static const textMuted = Color(0xFF8B929B);
}
