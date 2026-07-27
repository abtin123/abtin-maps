import 'package:flutter/material.dart';
import 'app_colors.dart';

class AppTheme {
  AppTheme._();

  static ThemeData get dark {
    return ThemeData(
      useMaterial3: true,
      brightness: Brightness.dark,
      scaffoldBackgroundColor: AppColors.background(),
      fontFamily: 'Vazirmatn',
      colorScheme: ColorScheme.dark(
        primary: AppColors.homeAccent,
        secondary: AppColors.subAccentA,
        surface: AppColors.frameBackground(),
      ),
      textTheme: TextTheme(
        bodyMedium: TextStyle(color: AppColors.textPrimary(), fontSize: 14),
      ),
      splashFactory: NoSplash.splashFactory,
    );
  }

  static ThemeData get light {
    return ThemeData(
      useMaterial3: true,
      brightness: Brightness.light,
      scaffoldBackgroundColor: const Color(0xFFF8F9FA),
      fontFamily: 'Vazirmatn',
      colorScheme: const ColorScheme.light(
        primary: Color(0xFF2FE6C4),
        secondary: Color(0xFF10D15C),
        surface: Colors.white,
      ),
      textTheme: const TextTheme(
        bodyMedium: TextStyle(color: Color(0xFF212529), fontSize: 14),
      ),
      splashFactory: NoSplash.splashFactory,
    );
  }
}
