import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../../core/theme/app_colors.dart';
import '../../../shared/widgets/glass_panel.dart';
import '../../../shared/widgets/page_header.dart';
import '../presentation/user_providers.dart';
import 'register_screen.dart';

class ProfileScreen extends ConsumerWidget {
  const ProfileScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final userAsync = ref.watch(currentUserProvider);

    return Scaffold(
      backgroundColor: AppColors.frameBackground,
      body: userAsync.when(
        data: (user) {
          if (user == null) {
            return const RegisterScreen();
          }
          return _ProfileContent(user: user);
        },
        loading: () => const Center(child: CircularProgressIndicator()),
        error: (e, _) => Center(child: Text('خطا در بارگذاری: $e')),
      ),
    );
  }
}

class _ProfileContent extends ConsumerWidget {
  final dynamic user;
  const _ProfileContent({required this.user});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    return Column(
      children: [
        const PageHeader(title: 'پروفایل کاربری'),
        Expanded(
          child: SingleChildScrollView(
            padding: const EdgeInsets.all(20),
            child: Column(
              children: [
                const SizedBox(height: 20),
                _buildAvatar(),
                const SizedBox(height: 20),
                Text(
                  user.fullName,
                  style: const TextStyle(
                    color: Colors.white,
                    fontSize: 22,
                    fontWeight: FontWeight.bold,
                  ),
                ),
                const SizedBox(height: 30),
                _buildInfoCard(),
                const SizedBox(height: 20),
                _buildActionButtons(context, ref),
              ],
            ),
          ),
        ),
      ],
    );
  }

  Widget _buildAvatar() {
    return Container(
      padding: const EdgeInsets.all(4),
      decoration: BoxDecoration(
        shape: BoxShape.circle,
        gradient: AppColors.subAccentGradient,
      ),
      child: CircleAvatar(
        radius: 50,
        backgroundColor: AppColors.frameBackground,
        child: const Icon(Icons.person_rounded, size: 60, color: Colors.white70),
      ),
    );
  }

  Widget _buildInfoCard() {
    return GlassPanel(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          children: [
            _InfoRow(label: 'شماره تماس', value: user.phone ?? 'ثبت نشده', icon: Icons.phone_android_rounded),
            const Divider(color: Colors.white10, height: 24),
            _InfoRow(label: 'ایمیل', value: user.email ?? 'ثبت نشده', icon: Icons.email_rounded),
          ],
        ),
      ),
    );
  }

  Widget _buildActionButtons(BuildContext context, WidgetRef ref) {
    return Column(
      children: [
        _ActionButton(
          label: 'ویرایش پروفایل',
          icon: Icons.edit_rounded,
          onTap: () {
            // Logic for editing
          },
        ),
        const SizedBox(height: 12),
        _ActionButton(
          label: 'خروج از حساب',
          icon: Icons.logout_rounded,
          color: Colors.redAccent.withOpacity(0.8),
          onTap: () async {
            await ref.read(userRepositoryProvider).deleteUser(user.id);
          },
        ),
      ],
    );
  }
}

class _InfoRow extends StatelessWidget {
  final String label;
  final String value;
  final IconData icon;

  const _InfoRow({required this.label, required this.value, required this.icon});

  @override
  Widget build(BuildContext context) {
    return Row(
      children: [
        Icon(icon, color: AppColors.textSecondary, size: 20),
        const SizedBox(width: 12),
        Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(label, style: const TextStyle(color: AppColors.textSecondary, fontSize: 12)),
            Text(value, style: const TextStyle(color: Colors.white, fontSize: 14, fontWeight: FontWeight.w500)),
          ],
        ),
      ],
    );
  }
}

class _ActionButton extends StatelessWidget {
  final String label;
  final IconData icon;
  final VoidCallback onTap;
  final Color? color;

  const _ActionButton({required this.label, required this.icon, required this.onTap, this.color});

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      onTap: onTap,
      child: GlassPanel(
        child: Container(
          padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 14),
          child: Row(
            children: [
              Icon(icon, color: color ?? AppColors.subAccentB, size: 22),
              const SizedBox(width: 12),
              Text(label, style: TextStyle(color: color ?? Colors.white, fontSize: 15, fontWeight: FontWeight.w500)),
              const Spacer(),
              Icon(Icons.chevron_right_rounded, color: (color ?? Colors.white).withOpacity(0.3)),
            ],
          ),
        ),
      ),
    );
  }
}
