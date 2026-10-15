import 'package:flutter_test/flutter_test.dart';
import 'package:sage_one/evolution/evolution_transition.dart';
import 'package:sage_one/evolution/evolution_visual.dart';

void main() {
  test('transition phases follow the locked High to Low story', () {
    expect(
      evolutionTransitionPhaseFor(.05),
      EvolutionTransitionPhase.accelerate,
    );
    expect(
      evolutionTransitionPhaseFor(.25),
      EvolutionTransitionPhase.concentrate,
    );
    expect(
      evolutionTransitionPhaseFor(.38),
      EvolutionTransitionPhase.blackout,
    );
    expect(
      evolutionTransitionPhaseFor(.50),
      EvolutionTransitionPhase.burst,
    );
    expect(
      evolutionTransitionPhaseFor(.70),
      EvolutionTransitionPhase.reform,
    );
    expect(
      evolutionTransitionPhaseFor(.95),
      EvolutionTransitionPhase.settle,
    );
  });

  test('transition clamps progress outside its animation range', () {
    expect(
      evolutionTransitionPhaseFor(-1),
      EvolutionTransitionPhase.accelerate,
    );
    expect(
      evolutionTransitionPhaseFor(2),
      EvolutionTransitionPhase.settle,
    );
  });

  test('adjacent Evolution stages retain distinct material identities', () {
    final bronze = evolutionVisualFor('Bronze');
    final silver = evolutionVisualFor('Silver');

    expect(bronze.order + 1, silver.order);
    expect(bronze.accent, isNot(silver.accent));
  });
}
