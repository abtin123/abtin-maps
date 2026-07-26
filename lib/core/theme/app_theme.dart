import 'package:flutter/material.dart';
import 'app_colors.dart';

class AppTheme {
  AppTheme._();

  static ThemeData get dark {
    return ThemeData(
      useMaterial3: true,
      brightness: Brightness.dark,
      scaffoldBackgroundColor: AppColors.background,
      fontFamily: 'Vazirmatn',
      colorScheme: const ColorScheme.dark(
        primary: AppColors.homeAccent,
        secondary: AppColors.subAccentA,
        surface: AppColors.frameBackground,
      ),
      textTheme: const TextTheme(
        bodyMedium: TextStyle(color: AppColors.textPrimary, fontSize: 14),
      ),
      splashFactory: NoSplash.splashFactory,
    );
  }
}
