import 'package:flutter/material.dart';

enum EvolutionIntensity { low, mid, high }

class EvolutionVisual {
  const EvolutionVisual({
    required this.order,
    required this.name,
    required this.material,
    required this.accent,
    required this.intensity,
  });

  final int order;
  final String name;
  final String material;
  final Color accent;
  final EvolutionIntensity intensity;

  double get particleOpacity => switch (intensity) {
        EvolutionIntensity.low => .20,
        EvolutionIntensity.mid => .42,
        EvolutionIntensity.high => .68,
      };

  double get glowOpacity => switch (intensity) {
        EvolutionIntensity.low => .08,
        EvolutionIntensity.mid => .15,
        EvolutionIntensity.high => .24,
      };

  double get particleDensity => switch (intensity) {
        EvolutionIntensity.low => .35,
        EvolutionIntensity.mid => .65,
        EvolutionIntensity.high => 1.0,
      };
}

const evolutionVisuals = <String, EvolutionVisual>{
  'bronze': EvolutionVisual(order: 1, name: 'Bronze', material: 'Copper / Bronze', accent: Color(0xFFCD8B5A), intensity: EvolutionIntensity.mid),
  'silver': EvolutionVisual(order: 2, name: 'Silver', material: 'Silver / White', accent: Color(0xFFB9C7D8), intensity: EvolutionIntensity.mid),
  'gold': EvolutionVisual(order: 3, name: 'Gold', material: 'Gold', accent: Color(0xFFFFC857), intensity: EvolutionIntensity.mid),
  'platinum': EvolutionVisual(order: 4, name: 'Platinum', material: 'Platinum / Ice', accent: Color(0xFF70D5FF), intensity: EvolutionIntensity.mid),
  'jade': EvolutionVisual(order: 5, name: 'Jade', material: 'Jade Green', accent: Color(0xFF45D6A2), intensity: EvolutionIntensity.mid),
  'ruby': EvolutionVisual(order: 6, name: 'Ruby', material: 'Ruby Red', accent: Color(0xFFFF4D68), intensity: EvolutionIntensity.mid),
  'sapphire': EvolutionVisual(order: 7, name: 'Sapphire', material: 'Sapphire Blue', accent: Color(0xFF428DFF), intensity: EvolutionIntensity.mid),
  'emerald': EvolutionVisual(order: 8, name: 'Emerald', material: 'Emerald Green', accent: Color(0xFF37D9B2), intensity: EvolutionIntensity.mid),
  'diamond sovereign': EvolutionVisual(order: 9, name: 'Diamond Sovereign', material: 'Diamond / White', accent: Color(0xFFE9F7FF), intensity: EvolutionIntensity.mid),
  'black opal realm': EvolutionVisual(order: 10, name: 'Black Opal Realm', material: 'Opalescent', accent: Color(0xFFBFA8FF), intensity: EvolutionIntensity.mid),
  'painite core': EvolutionVisual(order: 11, name: 'Painite Core', material: 'Rare Red / Orange', accent: Color(0xFFFF7048), intensity: EvolutionIntensity.mid),
  'void matter': EvolutionVisual(order: 12, name: 'Void Matter', material: 'Cosmic / Void', accent: Color(0xFFBA63FF), intensity: EvolutionIntensity.mid),
  'californium overlord': EvolutionVisual(order: 13, name: 'Californium Overlord', material: 'Ultra-rare / Cosmic', accent: Color(0xFFFFD166), intensity: EvolutionIntensity.mid),
};

EvolutionVisual evolutionVisualFor(String name, {EvolutionIntensity intensity = EvolutionIntensity.mid}) {
  final key = name.trim().toLowerCase();
  final base = evolutionVisuals[key] ?? const EvolutionVisual(
    order: 0,
    name: 'SAGE',
    material: 'SAGE Core',
    accent: Color(0xFF35B8FF),
    intensity: EvolutionIntensity.mid,
  );
  return EvolutionVisual(
    order: base.order,
    name: base.name,
    material: base.material,
    accent: base.accent,
    intensity: intensity,
  );
}

class EvolutionAtmosphere extends StatelessWidget {
  const EvolutionAtmosphere({
    required this.visual,
    required this.child,
    super.key,
  });

  final EvolutionVisual visual;
  final Widget child;

  @override
  Widget build(BuildContext context) {
    final accent = visual.accent;
    return Stack(
      children: [
        Positioned.fill(
          child: DecoratedBox(
            decoration: BoxDecoration(
              color: const Color(0xFF02060D),
              gradient: RadialGradient(
                center: const Alignment(0, -.55),
                radius: 1.15,
                colors: [
                  accent.withValues(alpha: visual.glowOpacity),
                  const Color(0xFF061426).withValues(alpha: .9),
                  const Color(0xFF010308),
                ],
              ),
            ),
          ),
        ),
        Positioned.fill(
          child: IgnorePointer(
            child: CustomPaint(
              painter: _EvolutionParticlesPainter(
                accent: accent,
                opacity: visual.particleOpacity,
                density: visual.particleDensity,
              ),
            ),
          ),
        ),
        child,
      ],
    );
  }
}

class _EvolutionParticlesPainter extends CustomPainter {
  const _EvolutionParticlesPainter({
    required this.accent,
    required this.opacity,
    required this.density,
  });

  final Color accent;
  final double opacity;
  final double density;

  @override
  void paint(Canvas canvas, Size size) {
    final paint = Paint()..color = accent.withValues(alpha: opacity);
    final count = (18 * density).round();
    for (var i = 0; i < count; i++) {
      final x = ((i * 83) % 100) / 100 * size.width;
      final y = ((i * 47 + 11) % 100) / 100 * size.height;
      final radius = i.isEven ? 1.2 : .7;
      canvas.drawCircle(Offset(x, y), radius, paint);
    }
  }

  @override
  bool shouldRepaint(covariant _EvolutionParticlesPainter oldDelegate) =>
      oldDelegate.accent != accent ||
      oldDelegate.opacity != opacity ||
      oldDelegate.density != density;
}
