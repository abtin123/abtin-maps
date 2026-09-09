import 'package:flutter/material.dart';
import 'abm_notifier.dart';
import 'abm_log_share.dart';

class AbmDebugBanner extends StatelessWidget {
  final Widget child;
  const AbmDebugBanner({super.key, required this.child});

  @override
  Widget build(BuildContext context) {
    return Stack(
      children: [
        child,
        ValueListenableBuilder<String?>(
          valueListenable: AbmNotifier.message,
          builder: (_, msg, __) {
            if (msg == null) return const SizedBox();
            return Positioned(
              left: 12,
              right: 12,
              bottom: 30,
              child: Material(
                color: Colors.redAccent,
                borderRadius: BorderRadius.circular(12),
                child: ListTile(
                  title: Text(msg, style: const TextStyle(color: Colors.white)),
                  trailing: Wrap(
                    children: [
                      IconButton(
                        icon: const Icon(Icons.send, color: Colors.white),
                        onPressed: () => AbmLogShare.send(msg),
                      ),
                      IconButton(
                        icon: const Icon(Icons.close, color: Colors.white),
                        onPressed: () => AbmNotifier.message.value = null,
                      ),
                    ],
                  ),
                ),
              ),
            );
          },
        )
      ],
    );
  }
}
