import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:sage_one/screens/splash.dart';

void main() {
  testWidgets('shows SAGE branding then enters the existing app', (tester) async {
    await tester.pumpWidget(
      const MaterialApp(
        home: SageSplashScreen(
          duration: Duration(milliseconds: 400),
          child: Scaffold(body: Text('EXISTING APP')),
        ),
      ),
    );

    expect(find.text('SAGE ONE'), findsOneWidget);
    expect(find.text('YOUR PERSONAL AI MENTOR & EXECUTION PARTNER'), findsOneWidget);
    expect(find.text('EXISTING APP'), findsNothing);

    await tester.pump(const Duration(milliseconds: 450));
    await tester.pump();

    expect(find.text('EXISTING APP'), findsOneWidget);
  });
}
