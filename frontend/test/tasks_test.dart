import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:sage_one/core/sage_api.dart';
import 'package:sage_one/screens/tasks.dart';

class _TasksApiClient extends http.BaseClient {
  _TasksApiClient({this.includeActiveTask = true});

  final bool includeActiveTask;
  int cancelRequests = 0;
  @override
  
  Future<http.StreamedResponse> send(http.BaseRequest request) async {
    if (request.url.path == '/tasks/task-123/cancel') cancelRequests++;
    final body = switch (request.url.path) {
      '/tasks' => jsonEncode({
          'tasks': [
            {
              'id': 'task-123',
              'title': 'Research: Flutter reliability',
              'status': includeActiveTask ? 'running' : 'completed',
            },
          ],
        }),
      '/tasks/task-123/cancel' => jsonEncode({'success': true}),
      '/tasks/task-123' => jsonEncode({
          'id': 'task-123',
          'title': 'Research: Flutter reliability',
          'status': 'completed',
          'created_at': '2026-09-18T10:00:00Z',
          'updated_at': '2026-09-18T10:01:00Z',
          'result': 'Research completed.',
        }),
      _ => jsonEncode({'detail': 'not found'}),
    };
    final status = request.url.path == '/tasks' ||
            request.url.path == '/tasks/task-123' ||
            request.url.path == '/tasks/task-123/cancel'
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
  testWidgets('Tasks screen renders durable task and opens detail',
      (tester) async {
    final api = SageApi(client: _TasksApiClient(), authToken: 'test-token');
    await tester.pumpWidget(
      MaterialApp(home: TasksScreen(api: api)),
    );
    await tester.pump();

    expect(find.text('Execution queue'), findsOneWidget);
    expect(find.text('Research: Flutter reliability'), findsOneWidget);
    expect(find.text('running • task-123'), findsOneWidget);

    await tester.tap(find.text('Research: Flutter reliability'));
    await tester.pump();
    await tester.pump(const Duration(milliseconds: 250));

    expect(find.text('Task detail'), findsOneWidget);
    expect(find.text('Status'), findsOneWidget);
    expect(find.text('completed'), findsOneWidget);
    expect(find.text('Task ID'), findsOneWidget);
    expect(find.text('Research completed.'), findsOneWidget);
  });
  testWidgets('Cancel task sends a request to the backend', (tester) async {
    final client = _TasksApiClient();
    final api = SageApi(client: client, authToken: 'test-token');
    await tester.pumpWidget(MaterialApp(home: TasksScreen(api: api)));
    await tester.pumpAndSettle();

    await tester.tap(find.byTooltip('Cancel task'));
    await tester.pumpAndSettle();

    expect(client.cancelRequests, 1);
    expect(find.text('Cancellation requested'), findsOneWidget);
    await tester.pumpWidget(const SizedBox.shrink());
    api.dispose();
  });

  testWidgets('Tasks screen shows a useful empty state for filters', (tester) async {
    final api = SageApi(
      client: _TasksApiClient(includeActiveTask: false),
      authToken: 'test-token',
    );
    await tester.pumpWidget(MaterialApp(home: TasksScreen(api: api)));
    await tester.pump();

    await tester.tap(find.byType(DropdownButton<String>));
    await tester.pump();
    await tester.tap(find.text('ACTIVE').last);
    await tester.pump();
    expect(find.text('No tasks match this filter.'), findsOneWidget);
  });
}
