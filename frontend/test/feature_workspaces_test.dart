import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:sage_one/screens/feature_workspaces.dart';

void main() {
  testWidgets('workspace action does not falsely report success', (tester) async {
    await tester.pumpWidget(const MaterialApp(
      home: AppsScreen(),
    ));

    await tester.tap(find.text('Browse connected apps'));
    await tester.pumpAndSettle();

    expect(find.text('Integration status'), findsOneWidget);
    expect(find.text('Interface available • Live actions not connected yet'), findsOneWidget);
    expect(find.textContaining('not connected to a live workflow yet'), findsOneWidget);
    expect(find.text('is ready in SAGE ONE.'), findsNothing);
  });

  testWidgets(
    'Learning and Community placeholder actions stay explicitly unconnected',
    (tester) async {
      const scenarios = <_WorkspaceScenario>[
        _WorkspaceScenario(
          screen: CommunityScreen(),
          actions: ['Open community', 'Create a post', 'View activity'],
        ),
      ];

      for (final scenario in scenarios) {
        await tester.pumpWidget(MaterialApp(home: scenario.screen));
        await tester.pumpAndSettle();
        expect(find.text('Integration status'), findsOneWidget);

        for (final action in scenario.actions) {
          await tester.tap(find.text(action));
          await tester.pumpAndSettle();

          expect(
            find.textContaining('not connected to a live workflow yet'),
            findsOneWidget,
            reason: 'Every placeholder action must disclose its integration status.',
          );
          expect(
            find.textContaining('It will not report success or change account data'),
            findsOneWidget,
          );
          expect(find.text('is ready in SAGE ONE.'), findsNothing);

          await tester.tap(find.text('Understood'));
          await tester.pumpAndSettle();
          expect(tester.takeException(), isNull);
        }

        await tester.pumpWidget(const SizedBox.shrink());
      }
    },
  );

}

class _WorkspaceScenario {
  const _WorkspaceScenario({required this.screen, required this.actions});
  final Widget screen;
  final List<String> actions;
}
