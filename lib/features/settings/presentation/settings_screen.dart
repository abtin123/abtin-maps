import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import '../../../core/theme/app_colors.dart';
import '../../../shared/widgets/bottom_nav.dart';
import '../../../shared/widgets/glass_panel.dart';
import '../../../shared/widgets/page_header.dart';
import '../../vehicle/presentation/vehicle_provider.dart';
import '../../auth/presentation/user_providers.dart';
import '../../../shared/providers/app_settings_providers.dart';
import 'legal_screens.dart';
import '../../../core/localization/app_localizations.dart';

class SettingsScreen extends ConsumerWidget {
  const SettingsScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final selectedVehicle = ref.watch(selectedVehicleProvider);
    return Scaffold(
      backgroundColor: AppColors.background(context),
      appBar: PageHeader(title: AppStrings.get(context, ref, 'settings')),
      body: Container(
        decoration: BoxDecoration(
          gradient: Theme.of(context).brightness == Brightness.dark
            ? const RadialGradient(
                center: Alignment.topCenter,
                radius: 1.2,
                colors: [Color(0xFF10151A), Color(0xFF0A0C10)],
              )
            : null,
          color: AppColors.background(context),
        ),
        child: Stack(
          children: [
            Padding(
              padding: const EdgeInsets.fromLTRB(16, 16, 16, 110),
              child: GlassPanel(
                child: SingleChildScrollView(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.stretch,
                    children: [
                      Consumer(
                        builder: (context, ref, child) {
                          final userAsync = ref.watch(currentUserProvider);
                          return userAsync.when(
                            data: (user) => GestureDetector(
                              onTap: () => context.push('/profile'),
                              child: Row(
                                children: [
                                  Container(
                                    width: 46,
                                    height: 46,
                                    decoration: BoxDecoration(
                                      shape: BoxShape.circle,
                                      color: AppColors.subGlassBgSoft(),
                                      border: Border.all(color: AppColors.subGlassBorder()),
                                    ),
                                    child: const Icon(Icons.person_rounded, color: AppColors.subAccentA),
                                  ),
                                  const SizedBox(width: 12),
                                  Expanded(
                                    child: Column(
                                      crossAxisAlignment: CrossAxisAlignment.end,
                                      children: [
                                        Text(user?.fullName ?? AppStrings.get(context, ref, 'guest'),
                                            style: const TextStyle(color: Colors.white, fontWeight: FontWeight.bold)),
                                        const SizedBox(height: 2),
                                        Text(user == null ? AppStrings.get(context, ref, 'login_sync') : AppStrings.get(context, ref, 'profile'),
                                            style: TextStyle(color: AppColors.textSecondary(), fontSize: 14)),
                                      ],
                                    ),
                                  ),
                                  const Icon(Icons.chevron_left_rounded, color: Color(0xFF8B929B)),
                                ],
                              ),
                            ),
                            loading: () => const CircularProgressIndicator(),
                            error: (e, _) => const Text('Error'),
                          );
                        },
                      ),
                      const Divider(color: Color(0x242FE6C4), height: 30),
                      Text(AppStrings.get(context, ref, 'navigation'),
                          style: const TextStyle(color: AppColors.subAccentB, fontWeight: FontWeight.bold, fontSize: 17)),
                      const SizedBox(height: 6),
                      _MenuRow(icon: Icons.map_rounded, label: AppStrings.get(context, ref, 'map_settings'), chevron: true, onTap: () => context.push('/map-settings')),
                      _MenuRow(
                        icon: Icons.brightness_6_rounded,
                        label: AppStrings.get(context, ref, 'theme'),
                        onTap: () {
                          final current = ref.read(themeModeProvider);
                          ref.read(themeModeProvider.notifier).state =
                              current == ThemeMode.dark ? ThemeMode.light : ThemeMode.dark;
                        },
                      ),
                      _MenuRow(
                        icon: Icons.record_voice_over_rounded,
                        label: AppStrings.get(context, ref, 'voice_settings'),
                        chevron: true,
                        onTap: () => context.push('/voice-settings'),
                      ),
                      const _MenuRow(icon: Icons.traffic_rounded, label: 'ترافیک / راهبندها', desc: 'خودکار روی مسیرها اعمال می‌شود'),
                      _MenuRow(
                        icon: Icons.directions_car_filled_rounded,
                        label: 'انتخاب خودرو',
                        desc: selectedVehicle == VehicleType.arrow
                            ? 'پیکان (پیش‌فرض)'
                            : 'BMW i8 — مدل سه‌بعدی',
                        chevron: true,
                        onTap: () => _showVehiclePicker(context, ref),
                      ),
                      const SizedBox(height: 20),
                      const Text('حساب کاربری و داده‌ها',
                          style: TextStyle(color: AppColors.subAccentB, fontWeight: FontWeight.bold, fontSize: 17)),
                      const SizedBox(height: 6),
                      const _MenuRow(icon: Icons.account_circle_rounded, label: 'حساب کاربری'),
                      _MenuRow(
                        icon: Icons.star_rounded,
                        label: 'علاقه‌مندی‌ها',
                        chevron: true,
                        onTap: () => context.push('/saved-places'),
                      ),
                      const SizedBox(height: 20),
                      const Text('عمومی',
                          style: TextStyle(color: AppColors.subAccentB, fontWeight: FontWeight.bold, fontSize: 17)),
                      const SizedBox(height: 6),
                      _MenuRow(
                        icon: Icons.language_rounded,
                        label: AppStrings.get(context, ref, 'language'),
                        desc: ref.watch(languageProvider) == 'fa' ? 'فارسی' : 'English',
                        onTap: () {
                          final current = ref.read(languageProvider);
                          ref.read(languageProvider.notifier).state = current == 'fa' ? 'en' : 'fa';
                        },
                      ),
                      _MenuRow(
                        icon: Icons.shield_rounded,
                        label: AppStrings.get(context, ref, 'privacy'),
                        onTap: () => Navigator.push(
                          context,
                          MaterialPageRoute(builder: (context) => const PrivacyPolicyScreen()),
                        ),
                      ),
                      _MenuRow(
                        icon: Icons.info_outline_rounded,
                        label: AppStrings.get(context, ref, 'about'),
                        onTap: () => Navigator.push(
                          context,
                          MaterialPageRoute(builder: (context) => const AboutAppScreen()),
                        ),
                      ),
                      const SizedBox(height: 24),
                      Center(
                        child: GestureDetector(
                          onTap: () {
                            final userAsync = ref.read(currentUserProvider);
                            userAsync.whenData((user) {
                              if (user != null) {
                                ref.read(userRepositoryProvider).deleteUser(user.id);
                              }
                            });
                          },
                          child: Text(AppStrings.get(context, ref, 'logout'),
                              style: const TextStyle(color: Color(0xFFFF6B81), fontWeight: FontWeight.w600)),
                        ),
                      ),
                    ],
                  ),
                ),
              ),
            ),
            const BottomNav(currentPage: NavKey.settings),
          ],
        ),
      ),
    );
  }

  void _showVehiclePicker(BuildContext context, WidgetRef ref) {
    showModalBottomSheet(
      context: context,
      backgroundColor: const Color(0xFF14181D),
      shape: const RoundedRectangleBorder(
        borderRadius: BorderRadius.vertical(top: Radius.circular(24)),
      ),
      builder: (ctx) {
        final current = ref.watch(selectedVehicleProvider);
        return Padding(
          padding: const EdgeInsets.all(20),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              const Text('انتخاب خودرو', style: TextStyle(color: Colors.white, fontWeight: FontWeight.bold, fontSize: 18)),
              const SizedBox(height: 16),
              _VehicleOption(
                title: 'پیکان (پیش‌فرض)',
                subtitle: 'نمای دوبعدی، همیشه در دسترس',
                selected: current == VehicleType.arrow,
                onTap: () {
                  ref.read(selectedVehicleProvider.notifier).state = VehicleType.arrow;
                  Navigator.pop(ctx);
                },
              ),
              const SizedBox(height: 10),
              _VehicleOption(
                title: 'BMW i8 (مدل سه‌بعدی)',
                subtitle: 'رندر کامل GLB در فاز بعد فعال می‌شود',
                selected: current == VehicleType.bmwI8,
                onTap: () {
                  ref.read(selectedVehicleProvider.notifier).state = VehicleType.bmwI8;
                  Navigator.pop(ctx);
                },
              ),
            ],
          ),
        );
      },
    );
  }
}

