import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:sage_one/core/sage_api.dart';
import 'package:sage_one/screens/evolution.dart';

class _EvolutionClient extends http.BaseClient {
  bool failEconomy = false;
  bool returnEmptyTiers = false;
  int economyRequests = 0;
  int tierRequests = 0;
  String currentTier = 'Silver';

  @override
  Future<http.StreamedResponse> send(http.BaseRequest request) async {
    final path = request.url.path;
    var status = 200;
    dynamic body;

    if (path == '/economy/me') {
      economyRequests++;
      if (failEconomy) {
        status = 503;
        body = {'detail': 'economy service unavailable'};
      } else {
        body = {
          'success': true,
          'spark': {'balance': 125},
          'evolution': {
            'lifetime_achievement': currentTier == 'Californium Overlord' ? 15000 : 250,
            'tier': currentTier,
            'progress': currentTier == 'Californium Overlord'
                ? {
                    'current_threshold': 10000,
                    'next_threshold': null,
                    'next_tier': null,
                    'ratio': 1.4,
                  }
                : {
                    'current_threshold': 100,
                    'next_threshold': 1000,
                    'next_tier': 'Gold',
                    'ratio': 0.25,
                  },
          },
        };
      }
    } else if (path == '/economy/evolution/tiers') {
      tierRequests++;
      body = {
        'success': true,
        'tiers': returnEmptyTiers
            ? <Map<String, dynamic>>[]
            : [
                {'tier': 'Bronze', 'threshold': 0, 'order': 1},
                {'tier': 'Silver', 'threshold': 100, 'order': 2},
                {'tier': 'Gold', 'threshold': 1000, 'order': 3},
                {
                  'tier': 'Californium Overlord',
                  'threshold': 10000,
                  'order': 13,
                },
              ],
      };
    } else {
      status = 404;
      body = {'detail': 'unexpected route: $path'};
    }

    return http.StreamedResponse(
      Stream.value(utf8.encode(jsonEncode(body))),
      status,
      headers: {'content-type': 'application/json'},
    );
  }
}

void main() {
  testWidgets('Evolution dashboard renders backend tier, XP progress, and rank catalog', (tester) async {
    final client = _EvolutionClient();
    final api = SageApi(
      client: client,
      baseUrl: 'http://test',
      authToken: 'test-token',
    );

    await tester.pumpWidget(MaterialApp(home: EvolutionScreen(api: api)));
    await tester.pumpAndSettle();

    expect(client.economyRequests, 1);
    expect(client.tierRequests, 1);
    expect(find.text('CURRENT RANK'), findsOneWidget);
    expect(find.text('SILVER'), findsOneWidget);
    expect(find.text('250 XP'), findsOneWidget);
    expect(find.text('750 XP to Gold'), findsOneWidget);
    expect(find.text('Next milestone: Gold at 1000 XP'), findsOneWidget);
    await tester.scrollUntilVisible(find.textContaining('Bronze'), 250);
    expect(find.textContaining('Bronze'), findsOneWidget);
    expect(find.text('UNLOCKED'), findsOneWidget);

    await tester.scrollUntilVisible(find.textContaining('Silver'), 250);
    expect(find.textContaining('Silver'), findsOneWidget);
    expect(find.text('CURRENT'), findsOneWidget);

    await tester.scrollUntilVisible(find.textContaining('Gold'), 250);
    expect(find.textContaining('Gold'), findsWidgets);
    expect(find.text('LOCKED'), findsNWidgets(2));

    await tester.pumpWidget(const SizedBox.shrink());
    api.dispose();
  });

  testWidgets('Evolution error state retries both backend requests', (tester) async {
    final client = _EvolutionClient()..failEconomy = true;
    final api = SageApi(
      client: client,
      baseUrl: 'http://test',
      authToken: 'test-token',
    );

    await tester.pumpWidget(MaterialApp(home: EvolutionScreen(api: api)));
    await tester.pumpAndSettle();

    expect(find.text('Evolution is unavailable'), findsOneWidget);
    expect(find.text('Try again'), findsOneWidget);
    expect(client.economyRequests, 1);
    expect(client.tierRequests, 1);

    client.failEconomy = false;
    await tester.tap(find.text('Try again'));
    await tester.pumpAndSettle();

    expect(client.economyRequests, 2);
    expect(client.tierRequests, 2);
    expect(find.text('SILVER'), findsOneWidget);

    await tester.pumpWidget(const SizedBox.shrink());
    api.dispose();
  });

  testWidgets('Evolution safely handles a missing tier catalog', (tester) async {
    final client = _EvolutionClient()..returnEmptyTiers = true;
    final api = SageApi(
      client: client,
      baseUrl: 'http://test',
      authToken: 'test-token',
    );

    await tester.pumpWidget(MaterialApp(home: EvolutionScreen(api: api)));
    await tester.pumpAndSettle();

    expect(find.text('The rank catalog is not available yet. Pull to refresh.'), findsOneWidget);
    expect(find.text('SILVER'), findsOneWidget);

    await tester.pumpWidget(const SizedBox.shrink());
    api.dispose();
  });

  testWidgets('Evolution shows MAX rank without negative progress', (tester) async {
    final client = _EvolutionClient()..currentTier = 'Californium Overlord';
    final api = SageApi(
      client: client,
      baseUrl: 'http://test',
      authToken: 'test-token',
    );

    await tester.pumpWidget(MaterialApp(home: EvolutionScreen(api: api)));
    await tester.pumpAndSettle();

    expect(find.text('CALIFORNIUM OVERLORD'), findsOneWidget);
    expect(find.text('MAX RANK'), findsNWidgets(2));
    expect(
      tester.widget<LinearProgressIndicator>(find.byType(LinearProgressIndicator)).value,
      1.0,
    );
    expect(find.text('Next milestone: Gold at 1000 XP'), findsNothing);

    await tester.pumpWidget(const SizedBox.shrink());
    api.dispose();
  });
}
