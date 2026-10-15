import 'dart:convert';
import 'dart:typed_data';

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:sage_one/core/sage_api.dart';
import 'package:sage_one/main.dart';

class _NavigationClient extends http.BaseClient {
  @override
  Future<http.StreamedResponse> send(http.BaseRequest request) async {
    final payload = switch (request.url.path) {
      '/notifications' => {'success': true, 'notifications': <dynamic>[]},
      '/worker/health' => {'success': true, 'worker': {'running': false}},
      '/learning/paths' => {
        'success': true,
        'paths': [
          {
            'id': 'digital-foundations',
            'title': 'Digital Foundations',
            'subtitle': 'Practical digital skills',
            'level': 'Beginner',
            'estimated_minutes': 20,
            'lessons': [],
            'completed_lessons': 0,
            'total_lessons': 0,
            'progress_ratio': 0.0,
            'is_completed': false,
          },
        ],
      },
      _ => {'success': true, 'items': <dynamic>[]},
    };
    return http.StreamedResponse(
      Stream.value(Uint8List.fromList(utf8.encode(jsonEncode(payload)))),
      200,
      headers: {'content-type': 'application/json'},
      request: request,
    );
  }
}

class _MenuRouteCase {
  const _MenuRouteCase(this.title, this.firstAction);
  final String title;
  final String firstAction;
}

void main() {
  testWidgets(
    'More menu navigates to Community placeholder',
    (tester) async {
      const routes = <_MenuRouteCase>[
        _MenuRouteCase('Community', 'Open community'),
      ];

      for (final route in routes) {
        final api = SageApi(
          client: _NavigationClient(),
          baseUrl: 'http://test',
          authToken: 'test-token',
        );
        await tester.pumpWidget(MaterialApp(home: SageOneShell(api: api)));
        // CommandCenter contains an intentionally repeating animation, so use
        // bounded pumps rather than pumpAndSettle while the shell is mounted.
        await tester.pump(const Duration(milliseconds: 300));

        await tester.tap(find.text('More'));
        await tester.pump();
        await tester.pump(const Duration(milliseconds: 400));

        final menuItem = find.widgetWithText(ListTile, route.title);
        expect(menuItem, findsOneWidget, reason: 'More menu should expose ${route.title}');
        await tester.ensureVisible(menuItem);
        await tester.pump(const Duration(milliseconds: 300));
        await tester.tap(menuItem);
        await tester.pump();
        await tester.pump(const Duration(milliseconds: 400));

        expect(find.text('Integration status'), findsOneWidget);
        expect(
          find.text('Interface available • Live actions not connected yet'),
          findsOneWidget,
        );
        await tester.ensureVisible(find.text(route.firstAction));
        await tester.tap(find.text(route.firstAction));
        await tester.pump();
        await tester.pump(const Duration(milliseconds: 300));

        expect(
          find.textContaining('not connected to a live workflow yet'),
          findsOneWidget,
          reason: 'The ${route.title} action should not pretend to complete work.',
        );
        await tester.tap(find.text('Understood'));
        await tester.pump();
        await tester.pump(const Duration(milliseconds: 300));

        await tester.pumpWidget(const SizedBox.shrink());
        api.dispose();
      }
    },
  );

  testWidgets('More menu opens the connected Learning paths screen', (tester) async {
    final api = SageApi(
      client: _NavigationClient(),
      baseUrl: 'http://test',
      authToken: 'test-token',
    );
    await tester.pumpWidget(MaterialApp(home: SageOneShell(api: api)));
    // The command-center surface contains a repeating animation.
    await tester.pump(const Duration(milliseconds: 300));

    await tester.tap(find.text('More'));
    await tester.pump();
    await tester.pump(const Duration(milliseconds: 400));
    final learningItem = find.widgetWithText(ListTile, 'Learning');
    expect(learningItem, findsOneWidget);
    await tester.ensureVisible(learningItem);
    await tester.tap(learningItem);
    await tester.pump();
    await tester.pump(const Duration(milliseconds: 400));

    expect(find.text('Digital Foundations'), findsOneWidget);
    expect(find.text('Integration status'), findsNothing);

    await tester.pumpWidget(const SizedBox.shrink());
    api.dispose();
  });
}
