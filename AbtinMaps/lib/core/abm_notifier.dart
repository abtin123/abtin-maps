import 'package:flutter/material.dart';

class AbmNotifier {
  static final ValueNotifier<String?> message = ValueNotifier<String?>(null);

  static void show(String text) {
    message.value = text;
  }
}
