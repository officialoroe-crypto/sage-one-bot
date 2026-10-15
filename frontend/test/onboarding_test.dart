import 'package:flutter_test/flutter_test.dart';

import 'package:sage_one/screens/auth_gate.dart';

void main() {
  test('onboarding is required for a normal incomplete profile', () {
    expect(
      shouldRequireOnboarding(
        const {'onboarding_completed': false},
        developerMode: false,
        ownerMode: false,
      ),
      isTrue,
    );
  });

  test('completed onboarding opens the workspace', () {
    expect(
      shouldRequireOnboarding(
        const {'onboarding_completed': true},
        developerMode: false,
        ownerMode: false,
      ),
      isFalse,
    );
  });

  test('developer mode still requires first-run onboarding', () {
    expect(
      shouldRequireOnboarding(
        const {'onboarding_completed': false},
        developerMode: true,
        ownerMode: false,
      ),
      isTrue,
    );
  });

  test('owner mode still requires first-run onboarding', () {
    expect(
      shouldRequireOnboarding(
        const {'onboarding_completed': false},
        developerMode: false,
        ownerMode: true,
      ),
      isTrue,
    );
  });
}