class _VehicleOption extends StatelessWidget {
  final String title;
  final String subtitle;
  final bool selected;
  final VoidCallback onTap;

  const _VehicleOption({
    required this.title,
    required this.subtitle,
    required this.selected,
    required this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      onTap: onTap,
      child: Container(
        width: double.infinity,
        padding: const EdgeInsets.all(14),
        decoration: BoxDecoration(
          color: selected ? AppColors.subAccentB.withOpacity(.16) : AppColors.subGlassBgSoft(),
          borderRadius: BorderRadius.circular(14),
          border: Border.all(color: selected ? AppColors.subAccentB : AppColors.subGlassBorder(), width: 1.5),
        ),
        child: Row(
          children: [
            Icon(
              selected ? Icons.check_circle_rounded : Icons.circle_outlined,
              color: selected ? AppColors.subAccentB : const Color(0xFF6B7280),
              size: 20,
            ),
            const SizedBox(width: 12),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.end,
                children: [
                  Text(title, style: const TextStyle(color: Colors.white, fontWeight: FontWeight.bold, fontSize: 16)),
                  const SizedBox(height: 2),
                  Text(subtitle, style: TextStyle(color: AppColors.textSecondary(), fontSize: 13)),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _MenuRow extends StatelessWidget {
  final IconData icon;
  final String label;
  final String? desc;
  final bool chevron;
  final VoidCallback? onTap;

  const _MenuRow({
    required this.icon,
    required this.label,
    this.desc,
    this.chevron = false,
    this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    return InkWell(
      onTap: onTap,
      child: Container(
        padding: const EdgeInsets.symmetric(vertical: 12),
        decoration: BoxDecoration(
          border: Border(bottom: BorderSide(color: Colors.white.withOpacity(.06))),
        ),
        child: Row(
          children: [
            Icon(icon, color: AppColors.subAccentA, size: 20),
            const SizedBox(width: 12),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.end,
                children: [
                  Text(label, style: const TextStyle(color: Color(0xFFF0F2F4), fontSize: 16, fontWeight: FontWeight.w500)),
                  if (desc != null) ...[
                    const SizedBox(height: 3),
                    Text(desc!, style: const TextStyle(color: Color(0xFF8B929B), fontSize: 13)),
                  ],
                ],
              ),
            ),
            if (chevron) const Icon(Icons.chevron_left_rounded, color: Color(0xFF8B929B), size: 18),
          ],
        ),
      ),
    );
  }
}
