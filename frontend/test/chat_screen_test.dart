import 'dart:async';
import 'dart:convert';
import 'dart:typed_data';

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:sage_one/core/sage_api.dart';
import 'package:sage_one/screens/feature_workspaces.dart';

class _MissingTaskIdClient extends http.BaseClient {
  @override
  Future<http.StreamedResponse> send(http.BaseRequest request) async {
    final path = request.url.path;
    final dynamic payload = switch ('${request.method} $path') {
      'POST /session' => {'success': true, 'session': {'id': 'session-1'}},
      'POST /command' => {'success': true, 'status': 'queued'},
      _ => {'error': 'not found'},
    };
    final status = path == '/session' || path == '/command' ? 200 : 404;
    return http.StreamedResponse(
      Stream.value(Uint8List.fromList(utf8.encode(jsonEncode(payload)))),
      status,
      headers: {'content-type': 'application/json'},
      request: request,
    );
  }
}


class _DeferredCommandClient extends http.BaseClient {
  final Completer<http.StreamedResponse> commandResponse =
      Completer<http.StreamedResponse>();
  final List<String> requestPaths = <String>[];
  int sessionCount = 0;

  @override
  Future<http.StreamedResponse> send(http.BaseRequest request) async {
    final path = request.url.path;
    requestPaths.add('${request.method} $path');

    if (request.method == 'POST' && path == '/command') {
      return commandResponse.future;
    }

    if (request.method == 'POST' && path == '/session') {
      sessionCount++;
      final payload = {
        'success': true,
        'session': {'id': 'session-$sessionCount'},
      };
      return http.StreamedResponse(
        Stream.value(Uint8List.fromList(utf8.encode(jsonEncode(payload)))),
        200,
        headers: {'content-type': 'application/json'},
        request: request,
      );
    }

    final dynamic payload = switch ('${request.method} $path') {
      'GET /tasks/task-1' => {
          'success': true,
          'task': {'id': 'task-1', 'status': 'running'},
        },
      _ => {'error': 'not found'},
    };
    final status = path == '/tasks/task-1' ? 200 : 404;
    return http.StreamedResponse(
      Stream.value(Uint8List.fromList(utf8.encode(jsonEncode(payload)))),
      status,
      headers: {'content-type': 'application/json'},
      request: request,
    );
  }
}

class _RecoverableChatClient extends http.BaseClient {
  int sessionRequests = 0;
  int historyRequests = 0;

  @override
  Future<http.StreamedResponse> send(http.BaseRequest request) async {
    dynamic payload;
    var status = 200;
    if (request.method == 'POST' && request.url.path == '/session') {
      sessionRequests++;
      if (sessionRequests == 1) {
        status = 503;
        payload = {'detail': 'session temporarily unavailable'};
      } else {
        payload = {'success': true, 'session': {'id': 'session-recovered'}};
      }
    } else if (request.method == 'GET' &&
        request.url.path == '/session/session-recovered/messages') {
      historyRequests++;
      if (historyRequests == 1) {
        status = 503;
        payload = {'detail': 'history temporarily unavailable'};
      } else {
        payload = {
          'success': true,
          'messages': [
            {'role': 'assistant', 'content': 'Recovered chat history'},
          ],
        };
      }
    } else {
      status = 404;
      payload = {'detail': 'not found'};
    }
    return http.StreamedResponse(
      Stream.value(Uint8List.fromList(utf8.encode(jsonEncode(payload)))),
      status,
      headers: {'content-type': 'application/json'},
      request: request,
    );
  }
}

