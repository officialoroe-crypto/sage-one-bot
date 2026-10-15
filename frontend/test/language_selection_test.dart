import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:sage_one/screens/language_selection.dart';

void main() {
  testWidgets('selects a language and continues with the choice', (tester) async {
    String? selected;
    await tester.pumpWidget(MaterialApp(
      home: LanguageSelectionScreen(onContinue: (language) => selected = language),
    ));
    expect(find.text('Choose your language.'), findsOneWidget);
    expect(find.text('English'), findsNWidgets(2));
    expect(find.text('नेपाली'), findsOneWidget);
    await tester.tap(find.text('नेपाली'));
    await tester.pump();
    await tester.tap(find.text('Continue'));
    await tester.pump();
    expect(selected, 'Nepali');
  });
}