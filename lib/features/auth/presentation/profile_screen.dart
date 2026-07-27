import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'dart:ui';
import '../../../core/theme/app_colors.dart';
import '../../../shared/widgets/glass_panel.dart';
import '../../../shared/widgets/page_header.dart';
import '../../../shared/widgets/bottom_nav.dart';
import '../presentation/user_providers.dart';
import 'register_screen.dart';
import 'edit_profile_screen.dart';

class ProfileScreen extends ConsumerWidget {
  const ProfileScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final userAsync = ref.watch(currentUserProvider);

    return Scaffold(
      backgroundColor: const Color(0xFF0A0C10),
      body: Container(
        decoration: const BoxDecoration(
          gradient: RadialGradient(
            center: Alignment.topCenter,
            radius: 1.2,
            colors: [Color(0xFF10151A), Color(0xFF0A0C10)],
          ),
        ),
        child: Stack(
          children: [
            userAsync.when(
              data: (user) {
                if (user == null) {
                  return const RegisterScreen();
                }
                return _ProfileContent(user: user);
              },
              loading: () => const Center(child: CircularProgressIndicator(color: Color(0xFF2FE6C4))),
              error: (e, _) => Center(child: Text('خطا در بارگذاری: $e', style: const TextStyle(color: Colors.white))),
            ),
            const BottomNav(currentPage: NavKey.settings),
          ],
        ),
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
                const SizedBox(height: 16),
                Text(
                  user.fullName,
                  style: const TextStyle(
                    color: Colors.white,
                    fontSize: 24,
                    fontWeight: FontWeight.bold,
                    letterSpacing: 0.5,
                  ),
                ),
                Text(
                  'کاربر آبتین',
                  style: TextStyle(
                    color: const Color(0xFF2FE6C4).withOpacity(0.8),
                    fontSize: 14,
                    fontWeight: FontWeight.w500,
                  ),
                ),
                const SizedBox(height: 32),
                _buildInfoSection(),
                const SizedBox(height: 24),
                _buildStatsSection(),
                const SizedBox(height: 24),
                _buildActionButtons(context, ref),
                const SizedBox(height: 120),
              ],
            ),
          ),
        ),
      ],
    );
  }

  Widget _buildAvatar() {
    return Container(
      width: 110,
      height: 110,
      padding: const EdgeInsets.all(3),
      decoration: const BoxDecoration(
        shape: BoxShape.circle,
        gradient: LinearGradient(
          colors: [Color(0xFF2FE6C4), Color(0xFF10D15C)],
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
        ),
      ),
      child: Container(
        decoration: const BoxDecoration(
          shape: BoxShape.circle,
          color: Color(0xFF0E1219),
        ),
        child: const Icon(Icons.person_rounded, size: 65, color: Colors.white70),
      ),
    );
  }

  Widget _buildInfoSection() {
    return GlassPanel(
      child: Padding(
        padding: const EdgeInsets.all(20),
        child: Column(
          children: [
            _InfoRow(label: 'شماره همراه', value: user.phone ?? '۰۹۱۲۳۴۵۶۷۸۹', icon: Icons.phone_iphone_rounded),
            const Divider(color: Colors.white10, height: 32),
            _InfoRow(label: 'پست الکترونیک', value: user.email ?? 'info@abtin.ir', icon: Icons.alternate_email_rounded),
          ],
        ),
      ),
    );
  }

  Widget _buildStatsSection() {
    return Row(
      children: [
        Expanded(child: _StatCard(label: 'امتیاز', value: '۱۲۵۰', icon: Icons.stars_rounded, color: Colors.amber)),
        const SizedBox(width: 12),
        Expanded(child: _StatCard(label: 'سفرها', value: '۴۸', icon: Icons.route_rounded, color: const Color(0xFF2FE6C4))),
      ],
    );
  }

  Widget _buildActionButtons(BuildContext context, WidgetRef ref) {
    return Column(
      children: [
        _ProfileButton(
          label: 'ویرایش اطلاعات کاربری',
          icon: Icons.edit_note_rounded,
          onTap: () {
            Navigator.push(
              context,
              MaterialPageRoute(builder: (context) => EditProfileScreen(user: user)),
            );
          },
        ),
        const SizedBox(height: 12),
        _ProfileButton(
          label: 'تاریخچه سفرهای من',
          icon: Icons.history_toggle_off_rounded,
          onTap: () {},
        ),
        const SizedBox(height: 12),
        _ProfileButton(
          label: 'خروج از حساب کاربری',
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

class _StatCard extends StatelessWidget {
  final String label;
  final String value;
  final IconData icon;
  final Color color;
  const _StatCard({required this.label, required this.value, required this.icon, required this.color});

  @override
  Widget build(BuildContext context) {
    return GlassPanel(
      child: Padding(
        padding: const EdgeInsets.symmetric(vertical: 16),
        child: Column(
          children: [
            Icon(icon, color: color, size: 24),
            const SizedBox(height: 8),
            Text(value, style: const TextStyle(color: Colors.white, fontSize: 18, fontWeight: FontWeight.bold)),
            Text(label, style: TextStyle(color: Colors.white.withOpacity(0.5), fontSize: 12)),
          ],
        ),
      ),
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
        Container(
          padding: const EdgeInsets.all(8),
          decoration: BoxDecoration(
            color: Colors.white.withOpacity(0.05),
            borderRadius: BorderRadius.circular(10),
          ),
          child: Icon(icon, color: const Color(0xFF2FE6C4), size: 20),
        ),
        const SizedBox(width: 16),
        Expanded(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.end,
            children: [
              Text(label, style: TextStyle(color: Colors.white.withOpacity(0.4), fontSize: 11)),
              const SizedBox(height: 2),
              Text(value, style: const TextStyle(color: Colors.white, fontSize: 15, fontWeight: FontWeight.w500)),
            ],
          ),
        ),
      ],
    );
  }
}

class _ProfileButton extends StatelessWidget {
  final String label;
  final IconData icon;
  final VoidCallback onTap;
  final Color? color;

  const _ProfileButton({required this.label, required this.icon, required this.onTap, this.color});

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      onTap: onTap,
      child: GlassPanel(
        child: Container(
          padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 14),
          child: Row(
            children: [
              Icon(icon, color: color ?? const Color(0xFF2FE6C4), size: 22),
              const SizedBox(width: 12),
              Text(label, style: TextStyle(color: color ?? Colors.white, fontSize: 15, fontWeight: FontWeight.w500)),
              const Spacer(),
              Icon(Icons.chevron_right_rounded, color: (color ?? Colors.white).withOpacity(0.2)),
            ],
          ),
        ),
      ),
    );
  }
}
