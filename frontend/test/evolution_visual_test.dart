import 'package:flutter_test/flutter_test.dart';
import 'package:sage_one/evolution/evolution_visual.dart';

void main() {
  const canonicalStages = [
    'Bronze',
    'Silver',
    'Gold',
    'Platinum',
    'Jade',
    'Ruby',
    'Sapphire',
    'Emerald',
    'Diamond Sovereign',
    'Black Opal Realm',
    'Painite Core',
    'Void Matter',
    'Californium Overlord',
  ];

  test('locked Evolution catalog contains all 13 stages in canonical order', () {
    expect(evolutionVisuals.length, canonicalStages.length);

    final ordered = evolutionVisuals.values.toList()
      ..sort((a, b) => a.order.compareTo(b.order));

    expect(ordered.map((stage) => stage.name).toList(), canonicalStages);
    expect(ordered.map((stage) => stage.order).toList(),
        List<int>.generate(13, (index) => index + 1));
  });

  test('all intensity levels preserve each rank identity and material', () {
    for (final stage in evolutionVisuals.values) {
      final low = evolutionVisualFor(
        stage.name,
        intensity: EvolutionIntensity.low,
      );
      final mid = evolutionVisualFor(
        stage.name,
        intensity: EvolutionIntensity.mid,
      );
      final high = evolutionVisualFor(
        stage.name,
        intensity: EvolutionIntensity.high,
      );

      expect(low.name, stage.name, reason: 'Low: ${stage.name}');
      expect(mid.name, stage.name, reason: 'Mid: ${stage.name}');
      expect(high.name, stage.name, reason: 'High: ${stage.name}');
      expect(low.order, stage.order, reason: 'Order: ${stage.name}');
      expect(low.material, stage.material, reason: 'Material: ${stage.name}');
      expect(low.accent, mid.accent, reason: 'Low/Mid accent: ${stage.name}');
      expect(mid.accent, high.accent, reason: 'Mid/High accent: ${stage.name}');
      expect(low.particleOpacity, lessThan(mid.particleOpacity));
      expect(mid.particleOpacity, lessThan(high.particleOpacity));
      expect(low.glowOpacity, lessThan(mid.glowOpacity));
      expect(mid.glowOpacity, lessThan(high.glowOpacity));
      expect(low.particleDensity, lessThan(mid.particleDensity));
      expect(mid.particleDensity, lessThan(high.particleDensity));
    }
  });

  test('unknown stages fail safely to SAGE core identity', () {
    final visual = evolutionVisualFor('Unknown Stage');
    expect(visual.order, 0);
    expect(visual.name, 'SAGE');
    expect(visual.material, 'SAGE Core');
  });
}
