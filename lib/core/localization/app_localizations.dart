import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../shared/providers/app_settings_providers.dart';

class AppStrings {
  static const Map<String, Map<String, String>> _localizedValues = {
    'fa': {
      'settings': 'تنظیمات',
      'home': 'خانه',
      'routes': 'مسیرها',
      'search': 'جستجو',
      'voice': 'صدا',
      'profile': 'پروفایل کاربری',
      'language': 'زبان و واحدها',
      'theme': 'نمای شب و روز',
      'privacy': 'حریم خصوصی',
      'about': 'درباره آبتین مپس',
      'logout': 'خروج از حساب',
      'guest': 'کاربر مهمان',
      'login_sync': 'برای همگام‌سازی وارد شوید',
      'navigation': 'مسیریابی و ناوبری',
      'map_settings': 'تنظیمات نقشه',
      'voice_settings': 'تنظیمات صدا',
      'favorites': 'علاقه‌مندی‌ها',
      'vehicle_selection': 'انتخاب خودرو',
      'edit_profile': 'ویرایش پروفایل',
      'save_changes': 'ذخیره تغییرات',
      'full_name': 'نام کامل',
      'phone': 'شماره همراه',
      'email': 'ایمیل',
    },
    'en': {
      'settings': 'Settings',
      'home': 'Home',
      'routes': 'Routes',
      'search': 'Search',
      'voice': 'Voice',
      'profile': 'User Profile',
      'language': 'Language & Units',
      'theme': 'Day & Night Mode',
      'privacy': 'Privacy Policy',
      'about': 'About Abtin Maps',
      'logout': 'Logout',
      'guest': 'Guest User',
      'login_sync': 'Login to sync',
      'navigation': 'Routing & Navigation',
      'map_settings': 'Map Settings',
      'voice_settings': 'Voice Settings',
      'favorites': 'Favorites',
      'vehicle_selection': 'Select Vehicle',
      'edit_profile': 'Edit Profile',
      'save_changes': 'Save Changes',
      'full_name': 'Full Name',
      'phone': 'Phone Number',
      'email': 'Email',
    },
  };

  static String get(BuildContext context, WidgetRef ref, String key) {
    final lang = ref.watch(languageProvider);
    return _localizedValues[lang]?[key] ?? key;
  }
}
