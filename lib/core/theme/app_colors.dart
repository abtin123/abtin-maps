import 'package:flutter/material.dart';

class AppColors {
  AppColors._();

  static Color background([BuildContext? context]) {
    if (context == null) return const Color(0xFF0A0C10);
    return Theme.of(context).brightness == Brightness.dark ? const Color(0xFF0A0C10) : const Color(0xFFF8F9FA);
  }

  static Color frameBackground([BuildContext? context]) {
    if (context == null) return const Color(0xFF05070A);
    return Theme.of(context).brightness == Brightness.dark ? const Color(0xFF05070A) : Colors.white;
  }

  static const homeAccent = Color(0xFF3EE66B);
  static const homeAccentDark = Color(0xFF123A34);
  static const homeDanger = Color(0xFFE5544B);

  static const subAccentA = Color(0xFF2FE6C4);
  static const subAccentB = Color(0xFF2FE6C4);
  
  static Color subGlassBg([BuildContext? context]) {
    if (context == null) return const Color(0xF014181D);
    return Theme.of(context).brightness == Brightness.dark ? const Color(0xF014181D) : Colors.white.withOpacity(0.9);
  }
      
  static Color subGlassBgSoft([BuildContext? context]) {
    if (context == null) return const Color(0xD01A2026);
    return Theme.of(context).brightness == Brightness.dark ? const Color(0xD01A2026) : Colors.white.withOpacity(0.8);
  }
      
  static Color subGlassBorder([BuildContext? context]) {
    if (context == null) return const Color(0x472FE6C4);
    return Theme.of(context).brightness == Brightness.dark ? const Color(0x472FE6C4) : Colors.black12;
  }
  
  static const speedLow = Color(0xFF3DDC84);
  static const speedMid = Color(0xFFFFD422);
  static const speedHigh = Color(0xFFFF4B4B);
  static const speedPanelBg = Color(0xFF14171F);

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

  static Color textPrimary([BuildContext? context]) {
    if (context == null) return Colors.white;
    return Theme.of(context).brightness == Brightness.dark ? Colors.white : const Color(0xFF212529);
  }
      
  static Color textSecondary([BuildContext? context]) {
    if (context == null) return const Color(0xFF9AA4B0);
    return Theme.of(context).brightness == Brightness.dark ? const Color(0xFF9AA4B0) : const Color(0xFF495057);
  }
      
  static Color textMuted([BuildContext? context]) {
    if (context == null) return const Color(0xFF8B929B);
    return Theme.of(context).brightness == Brightness.dark ? const Color(0xFF8B929B) : const Color(0xFFADB5BD);
  }
}
