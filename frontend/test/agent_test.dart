import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:sage_one/core/sage_api.dart';
import 'package:sage_one/screens/agent.dart';

class _AgentApiClient extends http.BaseClient {
  int polls = 0;

  @override
  Future<http.StreamedResponse> send(http.BaseRequest request) async {
    final body = switch (request.url.path) {
      '/execute/background' => jsonEncode({'task_id': 'agent-1'}),
      '/tasks/agent-1' => jsonEncode({
          'id': 'agent-1',
          'status': polls++ == 0 ? 'running' : 'completed',
          'result': 'All systems healthy.',
        }),
      _ => jsonEncode({'detail': 'not found'}),
    };
    final status = request.url.path == '/execute/background' ||
            request.url.path == '/tasks/agent-1'
        ? 200
        : 404;
    return http.StreamedResponse(
      Stream.value(utf8.encode(body)),
      status,
      headers: {'content-type': 'application/json'},
      request: request,
    );
  }
}

void main() {
  testWidgets('Agent screen reports system check result', (tester) async {
    final client = _AgentApiClient();
    final api = SageApi(client: client, authToken: 'test-token');
    await tester.pumpWidget(MaterialApp(home: AgentScreen(api: api)));
    await tester.pump();

    final runButton = find.byKey(
      const ValueKey<String>('agent-run-system-check'),
    );
    await tester.scrollUntilVisible(runButton, 500);
    expect(runButton, findsOneWidget);
    await tester.tap(runButton);
    await tester.pump();
    await tester.pump(const Duration(milliseconds: 100));

    expect(find.text('System check running'), findsOneWidget);
    expect(find.text('TASK  agent-1'), findsOneWidget);

    await tester.pump(const Duration(seconds: 5));
    await tester.pump();

    expect(find.text('System check complete'), findsOneWidget);
    expect(find.text('All systems healthy.'), findsOneWidget);
  });
}
