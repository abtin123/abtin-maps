import 'package:flutter/material.dart';
import '../../../shared/widgets/page_header.dart';

class PrivacyPolicyScreen extends StatelessWidget {
  const PrivacyPolicyScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return const Scaffold(
      backgroundColor: Color(0xFF0A0C10),
      appBar: PageHeader(title: 'حریم خصوصی'),
      body: SingleChildScrollView(
        padding: EdgeInsets.all(24),
        child: Text(
          'اپلیکیشن آبتین مپس متعهد به حفظ حریم خصوصی شماست. داده‌های مکانی شما فقط برای مسیریابی استفاده شده و به صورت محلی در دستگاه شما ذخیره می‌گردد. ما هیچ اطلاعات شخصی را بدون اجازه شما با اشخاص ثالث به اشتراک نمی‌گذاریم.',
          textAlign: TextAlign.right,
          style: TextStyle(color: Colors.white70, fontSize: 15, height: 1.8),
        ),
      ),
    );
  }
}

class AboutAppScreen extends StatelessWidget {
  const AboutAppScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: const Color(0xFF0A0C10),
      appBar: const PageHeader(title: 'درباره آبتین مپس'),
      body: Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Container(
              width: 100,
              height: 100,
              decoration: BoxDecoration(
                color: const Color(0xFF2FE6C4).withOpacity(0.1),
                borderRadius: BorderRadius.circular(20),
              ),
              child: const Icon(Icons.map_rounded, color: Color(0xFF2FE6C4), size: 50),
            ),
            const SizedBox(height: 24),
            const Text('آبتین مپس', style: TextStyle(color: Colors.white, fontSize: 24, fontWeight: FontWeight.bold)),
            const Text('نسخه 1.0.0', style: TextStyle(color: Colors.white54, fontSize: 14)),
            const SizedBox(height: 32),
            const Padding(
              padding: EdgeInsets.symmetric(horizontal: 40),
              child: Text(
                'پیشرفته‌ترین سامانه مسیریابی و نقشه کاملاً بومی با قابلیت‌های آفلاین و آنلاین دقیق.',
                textAlign: TextAlign.center,
                style: TextStyle(color: Colors.white70, fontSize: 14, height: 1.6),
              ),
            ),
          ],
        ),
      ),
    );
  }
}
