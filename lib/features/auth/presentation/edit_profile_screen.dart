import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:drift/drift.dart' as drift;
import '../../../core/theme/app_colors.dart';
import '../../../shared/widgets/page_header.dart';
import '../presentation/user_providers.dart';
import '../../../core/database/app_database.dart';

class EditProfileScreen extends ConsumerStatefulWidget {
  final User user;
  const EditProfileScreen({super.key, required this.user});

  @override
  ConsumerState<EditProfileScreen> createState() => _EditProfileScreenState();
}

class _EditProfileScreenState extends ConsumerState<EditProfileScreen> {
  late TextEditingController _nameController;
  late TextEditingController _emailController;
  late TextEditingController _phoneController;

  @override
  void initState() {
    super.initState();
    _nameController = TextEditingController(text: widget.user.fullName);
    _emailController = TextEditingController(text: widget.user.email ?? '');
    _phoneController = TextEditingController(text: widget.user.phone ?? '');
  }

  @override
  void dispose() {
    _nameController.dispose();
    _emailController.dispose();
    _phoneController.dispose();
    super.dispose();
  }

  Future<void> _save() async {
    final updatedUser = widget.user.copyWith(
      fullName: _nameController.text,
      email: drift.Value(_emailController.text),
      phone: drift.Value(_phoneController.text),
    );
    await ref.read(userRepositoryProvider).updateProfile(updatedUser);
    if (mounted) Navigator.pop(context);
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: const Color(0xFF0A0C10),
      appBar: const PageHeader(title: 'ویرایش پروفایل'),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(24),
        child: Column(
          children: [
            _buildAvatarSection(),
            const SizedBox(height: 32),
            _buildTextField(controller: _nameController, label: 'نام کامل', icon: Icons.person_outline),
            const SizedBox(height: 16),
            _buildTextField(controller: _phoneController, label: 'شماره همراه', icon: Icons.phone_iphone_outlined, keyboardType: TextInputType.phone),
            const SizedBox(height: 16),
            _buildTextField(controller: _emailController, label: 'ایمیل', icon: Icons.email_outlined, keyboardType: TextInputType.emailAddress),
            const SizedBox(height: 40),
            _buildSaveButton(),
          ],
        ),
      ),
    );
  }

  Widget _buildAvatarSection() {
    return Center(
      child: Stack(
        children: [
          Container(
            width: 120,
            height: 120,
            decoration: BoxDecoration(
              shape: BoxShape.circle,
              border: Border.all(color: const Color(0xFF2FE6C4), width: 2),
              color: Colors.white.withOpacity(0.05),
            ),
            child: const Icon(Icons.person, size: 70, color: Colors.white70),
          ),
          Positioned(
            bottom: 0,
            right: 0,
            child: Container(
              padding: const EdgeInsets.all(8),
              decoration: const BoxDecoration(color: Color(0xFF2FE6C4), shape: BoxShape.circle),
              child: const Icon(Icons.camera_alt_rounded, size: 20, color: Colors.black),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildTextField({
    required TextEditingController controller,
    required String label,
    required IconData icon,
    TextInputType? keyboardType,
  }) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.end,
      children: [
        Text(label, style: const TextStyle(color: Colors.white70, fontSize: 13)),
        const SizedBox(height: 8),
        TextField(
          controller: controller,
          keyboardType: keyboardType,
          textAlign: TextAlign.right,
          style: const TextStyle(color: Colors.white),
          decoration: InputDecoration(
            prefixIcon: Icon(icon, color: const Color(0xFF2FE6C4), size: 20),
            filled: true,
            fillColor: Colors.white.withOpacity(0.05),
            border: OutlineInputBorder(borderRadius: BorderRadius.circular(12), borderSide: BorderSide.none),
          ),
        ),
      ],
    );
  }

  Widget _buildSaveButton() {
    return SizedBox(
      width: double.infinity,
      height: 54,
      child: ElevatedButton(
        onPressed: _save,
        style: ElevatedButton.styleFrom(
          backgroundColor: const Color(0xFF2FE6C4),
          shape: RoundedRectangleType(borderRadius: BorderRadius.circular(12)),
        ),
        child: const Text('ذخیره تغییرات', style: TextStyle(color: Colors.black, fontSize: 16, fontWeight: FontWeight.bold)),
      ),
    );
  }
}

class RoundedRectangleType extends RoundedRectangleBorder {
  const RoundedRectangleType({super.borderRadius});
}
