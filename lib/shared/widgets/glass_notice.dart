import 'dart:ui';
import 'package:flutter/material.dart';

const double kBottomNavBarHeight = 76;

void showGlassNotice(
  BuildContext context,
  String message, {
  required IconData icon,
  required List<Color> colors,
  bool showAboveBottomNav = true,
  Duration duration = const Duration(seconds: 3),
}) {
  final messenger = ScaffoldMessenger.maybeOf(context);
  if (messenger == null) return;
  final bottomSafe = MediaQuery.of(context).padding.bottom;
  final bottomMargin =
      showAboveBottomNav ? (kBottomNavBarHeight + bottomSafe + 12) : (16 + bottomSafe);

  messenger.clearSnackBars();
  messenger.showSnackBar(
    SnackBar(
      behavior: SnackBarBehavior.floating,
      backgroundColor: Colors.transparent,
      elevation: 0,
      duration: duration,
      margin: EdgeInsets.fromLTRB(20, 0, 20, bottomMargin),
      padding: EdgeInsets.zero,
      content: ClipRRect(
        borderRadius: BorderRadius.circular(16),
        child: BackdropFilter(
          filter: ImageFilter.blur(sigmaX: 16, sigmaY: 16),
          child: Container(
            padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 12),
            decoration: BoxDecoration(
              color: const Color(0xCC14171F),
              borderRadius: BorderRadius.circular(16),
              border: Border.all(color: Colors.white.withOpacity(.12)),
              boxShadow: const [
                BoxShadow(color: Colors.black45, blurRadius: 18, offset: Offset(0, 8)),
              ],
            ),
            child: Row(
              children: [
                Container(
                  width: 30,
                  height: 30,
                  decoration: BoxDecoration(
                    shape: BoxShape.circle,
                    gradient: LinearGradient(colors: colors, begin: Alignment.topLeft, end: Alignment.bottomRight),
                    boxShadow: [BoxShadow(color: colors.last.withOpacity(.55), blurRadius: 12)],
                  ),
                  child: Icon(icon, color: Colors.white, size: 16),
                ),
                const SizedBox(width: 12),
                Expanded(
                  child: Text(
                    message,
                    style: const TextStyle(color: Colors.white, fontSize: 14.5, fontWeight: FontWeight.w600, height: 1.3),
                  ),
                ),
              ],
            ),
          ),
        ),
      ),
    ),
  );
}
