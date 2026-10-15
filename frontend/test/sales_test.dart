import 'dart:convert';
import 'dart:typed_data';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:sage_one/core/sage_api.dart';
import 'package:sage_one/screens/sales.dart';

class _SalesClient extends http.BaseClient {
  final List<String> requestPaths = <String>[];
  int followUpRequests = 0;
  bool failFollowUp = false;
  final List<Map<String, dynamic>> followUpPayloads = <Map<String, dynamic>>[];

  @override
  Future<http.StreamedResponse> send(http.BaseRequest request) async {
    requestPaths.add(request.url.path);
    var status = 200;
    dynamic body;
    if (request.method == 'POST' &&
        request.url.path == '/sales/leads/lead-1/follow-up') {
      followUpRequests++;
      if (request is http.Request) {
        followUpPayloads.add(
          Map<String, dynamic>.from(jsonDecode(request.body) as Map),
        );
      }
      if (failFollowUp) {
        status = 503;
        body = {'detail': 'follow-up service temporarily unavailable'};
      } else {
        body = {'success': true};
      }
    } else if (request.url.path == '/sales/leads') {
      body = {'success': true, 'leads': [{
        'id': 'lead-1', 'business_name': 'Demo Hardware', 'website': 'https://example.com',
        'score': 42, 'tier': 'hot', 'status': 'outreach_pending',
        'audit_json': jsonEncode({'gaps': ['clear_cta']}),
        'outreach_json': jsonEncode({'draft': 'Demo outreach', 'requires_approval': true}),
      }]};
    } else if (request.url.path == '/sales/leads/lead-1') {
      body = {'success': true, 'lead': {
        'id': 'lead-1', 'business_name': 'Demo Hardware', 'website': 'https://example.com',
        'score': 42, 'tier': 'hot', 'status': 'outreach_pending',
        'audit_json': jsonEncode({'gaps': ['clear_cta']}),
        'outreach_json': jsonEncode({'draft': 'Demo outreach', 'requires_approval': true}),
      }};
    } else if (request.url.path == '/sales/leads/lead-1/history') {
      body = {'success': true, 'history': [{'event_type': 'discovered_audited_scored', 'status': 'completed', 'created_at': '2026-10-09T00:00:00Z'}]};
    } else {
      body = {'success': true};
    }
    final bytes = Uint8List.fromList(utf8.encode(jsonEncode(body)));
    return http.StreamedResponse(
      Stream.value(bytes),
      status,
      headers: {'content-type': 'application/json'},
      request: request,
    );
  }
}

void main() {
  testWidgets('sales pipeline renders a lead and opens its detail', (tester) async {
    final client = _SalesClient();
    final api = SageApi(client: client, baseUrl: 'http://test', authToken: 'test');
    await tester.pumpWidget(MaterialApp(home: SalesScreen(api: api)));
    await tester.pumpAndSettle();
    expect(find.text('Lead pipeline'), findsOneWidget);
    expect(find.text('Demo Hardware'), findsOneWidget);
    await tester.tap(find.text('Demo Hardware'));
    await tester.pumpAndSettle();
    expect(find.text('Outreach draft'), findsOneWidget);
    expect(find.text('Approve outreach'), findsOneWidget);
    expect(find.text('Record follow-up'), findsOneWidget);
    expect(find.text('Activity history'), findsOneWidget);

    await tester.tap(find.text('Record follow-up'));
    await tester.pumpAndSettle();
    expect(find.text('What happened / next step'), findsOneWidget);
    final saveButton = find.widgetWithText(FilledButton, 'Save');
    expect(tester.widget<FilledButton>(saveButton).onPressed, isNull);
    await tester.enterText(find.byType(TextField), 'Called the business; follow up tomorrow.');
    await tester.pump();
    expect(tester.widget<FilledButton>(saveButton).onPressed, isNotNull);
    await tester.tap(saveButton);
    await tester.pumpAndSettle();
    expect(client.requestPaths, contains('/sales/leads/lead-1/follow-up'));
    expect(tester.takeException(), isNull);

    await tester.tap(find.text('Approve outreach'));
    await tester.pumpAndSettle();
    expect(client.requestPaths, contains('/sales/leads/lead-1/approve-outreach'));
  });
  testWidgets('sales follow-up remains editable and retries after a backend failure',
      (tester) async {
    final client = _SalesClient()..failFollowUp = true;
    final api = SageApi(
      client: client,
      baseUrl: 'http://test',
      authToken: 'test-token',
    );
    await tester.pumpWidget(MaterialApp(home: SalesScreen(api: api)));
    await tester.pumpAndSettle();

    await tester.tap(find.text('Demo Hardware'));
    await tester.pumpAndSettle();
    await tester.tap(find.text('Record follow-up'));
    await tester.pumpAndSettle();
    const note = 'Called the business; send updated quote tomorrow.';
    await tester.enterText(find.byType(TextField), note);
    await tester.pump();
    await tester.tap(find.widgetWithText(FilledButton, 'Save'));
    await tester.pumpAndSettle();

    expect(find.textContaining('Follow-up failed:'), findsOneWidget);
    expect(tester.widget<TextField>(find.byType(TextField)).controller!.text, note);
    expect(client.followUpRequests, 1);

    client.failFollowUp = false;
    await tester.tap(find.widgetWithText(FilledButton, 'Save'));
    await tester.pumpAndSettle();

    expect(client.followUpRequests, 2);
    expect(client.followUpPayloads.last['note'], note);
    expect(find.text('What happened / next step'), findsNothing);
    expect(tester.takeException(), isNull);

    await tester.pumpWidget(const SizedBox.shrink());
    api.dispose();
  });

}