void main() {
  testWidgets('Chat reports a missing task ID instead of remaining stuck', (tester) async {
    final api = SageApi(
      client: _MissingTaskIdClient(),
      baseUrl: 'http://test',
      authToken: 'test-token',
    );
    await tester.pumpWidget(MaterialApp(home: ChatScreen(api: api)));
    await tester.pumpAndSettle();

    await tester.enterText(find.byType(TextField), 'Check SAGE status');
    await tester.tap(find.byIcon(Icons.arrow_upward));
    await tester.pumpAndSettle();

    expect(find.text('Could not queue command'), findsOneWidget);
    expect(tester.widget<TextField>(find.byType(TextField)).enabled, isTrue);
    expect(tester.widget<TextField>(find.byType(TextField)).controller!.text,
        'Check SAGE status');
    expect(find.text('Retry'), findsOneWidget);
  });

  testWidgets('Chat offers retry for session startup and history failures', (tester) async {
    final client = _RecoverableChatClient();
    final api = SageApi(
      client: client,
      baseUrl: 'http://test',
      authToken: 'test-token',
    );
    await tester.pumpWidget(MaterialApp(home: ChatScreen(api: api)));
    await tester.pumpAndSettle();

    expect(find.textContaining('Could not start chat.'), findsOneWidget);
    await tester.tap(find.text('Retry'));
    await tester.pumpAndSettle();
    expect(client.sessionRequests, 2);
    expect(find.textContaining('Could not start chat.'), findsNothing);

    await tester.tap(find.byTooltip('Refresh chat history'));
    await tester.pumpAndSettle();
    expect(find.textContaining('Chat history could not load.'), findsOneWidget);
    await tester.tap(find.text('Retry'));
    await tester.pumpAndSettle();

    expect(client.historyRequests, 2);
    expect(find.text('Recovered chat history'), findsOneWidget);
    expect(find.textContaining('Chat history could not load.'), findsNothing);
    await tester.pumpWidget(const SizedBox.shrink());
    api.dispose();
  });
  
  testWidgets('Chat does not poll a task when a command returns after disposal',
      (tester) async {
    final client = _DeferredCommandClient();
    final api = SageApi(
      client: client,
      baseUrl: 'http://test',
      authToken: 'test-token',
    );
    await tester.pumpWidget(MaterialApp(home: ChatScreen(api: api)));
    await tester.pumpAndSettle();

    await tester.enterText(find.byType(TextField), 'Queue a command');
    await tester.tap(find.byIcon(Icons.arrow_upward));
    await tester.pump();

    expect(client.requestPaths, contains('POST /command'));

    // Simulate leaving the screen while submitCommand is still awaiting HTTP.
    await tester.pumpWidget(const SizedBox.shrink());
    client.commandResponse.complete(http.StreamedResponse(
      Stream.value(Uint8List.fromList(utf8.encode(jsonEncode({
        'success': true,
        'task': {'id': 'task-1', 'status': 'queued'},
      })))),
      200,
      headers: {'content-type': 'application/json'},
    ));

    await tester.pump();
    await tester.pump(const Duration(seconds: 3));
    expect(client.requestPaths, isNot(contains('GET /tasks/task-1')));
    expect(tester.takeException(), isNull);
    api.dispose();
  });

  testWidgets(
    'Chat ignores a pending command after the user starts a new session',
    (tester) async {
      final client = _DeferredCommandClient();
      final api = SageApi(
        client: client,
        baseUrl: 'http://test',
        authToken: 'test-token',
      );
      await tester.pumpWidget(MaterialApp(home: ChatScreen(api: api)));
      await tester.pumpAndSettle();
      expect(client.sessionCount, 1);

      await tester.enterText(find.byType(TextField), 'Queue a command');
      await tester.tap(find.byIcon(Icons.arrow_upward));
      await tester.pump();
      expect(client.requestPaths, contains('POST /command'));

      // Start another conversation before the first command response arrives.
      await tester.tap(find.byIcon(Icons.add_comment_outlined));
      await tester.pumpAndSettle();
      expect(client.sessionCount, 2);
      expect(find.text('Queue a command'), findsNothing);

      client.commandResponse.complete(http.StreamedResponse(
        Stream.value(Uint8List.fromList(utf8.encode(jsonEncode({
          'success': true,
          'task': {'id': 'task-1', 'status': 'queued'},
        })))),
        200,
        headers: {'content-type': 'application/json'},
      ));

      await tester.pump();
      await tester.pump(const Duration(seconds: 3));
      expect(client.requestPaths, isNot(contains('GET /tasks/task-1')));
      expect(find.text('Queue a command'), findsNothing);
      expect(tester.takeException(), isNull);

      await tester.pumpWidget(const SizedBox.shrink());
      api.dispose();
    },
  );


}
