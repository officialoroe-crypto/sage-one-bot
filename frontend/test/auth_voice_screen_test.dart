import 'dart:convert';
import 'dart:typed_data';

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:sage_one/core/identity_client.dart';
import 'package:sage_one/core/sage_api.dart';
import 'package:sage_one/screens/auth_gate.dart';
import 'package:sage_one/screens/login.dart';
import 'package:sage_one/screens/memory.dart';
import 'package:sage_one/screens/private_owner_gate.dart';
import 'package:sage_one/screens/voice_command.dart';
import 'package:sage_one/screens/voice_mode.dart';

class _ConfigClient extends http.BaseClient {
  @override
  Future<http.StreamedResponse> send(http.BaseRequest request) async {
    final body = request.url.path == '/identity/config'
        ? {'success': true, 'developer_mode': true}
        : {'success': true};
    return http.StreamedResponse(
      Stream.value(Uint8List.fromList(utf8.encode(jsonEncode(body)))),
      200,
      headers: {'content-type': 'application/json'},
      request: request,
    );
  }
}

class _ExistingSessionIdentity extends IdentityClient {
  _ExistingSessionIdentity()
      : super(client: _ConfigClient(), baseUrl: 'http://test');

  @override
  Future<String?> token() async => 'existing-test-token';

  @override
  Future<Map<String, dynamic>> devLogin({String label = 'local-owner'}) async =>
      {'success': true, 'token': 'test-token'};

  @override
  void dispose() {}
}


class _ExpiredSessionIdentity extends IdentityClient {
  _ExpiredSessionIdentity()
      : super(client: _ConfigClient(), baseUrl: 'http://test');

  @override
  Future<String?> token() async => 'expired-token';

  @override
  Future<Map<String, dynamic>> me() async => throw Exception('expired token');

  @override
  Future<void> signOut() async => throw Exception('provider sign-out failed');

  @override
  void dispose() {}
}

class _ApiClient extends http.BaseClient {
  final List<String> requestPaths = <String>[];

  @override
  Future<http.StreamedResponse> send(http.BaseRequest request) async {
    requestPaths.add(request.url.path);
    return http.StreamedResponse(
      Stream.value(Uint8List.fromList(utf8.encode(jsonEncode({'success': true})))),
      200,
      headers: {'content-type': 'application/json'},
      request: request,
    );
  }
}

SageApi _api() => SageApi(
  client: _ApiClient(),
  baseUrl: 'http://test',
  authToken: 'test-token',
);

void main() {
  test('Identity and SAGE clients share the Android emulator API default', () {
    final identity = IdentityClient(client: _ConfigClient());
    final api = SageApi(client: _ApiClient());

    expect(identity.baseUrl, 'http://10.0.2.2:8010');
    expect(api.baseUrl, identity.baseUrl);

    identity.dispose();
    api.dispose();
  });

  testWidgets('Login uses the private owner entry when backend developer mode is enabled', (tester) async {
    final identity = IdentityClient(client: _ConfigClient(), baseUrl: 'http://test');
    await tester.pumpWidget(MaterialApp(
      home: LoginScreen(identity: identity, onSignedIn: (_) {}),
    ));
    await tester.pumpAndSettle();

    expect(find.text('Enter SAGE Owner Mode'), findsOneWidget);
    expect(find.textContaining('no Google, SMS or OTP required'), findsOneWidget);

    await tester.pumpWidget(const SizedBox.shrink());
    identity.dispose();
  });


  testWidgets('AuthGate returns to login when provider sign-out fails', (tester) async {
    final identity = _ExpiredSessionIdentity();
    await tester.pumpWidget(MaterialApp(
      home: AuthGate(
        identity: identity,
        childBuilder: (_) => const Scaffold(body: Text('Inside SAGE')),
      ),
    ));
    await tester.pump(const Duration(seconds: 1));
    await tester.pumpAndSettle();

    expect(find.text('Enter SAGE Owner Mode'), findsOneWidget);
    expect(find.text('Inside SAGE'), findsNothing);
    expect(tester.takeException(), isNull);

    await tester.pumpWidget(const SizedBox.shrink());
  });

  testWidgets('Private owner gate enters the supplied workspace with an existing session', (tester) async {
    final identity = _ExistingSessionIdentity();
    await tester.pumpWidget(MaterialApp(
      home: PrivateOwnerGate(
        identity: identity,
        child: const Scaffold(body: Center(child: Text('Inside SAGE'))),
      ),
    ));
    await tester.pumpAndSettle();

    expect(find.text('Inside SAGE'), findsOneWidget);
  });

  testWidgets('Voice command screen handles unavailable platform voice services without crashing', (tester) async {
    await tester.pumpWidget(MaterialApp(home: VoiceCommandScreen(api: _api())));
    await tester.pump(const Duration(milliseconds: 500));

    expect(find.byType(Scaffold), findsOneWidget);
    expect(tester.takeException(), isNull);
  });

  testWidgets('Voice mode screen handles unavailable platform voice services without crashing', (tester) async {
    await tester.pumpWidget(MaterialApp(home: SageVoiceScreen(api: _api())));
    await tester.pump(const Duration(milliseconds: 500));

    expect(find.byType(Scaffold), findsOneWidget);
    expect(tester.takeException(), isNull);
  });

  testWidgets('Saving a memory calls the identity API', (tester) async {
    final client = _ApiClient();
    final api = SageApi(
      client: client,
      baseUrl: 'http://test',
      authToken: 'test-token',
    );
    await tester.pumpWidget(MaterialApp(home: MemoryScreen(api: api)));
    await tester.pumpAndSettle();

    await tester.tap(find.text('Add memory'));
    await tester.pumpAndSettle();
    await tester.enterText(find.byType(TextField).last, 'SAGE should remember this');
    await tester.tap(find.text('Save memory'));
    await tester.pumpAndSettle();

    expect(client.requestPaths, contains('/identity/memory'));
    expect(tester.takeException(), isNull);
    await tester.pumpWidget(const SizedBox.shrink());
    api.dispose();
  });

  testWidgets('Memory screen renders saved-memory controls and opens its add dialog', (tester) async {
    await tester.pumpWidget(MaterialApp(home: MemoryScreen(api: _api())));
    await tester.pumpAndSettle();

    expect(find.text('PERSONAL MEMORY'), findsOneWidget);
    expect(find.text('What SAGE remembers'), findsOneWidget);
    await tester.tap(find.text('Add memory'));
    await tester.pumpAndSettle();
    expect(find.text('Add a memory'), findsOneWidget);

    await tester.enterText(find.byType(TextField).last, 'Remember this preference');
    await tester.pump();
    final saveButton = tester.widget<FilledButton>(
      find.widgetWithText(FilledButton, 'Save memory'),
    );
    expect(saveButton.onPressed, isNotNull);

    await tester.tap(find.text('Cancel'));
    await tester.pumpAndSettle();
    expect(find.text('Add a memory'), findsNothing);
    expect(tester.takeException(), isNull);
  });

}
