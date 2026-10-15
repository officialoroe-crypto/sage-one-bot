import 'dart:convert';
import 'dart:typed_data';

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:sage_one/core/sage_api.dart';
import 'package:sage_one/screens/learning.dart';

class _LearningClient extends http.BaseClient {
  final Set<String> completedLessons = <String>{};
  final List<String> requests = <String>[];
  bool failPathRead = false;

  @override
  Future<http.StreamedResponse> send(http.BaseRequest request) async {
    final method = request.method;
    final path = request.url.path;
    requests.add('$method $path');
    dynamic payload;
    var status = 200;

    if (method == 'GET' && path == '/learning/paths') {
      if (failPathRead) {
        status = 503;
        payload = {'detail': 'learning service temporarily unavailable'};
      } else {
        final completed = completedLessons.contains('digital-files-and-documents');
        payload = {
          'success': true,
          'paths': [
            {
              'id': 'digital-foundations',
              'title': 'Digital Foundations',
              'subtitle': 'Practical digital skills',
              'level': 'Beginner',
              'estimated_minutes': 8,
              'lessons': [
                {
                  'id': 'digital-files-and-documents',
                  'title': 'Files, folders and documents',
                  'minutes': 8,
                  'objective': 'Organize your work so it is easy to find and share.',
                  'content': 'Create one folder for each project and use descriptive names.',
                  'exercise': 'Create a project folder and name one document clearly.',
                  'is_completed': completed,
                  'completed_at': completed ? '2026-10-10T00:00:00Z' : null,
                },
              ],
              'completed_lessons': completed ? 1 : 0,
              'total_lessons': 1,
              'progress_ratio': completed ? 1.0 : 0.0,
              'is_completed': completed,
            },
          ],
        };
      }
    } else if (method == 'POST' &&
        path == '/learning/lessons/digital-files-and-documents/complete') {
      completedLessons.add('digital-files-and-documents');
      payload = {
        'success': true,
        'lesson': {
          'id': 'digital-files-and-documents',
          'title': 'Files, folders and documents',
          'is_completed': true,
          'completed_at': '2026-10-10T00:00:00Z',
        },
        'message': 'Lesson marked complete.',
      };
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
  testWidgets('Learning screen loads a lesson and saves completed progress', (tester) async {
    final client = _LearningClient();
    final api = SageApi(client: client, baseUrl: 'http://test', authToken: 'test-token');
    await tester.pumpWidget(MaterialApp(home: LearningScreen(api: api)));
    await tester.pumpAndSettle();

    expect(find.text('Digital Foundations'), findsOneWidget);
    expect(find.text('0 of 1 lessons • Beginner • 8 min'), findsOneWidget);

    await tester.tap(find.text('Digital Foundations'));
    await tester.pumpAndSettle();
    await tester.tap(find.text('Files, folders and documents'));
    await tester.pumpAndSettle();

    expect(find.text('Organize your work so it is easy to find and share.'), findsOneWidget);
    expect(find.text('Create a project folder and name one document clearly.'), findsOneWidget);
    await tester.tap(find.text('Mark complete'));
    await tester.pumpAndSettle();

    expect(client.requests, contains('POST /learning/lessons/digital-files-and-documents/complete'));
    expect(find.text('1 of 1 lessons • Beginner • 8 min'), findsOneWidget);
    await tester.tap(find.text('Files, folders and documents'));
    await tester.pumpAndSettle();
    expect(find.text('Completed'), findsOneWidget);

    await tester.pumpWidget(const SizedBox.shrink());
    api.dispose();
  });

  testWidgets('Learning path load failure exposes Retry and recovers', (tester) async {
    final client = _LearningClient()..failPathRead = true;
    final api = SageApi(client: client, baseUrl: 'http://test', authToken: 'test-token');
    await tester.pumpWidget(MaterialApp(home: LearningScreen(api: api)));
    await tester.pumpAndSettle();

    expect(find.text('Learning paths could not load'), findsOneWidget);
    client.failPathRead = false;
    await tester.tap(find.text('Retry'));
    await tester.pumpAndSettle();

    expect(find.text('Learning paths could not load'), findsNothing);
    expect(find.text('Digital Foundations'), findsOneWidget);
    expect(client.requests.where((request) => request == 'GET /learning/paths').length, 2);

    await tester.pumpWidget(const SizedBox.shrink());
    api.dispose();
  });
}
