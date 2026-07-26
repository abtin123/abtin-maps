import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../../core/theme/app_colors.dart';
import '../../../shared/widgets/bottom_nav.dart';
import '../../../shared/widgets/glass_panel.dart';
import '../../../shared/widgets/page_header.dart';
import '../data/voice_pack_fa.dart';
import 'tts_providers.dart';

class VoiceSettingsScreen extends ConsumerStatefulWidget {
  const VoiceSettingsScreen({super.key});

  @override
  ConsumerState<VoiceSettingsScreen> createState() => _VoiceSettingsScreenState();
}

class _VoiceSettingsScreenState extends ConsumerState<VoiceSettingsScreen> {
  bool streetNames = true;
  bool cameraAlerts = true;
  bool duckMusic = false;

  @override
  Widget build(BuildContext context) {
    final voiceService = ref.read(ttsServiceProvider);
    final masterOn = ref.watch(ttEnabledProvider);
    final gender = ref.watch(ttsGenderProvider);
    final volume = ref.watch(ttsVolumeProvider);
    final rate = ref.watch(ttsRateProvider);
    final ratePosition = ((rate - 0.5) / 1.0).clamp(0.0, 1.0);

    return Scaffold(
      appBar: const PageHeader(title: 'تنظیمات صدا', backRoute: '/settings'),
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
            Padding(
              padding: const EdgeInsets.fromLTRB(16, 16, 16, 110),
              child: GlassPanel(
                child: SingleChildScrollView(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.stretch,
                    children: [
                      _SwitchRow(
                        label: 'راهنمای صوتی',
                        value: masterOn,
                        onChanged: (v) {
                          ref.read(ttEnabledProvider.notifier).set(v);
                          if (!v) {
                            voiceService.stop();
                          }
                        },
                      ),
                      const SizedBox(height: 16),
                      _OptionRow(
                        title: 'صدای زن',
                        subtitle: 'پکِ صوتیِ فارسی — ضبط‌شده، آفلاین',
                        selected: gender == VoiceGender.female,
                        onTap: () {
                          ref.read(ttsGenderProvider.notifier).set(VoiceGender.female);
                        },
                      ),
                      const SizedBox(height: 10),
                      _OptionRow(
                        title: 'صدای مرد',
                        subtitle: 'پکِ صوتیِ فارسی — ضبط‌شده، آفلاین',
                        selected: gender == VoiceGender.male,
                        onTap: () {
                          ref.read(ttsGenderProvider.notifier).set(VoiceGender.male);
                        },
                      ),
                      const SizedBox(height: 16),
                      _Slider(
                        label: 'میزان بلندی صدا',
                        value: volume,
                        valueLabel: '${(volume * 100).round()}%',
                        onChanged: (v) {
                          ref.read(ttsVolumeProvider.notifier).set(v);
                          voiceService.setVolume(v);
                        },
                      ),
                      const SizedBox(height: 16),
                      _Slider(
                        label: 'سرعت پخش',
                        value: ratePosition,
                        valueLabel: _rateLabel(ratePosition),
                        onChanged: (v) {
                          final mappedRate = 0.5 + v * 1.0;
                          ref.read(ttsRateProvider.notifier).set(mappedRate);
                          voiceService.setPlaybackRate(mappedRate);
                        },
                      ),
                      const SizedBox(height: 10),
                      _TestVoiceButton(
                        onTap: () async {
                          voiceService.setVolume(volume);
                          voiceService.setPlaybackRate(rate);
                          await voiceService.playSequence(VoicePackFa.forManeuver(
                            type: 'turn',
                            modifier: 'right',
                            distanceMeters: 200,
                          ));
                        },
                      ),
                      const SizedBox(height: 20),
                      const Text('تنظیمات صوتی', style: TextStyle(color: Colors.white, fontSize: 15)),
                      const SizedBox(height: 8),
                      _SwitchRow(
                        label: 'اعلام نام خیابان‌ها',
                        desc: 'در پکِ صوتیِ فعلی پشتیبانی نمی‌شود (نیازمند TTS واقعی)',
                        value: false,
                        onChanged: null,
                      ),
                      _SwitchRow(
                        label: 'هشدار صوتی دوربین و رادار',
                        value: cameraAlerts,
                        onChanged: (v) => setState(() => cameraAlerts = v),
                      ),
                      _SwitchRow(
                        label: 'کاهش صدا هنگام پخش موزیک',
                        desc: 'صدای راهنما روی موزیک/پادکست دیگر پایین میاد',
                        value: duckMusic,
                        onChanged: (v) => setState(() => duckMusic = v),
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

  String _rateLabel(double p) {
    final speed = (0.5 + p * 1.0);
    final label = speed == 1.0 ? 'متوسط' : (speed < 1.0 ? 'کند' : 'سریع');
    return '$label (${speed.toStringAsFixed(1)}x)';
  }
}

class _SwitchRow extends StatelessWidget {
  final String label;
  final String? desc;
  final bool value;
  final ValueChanged<bool>? onChanged;

  const _SwitchRow({required this.label, this.desc, required this.value, required this.onChanged});

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(vertical: 12),
      decoration: BoxDecoration(
        border: Border(bottom: BorderSide(color: Colors.white.withOpacity(.06))),
      ),
      child: Row(
        children: [
          Switch(
            value: value,
            onChanged: onChanged,
            activeThumbColor: const Color(0xFF1B1638),
            activeTrackColor: AppColors.subAccentB,
          ),
          const SizedBox(width: 8),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.end,
              children: [
                Text(label, style: const TextStyle(color: Color(0xFFF0F2F4), fontSize: 15)),
                if (desc != null) ...[
                  const SizedBox(height: 3),
                  Text(desc!, style: const TextStyle(color: Color(0xFF8B929B), fontSize: 13)),
                ],
              ],
            ),
          ),
        ],
      ),
    );
  }
}

class _Slider extends StatelessWidget {
  final String label;
  final String valueLabel;
  final double value;
  final ValueChanged<double> onChanged;

  const _Slider({
    required this.label,
    required this.valueLabel,
    required this.value,
    required this.onChanged,
  });

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.end,
      children: [
        Text(label, style: const TextStyle(color: Colors.white, fontSize: 15)),
        Text(valueLabel, style: const TextStyle(color: AppColors.subAccentA, fontWeight: FontWeight.bold, fontSize: 15)),
        SliderTheme(
          data: SliderThemeData(
            activeTrackColor: AppColors.subAccentB,
            inactiveTrackColor: Colors.white.withOpacity(.1),
            thumbColor: Colors.white,
            overlayColor: AppColors.subAccentB.withOpacity(.2),
          ),
          child: Slider(value: value, onChanged: onChanged),
        ),
      ],
    );
  }
}

class _OptionRow extends StatelessWidget {
  final String title;
  final String subtitle;
  final bool selected;
  final VoidCallback onTap;

