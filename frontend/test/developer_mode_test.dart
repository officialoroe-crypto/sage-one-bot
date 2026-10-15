import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:sage_one/core/sage_api.dart';
import 'package:sage_one/screens/developer_mode.dart';

void main() {
  testWidgets('developer mode is explicitly approval gated', (tester) async {
    final api = SageApi(authToken: 'test-token');
    await tester.pumpWidget(
      MaterialApp(home: DeveloperModeScreen(api: api)),
    );

    expect(find.text('Developer Mode'), findsOneWidget);
    expect(find.text('Preview change'), findsOneWidget);
    expect(find.text('Approve & Apply'), findsNothing);
    expect(
      find.textContaining('Apply always requires an explicit approval action.'),
      findsOneWidget,
    );
    api.dispose();
  });
}
