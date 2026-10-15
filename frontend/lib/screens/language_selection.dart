import 'package:flutter/material.dart';

import '../theme/sage_theme.dart';

class LanguageSelectionScreen extends StatefulWidget {
  const LanguageSelectionScreen({required this.onContinue, super.key});

  final ValueChanged<String> onContinue;

  @override
  State<LanguageSelectionScreen> createState() => _LanguageSelectionScreenState();
}

class _LanguageSelectionScreenState extends State<LanguageSelectionScreen> {
  String _selected = 'English';

  static const _languages = <Map<String, String>>[
    {'name': 'English', 'native': 'English', 'code': 'EN'},
    {'name': 'Nepali', 'native': 'नेपाली', 'code': 'NE'},
  ];

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: SageTheme.voidBlack,
      body: DecoratedBox(
        decoration: const BoxDecoration(
          gradient: RadialGradient(
            center: Alignment(0, -.28),
            radius: 1.18,
            colors: [Color(0xFF0B2242), Color(0xFF061326), Color(0xFF020306)],
            stops: [0, .52, 1],
          ),
        ),
        child: SafeArea(
          child: Padding(
            padding: const EdgeInsets.fromLTRB(22, 22, 22, 20),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const _SageMark(size: 48),
                const Spacer(flex: 2),
                const Text('WELCOME TO SAGE ONE', style: TextStyle(
                  color: SageTheme.cyan, fontSize: 10, fontWeight: FontWeight.w800, letterSpacing: 2.1,
                )),
                const SizedBox(height: 10),
                const Text('Choose your language.', style: TextStyle(
                  fontSize: 31, height: 1.05, fontWeight: FontWeight.w800,
                )),
                const SizedBox(height: 10),
                const Text(
                  'You can change this later. SAGE ONE is starting with English and Nepali for its Nepal-first experience.',
                  style: TextStyle(color: SageTheme.textSecondary, fontSize: 12, height: 1.5),
                ),
                const SizedBox(height: 26),
                ..._languages.map(_languageTile),
                const Spacer(flex: 3),
                SizedBox(
                  width: double.infinity,
                  height: 54,
                  child: FilledButton(
                    onPressed: () => widget.onContinue(_selected),
                    child: const Text('Continue'),
                  ),
                ),
                const SizedBox(height: 8),
                const Center(child: Text('LANGUAGE • STEP 1', style: TextStyle(
                  color: SageTheme.textSecondary, fontSize: 9, letterSpacing: 1.4, fontWeight: FontWeight.w700,
                ))),
              ],
            ),
          ),
        ),
      ),
    );
  }

  Widget _languageTile(Map<String, String> language) {
    final selected = _selected == language['name'];
    return Padding(
      padding: const EdgeInsets.only(bottom: 10),
      child: Material(
        color: selected ? SageTheme.cyan.withValues(alpha: .09) : SageTheme.surface.withValues(alpha: .72),
        borderRadius: BorderRadius.circular(18),
        child: InkWell(
          borderRadius: BorderRadius.circular(18),
          onTap: () => setState(() => _selected = language['name']!),
          child: AnimatedContainer(
            duration: const Duration(milliseconds: 180),
            padding: const EdgeInsets.all(16),
            decoration: BoxDecoration(
              borderRadius: BorderRadius.circular(18),
              border: Border.all(color: selected ? SageTheme.cyan.withValues(alpha: .55) : Colors.white.withValues(alpha: .07)),
            ),
            child: Row(
              children: [
                Container(
                  width: 42, height: 42, alignment: Alignment.center,
                  decoration: BoxDecoration(
                    shape: BoxShape.circle,
                    color: selected ? SageTheme.cyan.withValues(alpha: .13) : Colors.white.withValues(alpha: .04),
                  ),
                  child: Text(language['code']!, style: TextStyle(
                    color: selected ? SageTheme.cyan : Colors.white70, fontSize: 11, fontWeight: FontWeight.w800,
                  )),
                ),
                const SizedBox(width: 14),
                Expanded(child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(language['name']!, style: const TextStyle(fontSize: 15, fontWeight: FontWeight.w700)),
                    const SizedBox(height: 3),
                    Text(language['native']!, style: const TextStyle(color: SageTheme.textSecondary, fontSize: 11)),
                  ],
                )),
                AnimatedSwitcher(
                  duration: const Duration(milliseconds: 160),
                  child: selected
                      ? const Icon(Icons.check_circle, key: ValueKey('selected'), color: SageTheme.cyan)
                      : const Icon(Icons.radio_button_unchecked, key: ValueKey('unselected'), color: SageTheme.textSecondary),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}

class _SageMark extends StatelessWidget {
  const _SageMark({required this.size});
  final double size;

  @override
  Widget build(BuildContext context) => Container(
    width: size, height: size, alignment: Alignment.center,
    decoration: BoxDecoration(
      shape: BoxShape.circle,
      gradient: const RadialGradient(
        center: Alignment(-.3, -.35), radius: .95,
        colors: [Color(0xFF5FE6FF), Color(0xFF1263D2), Color(0xFF061630), Color(0xFF020306)],
        stops: [0, .3, .72, 1],
      ),
      border: Border.all(color: SageTheme.cyan.withValues(alpha: .5)),
      boxShadow: [BoxShadow(color: SageTheme.cyan.withValues(alpha: .18), blurRadius: 24, spreadRadius: 1)],
    ),
    child: Text('S', style: TextStyle(
      color: Colors.white, fontSize: size * .54, height: 1, fontWeight: FontWeight.w300,
      shadows: const [Shadow(color: SageTheme.cyan, blurRadius: 10)],
    )),
  );
}
