import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:sage_one/core/sage_api.dart';
import 'package:sage_one/screens/research.dart';

class _ResearchApiClient extends http.BaseClient {
  int polls = 0;
  int cancelRequests = 0;

  @override
  Future<http.StreamedResponse> send(http.BaseRequest request) async {
    if (request.url.path == '/tasks/research-1/cancel') {
      cancelRequests++;
      return _json(request, {'success': true});
    }
    if (request.url.path == '/execute/background') {
      return _json(request, {'task_id': 'research-1'});
    }
    if (request.url.path == '/tasks/research-1') {
      return _json(request, {
        'id': 'research-1',
        'status': polls++ == 0 ? 'running' : 'completed',
        'result': 'Evidence report ready.',
      });
    }
    if (request.url.path == '/tools/execute') {
      final tool = request.url.queryParameters['tool_name'];
      if (tool == 'research_list') {
        return _json(request, {
          'result': [
            {
              'research_id': 'report-1',
              'question': 'Source validation',
              'summary': 'Verified report',
              'source_count': 3,
              'claim_count': 1,
              'status': 'completed',
            },
          ],
        });
      }
      if (tool == 'research_get') {
        return _json(request, {
          'result': {
            'research_id': 'report-1',
            'question': 'Source validation',
            'report': {
              'summary': 'Verified report',
              'claims': [
                {'claim': 'Claim A', 'status': 'verified'},
              ],
              'sources': [
                {'title': 'Safe source', 'url': 'https://example.com/article'},
                {'title': 'Blocked source', 'url': 'javascript:alert(1)'},
                {'title': 'Missing source'},
              ],
            },
          },
        });
      }
    }
    return _json(request, {'detail': 'not found'}, status: 404);
  }

  http.StreamedResponse _json(
    http.BaseRequest request,
    Map<String, dynamic> body, {
    int status = 200,
  }) {
    return http.StreamedResponse(
      Stream.value(utf8.encode(jsonEncode(body))),
      status,
      headers: {'content-type': 'application/json'},
      request: request,
    );
  }
}

void main() {
  testWidgets('Research screen queues and displays task result', (tester) async {
    final api = SageApi(client: _ResearchApiClient(), authToken: 'test-token');
    await tester.pumpWidget(
      MaterialApp(home: Scaffold(body: ResearchScreen(api: api))),
    );
    await tester.pump();

    await tester.enterText(find.byType(TextField), 'Flutter reliability');
    await tester.tap(find.byIcon(Icons.arrow_upward));
    await tester.pump();
    await tester.pump(const Duration(milliseconds: 100));

    expect(find.text('Research in progress'), findsOneWidget);
    expect(find.text('TASK  research-1'), findsOneWidget);

    await tester.pump(const Duration(seconds: 5));
    await tester.pump();

    expect(find.text('Research complete'), findsOneWidget);
    expect(find.text('Evidence report ready.'), findsOneWidget);
  });

  testWidgets('Research cancel button reaches the task cancellation API', (tester) async {
    final client = _ResearchApiClient();
    final api = SageApi(client: client, authToken: 'test-token');
    await tester.pumpWidget(
      MaterialApp(home: Scaffold(body: ResearchScreen(api: api))),
    );
    await tester.pump();

    await tester.enterText(find.byType(TextField), 'Cancel this research');
    await tester.tap(find.byIcon(Icons.arrow_upward));
    await tester.pump();
    await tester.pump(const Duration(milliseconds: 100));
    expect(find.text('CANCEL'), findsOneWidget);

    await tester.tap(find.text('CANCEL'));
    await tester.pump();
    await tester.pump(const Duration(milliseconds: 100));

    expect(client.cancelRequests, 1);
    expect(tester.takeException(), isNull);
    await tester.pumpWidget(const SizedBox.shrink());
    api.dispose();
  });

  test('Research source validator accepts only HTTP(S) URLs', () {
    expect(
      researchSourceUri({'url': 'https://example.com/article'}).toString(),
      'https://example.com/article',
    );
    expect(
      researchSourceUri({'url': 'http://example.com/article'}).toString(),
      'http://example.com/article',
    );
    expect(researchSourceUri({'url': 'javascript:alert(1)'}), isNull);
    expect(researchSourceUri({'url': 'file:///tmp/report'}), isNull);
    expect(researchSourceUri({'title': 'Missing source'}), isNull);
    expect(researchSourceUri({'url': 'https:///missing-host'}), isNull);
  });}
