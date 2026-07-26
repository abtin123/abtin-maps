import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import '../../core/theme/app_colors.dart';

class PageHeader extends StatelessWidget implements PreferredSizeWidget {
  final String title;
  final String backRoute;

  const PageHeader({super.key, required this.title, this.backRoute = '/'});

  static const double _contentHeight = 56;

  @override
  Size get preferredSize => const Size.fromHeight(_contentHeight + 59);

  @override
  Widget build(BuildContext context) {
    final topSafe = MediaQuery.of(context).padding.top;
    return Container(
      height: _contentHeight + topSafe,
      padding: EdgeInsets.only(top: topSafe, left: 8, right: 8),
      decoration: BoxDecoration(
        gradient: LinearGradient(
          begin: Alignment.topCenter,
          end: Alignment.bottomCenter,
          colors: [Colors.deepPurple.shade900.withOpacity(.35), Colors.transparent],
        ),
        border: Border(
          bottom: BorderSide(color: AppColors.subGlassBorder),
        ),
      ),
      child: Stack(
        alignment: Alignment.center,
        children: [
          Center(
            child: Text(
              title,
              style: const TextStyle(
                color: Colors.white,
                fontSize: 20,
                fontWeight: FontWeight.bold,
              ),
            ),
          ),
          Align(
            alignment: AlignmentDirectional.centerStart,
            child: Material(
              color: Colors.transparent,
              child: InkWell(
                borderRadius: BorderRadius.circular(24),
                onTap: () {
                  if (context.canPop()) {
                    context.pop();
                  } else {
                    context.go(backRoute);
                  }
                },
                child: Container(
                  width: 40,
                  height: 40,
                  decoration: BoxDecoration(
                    shape: BoxShape.circle,
                    color: const Color(0xFF1E1B42).withOpacity(.6),
                    border: Border.all(color: AppColors.subGlassBorder),
                  ),
                  child: const Icon(
                    Icons.arrow_back_ios_new_rounded,
                    size: 18,
                    color: AppColors.subAccentA,
                  ),
                ),
              ),
            ),
          ),
        ],
      ),
    );
  }
}