  const _OptionRow({
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
        margin: const EdgeInsets.only(bottom: 8),
        padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 12),
        decoration: BoxDecoration(
          color: selected ? AppColors.subAccentB.withOpacity(.14) : AppColors.subGlassBgSoft,
          borderRadius: BorderRadius.circular(14),
          border: Border.all(
            color: selected ? AppColors.subAccentB : AppColors.subGlassBorder,
            width: 1.5,
          ),
        ),
        child: Row(
          children: [
            Container(
              width: 20,
              height: 20,
              decoration: BoxDecoration(
                shape: BoxShape.circle,
                border: Border.all(color: selected ? AppColors.subAccentB : const Color(0xFF6B7280), width: 2),
              ),
              child: selected
                  ? Center(
                      child: Container(
                        width: 12,
                        height: 12,
                        decoration: BoxDecoration(shape: BoxShape.circle, gradient: AppColors.subAccentGradient),
                      ),
                    )
                  : null,
            ),
            const SizedBox(width: 12),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.end,
                children: [
                  Text(title, style: const TextStyle(color: Colors.white, fontWeight: FontWeight.bold, fontSize: 16)),
                  const SizedBox(height: 2),
                  Text(subtitle, style: const TextStyle(color: AppColors.textSecondary, fontSize: 13)),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _TestVoiceButton extends StatefulWidget {
  final VoidCallback onTap;

  const _TestVoiceButton({required this.onTap});

  @override
  State<_TestVoiceButton> createState() => _TestVoiceButtonState();
}

class _TestVoiceButtonState extends State<_TestVoiceButton> {
  bool playing = false;

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      onTap: () async {
        setState(() => playing = true);
        widget.onTap();
        await Future.delayed(const Duration(milliseconds: 2000));
        if (mounted) setState(() => playing = false);
      },
      child: Container(
        width: double.infinity,
        padding: const EdgeInsets.symmetric(vertical: 12),
        decoration: BoxDecoration(
          color: AppColors.subAccentB.withOpacity(.14),
          borderRadius: BorderRadius.circular(30),
          border: Border.all(color: AppColors.subAccentB, width: 1.5),
        ),
        child: Row(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            const Icon(Icons.play_arrow_rounded, color: AppColors.subAccentA, size: 18),
            const SizedBox(width: 6),
            Text(
              playing ? 'در حال پخش...' : 'پخش نمونه صدا',
              style: const TextStyle(color: AppColors.subAccentA, fontWeight: FontWeight.bold, fontSize: 15),
            ),
          ],
        ),
      ),
    );
  }
}
