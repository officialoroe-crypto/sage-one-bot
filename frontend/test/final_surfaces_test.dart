import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;

import 'package:sage_one/core/sage_api.dart';
import 'package:sage_one/screens/final_surfaces.dart';
import 'package:sage_one/theme/sage_theme.dart';

class _FinalSurfaceClient extends http.BaseClient {
  int markAllReadRequests = 0;
  int profilePatchRequests = 0;
  Map<String, dynamic>? lastProfilePatch;
  String? lastProfileAuthorization;
  int profileGetRequests = 0;
  int markReadRequests = 0;
  int economyGetRequests = 0;
  int notificationGetRequests = 0;
  int paymentStatusGetRequests = 0;
  int tasksGetRequests = 0;
  int workspaceGetRequests = 0;
  bool failProfileLoad = false;
  bool failEconomyLoad = false;
  bool failNotificationLoad = false;
  bool failPaymentStatusLoad = false;
  bool failTasksLoad = false;
  bool failWorkspaceLoad = false;
  bool includeArtifact = false;
  @override
  Future<http.StreamedResponse> send(http.BaseRequest request) async {
    final path = request.url.path;
    if (path == '/notifications/read-all') markAllReadRequests++;
    if (path == '/notifications/notice-1/read') markReadRequests++;
    if (path == '/identity/me' && request.method == 'PATCH') {
      profilePatchRequests++;
      lastProfileAuthorization = request.headers['authorization'];
      final requestBytes = await request.finalize().toBytes();
      lastProfilePatch =
          jsonDecode(utf8.decode(requestBytes)) as Map<String, dynamic>;
    }
    if (path == '/identity/me' && request.method == 'GET') profileGetRequests++;
    var status = 200;
    dynamic body = <String, dynamic>{'success': true};

    if (path == '/economy/me') {
      body = {
        'success': true,
        'spark': {'balance': 125, 'lifetime_earned': 200, 'lifetime_spent': 75},
        'ledger': [
          {'reason': 'Test grant', 'delta': 125, 'created_at': '2026-10-08T00:00:00Z'}
        ],
        'evolution': {
          'lifetime_achievement': 250,
          'tier': 'Silver',
          'stage': 'LOW',
          'progress': {
            'current_threshold': 0,
            'next_threshold': 1000,
            'next_tier': 'Silver',
            'ratio': 0.25
          }
        }
      };
    } else if (path == '/economy/evolution/tiers') {
      body = {
        'success': true,
        'tiers': [
          {'tier': 'Bronze', 'threshold': 0, 'order': 1},
          {'tier': 'Silver', 'threshold': 1000, 'order': 2}
        ]
      };
    } else if (path == '/identity/me' && request.method == 'GET') {
      if (failProfileLoad) {
        status = 503;
        body = {'detail': 'profile service unavailable'};
      } else {
        body = {
          'success': true,
          'profile': {
            'id': 'profile-1',
            'name': 'SAGE User',
            'help_intent': 'Build SAGE',
            'basic_info': {
              'saved_preference': 'keep-this',
              'settings': {
                'notifications': true,
                'compact_mode': false,
                'theme_mode': 'system',
                'custom_setting': 'preserve-me',
              }
            }
          }
        };
      }
    } else if (path == '/notifications') {
      body = {'success': true, 'notifications': [
        {'id': 'notice-1', 'title': 'Task completed', 'message': 'Task completed', 'created_at': '2026-10-08T00:00:00Z'}
      ]};
    } else if (path == '/economy/payment/status') {
      body = {
        'success': true,
        'configured': false,
        'provider': null,
        'mode': 'not_configured',
        'can_create_payment': false,
        'message': 'Payment provider is not configured; no payment action is available.'
      };
    } else if (path == '/tasks') {
      body = {
        'success': true,
        'tasks': includeArtifact
            ? [
                {
                  'id': 'task-artifact-1',
                  'artifact': {
                    'name': 'Readable report',
                    'url': 'https://example.com/report.pdf',
                    'mime_type': 'application/pdf',
                  },
                },
              ]
            : <dynamic>[],
      };
    } else if (path == '/workflow/workspaces') {
      body = {'success': true, 'workspaces': []};
    }

    if (request.method == 'GET') {
      if (path == '/economy/me') {
        economyGetRequests++;
        if (failEconomyLoad) { status = 503; body = {'detail': 'economy unavailable'}; }
      } else if (path == '/notifications') {
        notificationGetRequests++;
        if (failNotificationLoad) { status = 503; body = {'detail': 'notifications unavailable'}; }
      } else if (path == '/economy/payment/status') {
        paymentStatusGetRequests++;
        if (failPaymentStatusLoad) { status = 503; body = {'detail': 'payment status unavailable'}; }
      } else if (path == '/tasks') {
        tasksGetRequests++;
        if (failTasksLoad) { status = 503; body = {'detail': 'tasks unavailable'}; }
      } else if (path == '/workflow/workspaces') {
        workspaceGetRequests++;
        if (failWorkspaceLoad) { status = 503; body = {'detail': 'workspaces unavailable'}; }
      }
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


class _FinalSurfaceRetryCase {
  const _FinalSurfaceRetryCase({
    required this.label,
    required this.errorPrefix,
    required this.successText,
    required this.build,
    required this.fail,
    required this.recover,
    required this.requests,
  });

  final String label;
  final String errorPrefix;
  final String successText;
  final Widget Function(SageApi api) build;
  final void Function(_FinalSurfaceClient client) fail;
  final void Function(_FinalSurfaceClient client) recover;
  final int Function(_FinalSurfaceClient client) requests;
}

SageApi _api() => SageApi(
  client: _FinalSurfaceClient(),
  baseUrl: 'http://test',
  authToken: 'test-token',
);

void main() {
  tearDown(() {
    SageTheme.mode.value = ThemeMode.dark;
  });

  testWidgets('final economy, profile, settings, notification and payment surfaces render', (tester) async {
    final screens = <Widget>[
      SparkWalletScreen(api: _api()),
      TransactionsScreen(api: _api()),
      ProfileFinalScreen(api: _api()),
      SettingsFinalScreen(api: _api()),
      NotificationsFinalScreen(api: _api()),
      PaymentFinalScreen(api: _api()),
      FileManagerFinalScreen(api: _api()),
      AiStudioFinalScreen(api: _api()),
    ];

    final labels = <String>[
      'Spark Wallet',
      'Transactions',
      'Profile',
      'Settings',
      'Activity',
      'Provider readiness',
      'Task artifacts',
      'Workflow Studio',
    ];

    for (var i = 0; i < screens.length; i++) {
      await tester.pumpWidget(MaterialApp(home: screens[i]));
      await tester.pumpAndSettle();
      expect(find.text(labels[i]), findsOneWidget);
    }
  });
  testWidgets(
    'Profile validates fields and sends the authenticated PATCH contract',
    (tester) async {
      final client = _FinalSurfaceClient();
      final api = SageApi(
        client: client,
        baseUrl: 'http://test',
        authToken: 'test-token',
      );
      await tester.pumpWidget(MaterialApp(home: ProfileFinalScreen(api: api)));
      await tester.pumpAndSettle();

      await tester.tap(find.text('Save profile'));
      await tester.pumpAndSettle();
      expect(client.profilePatchRequests, 0);
      expect(find.text('Enter your address.'), findsOneWidget);

      await tester.enterText(find.byType(TextField).at(1), '12 Demo Road');
      await tester.enterText(find.byType(TextField).at(2), '29');
      await tester.tap(find.byType(SwitchListTile).first);
      await tester.pump();
      await tester.tap(find.text('Save profile'));
      await tester.pumpAndSettle();

      expect(client.profilePatchRequests, 1);
      expect(client.lastProfileAuthorization, 'Bearer test-token');
      expect(client.lastProfilePatch, {
        'name': 'SAGE User',
        'address': '12 Demo Road',
        'age': 29,
        'help_intent': 'Build SAGE',
        'memory_consent': true,
      });

      await tester.pumpWidget(const SizedBox.shrink());
      api.dispose();
    },
  );

  testWidgets('Profile rejects invalid age without calling the backend', (tester) async {
    final client = _FinalSurfaceClient();
    final api = SageApi(
      client: client,
      baseUrl: 'http://test',
      authToken: 'test-token',
    );
    await tester.pumpWidget(MaterialApp(home: ProfileFinalScreen(api: api)));
    await tester.pumpAndSettle();

    await tester.enterText(find.byType(TextField).at(1), '12 Demo Road');
    await tester.enterText(find.byType(TextField).at(2), '121');
    await tester.tap(find.text('Save profile'));
    await tester.pumpAndSettle();

    expect(find.text('Enter an age from 1 to 120, or leave it blank.'), findsOneWidget);
    expect(client.profilePatchRequests, 0);

    await tester.pumpWidget(const SizedBox.shrink());
    api.dispose();
  });

  testWidgets('AI Studio workspace dialog validates input and cancels safely', (tester) async {
    final api = _api();
    await tester.pumpWidget(MaterialApp(home: AiStudioFinalScreen(api: api)));
    await tester.pumpAndSettle();

    await tester.tap(find.text('Workspace'));
    await tester.pumpAndSettle();
    expect(find.text('Create workspace'), findsOneWidget);

    final createButton = tester.widget<FilledButton>(
      find.widgetWithText(FilledButton, 'Create'),
    );
    expect(createButton.onPressed, isNull);

    final fields = find.byType(TextField);
    await tester.enterText(fields.at(0), 'Demo workspace');
    await tester.enterText(fields.at(1), 'demo-workspace');
    await tester.pump();
    expect(
      tester.widget<FilledButton>(find.widgetWithText(FilledButton, 'Create')).onPressed,
      isNotNull,
    );

    await tester.tap(find.text('Cancel'));
    await tester.pumpAndSettle();
    expect(tester.takeException(), isNull);
    await tester.pumpWidget(const SizedBox.shrink());
    api.dispose();
  });

  testWidgets(
    'Settings cannot overwrite a profile when loading fails and can retry',
    (tester) async {
      final client = _FinalSurfaceClient()..failProfileLoad = true;
      final api = SageApi(
        client: client,
        baseUrl: 'http://test',
        authToken: 'test-token',
      );
      await tester.pumpWidget(MaterialApp(home: SettingsFinalScreen(api: api)));
      await tester.pumpAndSettle();

      expect(find.text('Settings could not be loaded'), findsOneWidget);
      expect(find.text('Retry'), findsOneWidget);
      expect(client.profilePatchRequests, 0);
      expect(
        tester.widget<FilledButton>(
          find.widgetWithText(FilledButton, 'Save settings'),
        ).onPressed,
        isNull,
      );

      client.failProfileLoad = false;
      await tester.tap(find.text('Retry'));
      await tester.pumpAndSettle();

      expect(client.profileGetRequests, 2);
      expect(
        tester.widget<FilledButton>(
          find.widgetWithText(FilledButton, 'Save settings'),
        ).onPressed,
        isNotNull,
      );
      await tester.tap(find.text('Save settings'));
      await tester.pumpAndSettle();

      expect(client.profilePatchRequests, 1);
      expect(find.text('Settings saved.'), findsOneWidget);
      await tester.pumpWidget(const SizedBox.shrink());
      api.dispose();
    },
  );

  testWidgets('Settings save persists updated preferences', (tester) async {
    final client = _FinalSurfaceClient();
    final api = SageApi(
      client: client,
      baseUrl: 'http://test',
      authToken: 'test-token',
    );
    await tester.pumpWidget(MaterialApp(home: SettingsFinalScreen(api: api)));
    await tester.pumpAndSettle();

    await tester.tap(find.byType(SwitchListTile).at(1));
    await tester.pump();
    await tester.tap(find.byType(DropdownButtonFormField<String>));
    await tester.pumpAndSettle();
    await tester.tap(find.text('Light').last);
    await tester.pumpAndSettle();
    await tester.tap(find.text('Save settings'));
    await tester.pumpAndSettle();

    expect(client.profilePatchRequests, 1);
    expect(SageTheme.mode.value, ThemeMode.light);
    final savedBasicInfo =
        client.lastProfilePatch?['basic_info'] as Map<String, dynamic>;
    final savedSettings =
        savedBasicInfo['settings'] as Map<String, dynamic>;
    expect(savedSettings['notifications'], isTrue);
    expect(savedSettings['compact_mode'], isTrue);
    expect(savedSettings['theme_mode'], 'light');
    expect(savedSettings['custom_setting'], 'preserve-me');
    expect(savedBasicInfo['saved_preference'], 'keep-this');
    expect(find.text('Settings saved.'), findsOneWidget);
    await tester.pumpWidget(const SizedBox.shrink());
    api.dispose();
  });

  testWidgets('Notification read button calls the backend', (tester) async {
    final client = _FinalSurfaceClient();
    final api = SageApi(
      client: client,
      baseUrl: 'http://test',
      authToken: 'test-token',
    );
    await tester.pumpWidget(MaterialApp(home: NotificationsFinalScreen(api: api)));
    await tester.pumpAndSettle();

    await tester.tap(find.byIcon(Icons.done));
    await tester.pumpAndSettle();

    expect(client.markReadRequests, 1);
    await tester.pumpWidget(const SizedBox.shrink());
    api.dispose();
  });

  testWidgets('Notifications mark-all-read button calls the backend', (tester) async {
    final client = _FinalSurfaceClient();
    final api = SageApi(
      client: client,
      baseUrl: 'http://test',
      authToken: 'test-token',
    );
    await tester.pumpWidget(MaterialApp(home: NotificationsFinalScreen(api: api)));
    await tester.pumpAndSettle();

    await tester.tap(find.text('Mark all read'));
    await tester.pumpAndSettle();

    expect(client.markAllReadRequests, 1);
  });



  testWidgets('File Manager catches artifact-launcher exceptions', (tester) async {
    const launcherChannel = MethodChannel('plugins.flutter.io/url_launcher');
    final messenger =
        TestDefaultBinaryMessengerBinding.instance.defaultBinaryMessenger;
    messenger.setMockMethodCallHandler(launcherChannel, (call) async {
      throw PlatformException(
        code: 'launcher-unavailable',
        message: 'No browser configured for this test.',
      );
    });
    addTearDown(() {
      messenger.setMockMethodCallHandler(launcherChannel, null);
    });

    final client = _FinalSurfaceClient()..includeArtifact = true;
    final api = SageApi(
      client: client,
      baseUrl: 'http://test',
      authToken: 'test-token',
    );
    await tester.pumpWidget(MaterialApp(home: FileManagerFinalScreen(api: api)));
    await tester.pumpAndSettle();

    expect(find.text('Readable report'), findsOneWidget);
    await tester.tap(find.text('Readable report'));
    await tester.pumpAndSettle();

    expect(
      find.textContaining('SAGE could not open this artifact.'),
      findsOneWidget,
    );
    expect(tester.takeException(), isNull);

    await tester.pumpWidget(const SizedBox.shrink());
    api.dispose();
  });

  testWidgets('final surfaces recover and clear errors after a successful retry',
      (tester) async {
    final scenarios = <_FinalSurfaceRetryCase>[
      _FinalSurfaceRetryCase(
        label: 'wallet', errorPrefix: 'Wallet error:', successText: 'Balance',
        build: (api) => SparkWalletScreen(api: api),
        fail: (client) => client.failEconomyLoad = true,
        recover: (client) => client.failEconomyLoad = false,
        requests: (client) => client.economyGetRequests,
      ),
      _FinalSurfaceRetryCase(
        label: 'transactions', errorPrefix: 'Transaction error:',
        successText: 'Test grant',
        build: (api) => TransactionsScreen(api: api),
        fail: (client) => client.failEconomyLoad = true,
        recover: (client) => client.failEconomyLoad = false,
        requests: (client) => client.economyGetRequests,
      ),
      _FinalSurfaceRetryCase(
        label: 'evolution', errorPrefix: 'Evolution error:', successText: 'Tier: Silver',
        build: (api) => EvolutionFinalScreen(api: api),
        fail: (client) => client.failEconomyLoad = true,
        recover: (client) => client.failEconomyLoad = false,
        requests: (client) => client.economyGetRequests,
      ),
      _FinalSurfaceRetryCase(
        label: 'notifications', errorPrefix: 'Notification error:', successText: 'Task completed',
        build: (api) => NotificationsFinalScreen(api: api),
        fail: (client) => client.failNotificationLoad = true,
        recover: (client) => client.failNotificationLoad = false,
        requests: (client) => client.notificationGetRequests,
      ),
      _FinalSurfaceRetryCase(
        label: 'payments', errorPrefix: 'Payment status error:', successText: 'Not configured',
        build: (api) => PaymentFinalScreen(api: api),
        fail: (client) => client.failPaymentStatusLoad = true,
        recover: (client) => client.failPaymentStatusLoad = false,
        requests: (client) => client.paymentStatusGetRequests,
      ),
      _FinalSurfaceRetryCase(
        label: 'file manager', errorPrefix: 'File manager error:',
        successText: 'No task artifacts found yet.',
        build: (api) => FileManagerFinalScreen(api: api),
        fail: (client) => client.failTasksLoad = true,
        recover: (client) => client.failTasksLoad = false,
        requests: (client) => client.tasksGetRequests,
      ),
      _FinalSurfaceRetryCase(
        label: 'AI Studio', errorPrefix: 'AI Studio error:', successText: 'No workspaces yet.',
        build: (api) => AiStudioFinalScreen(api: api),
        fail: (client) => client.failWorkspaceLoad = true,
        recover: (client) => client.failWorkspaceLoad = false,
        requests: (client) => client.workspaceGetRequests,
      ),
    ];

    for (final scenario in scenarios) {
      final client = _FinalSurfaceClient();
      scenario.fail(client);
      final api = SageApi(
        client: client,
        baseUrl: 'http://test',
        authToken: 'test-token',
      );
      await tester.pumpWidget(MaterialApp(home: scenario.build(api)));
      await tester.pumpAndSettle();

      expect(find.textContaining(scenario.errorPrefix), findsOneWidget,
          reason: 'Initial load error should be shown');
      expect(find.text('Retry'), findsOneWidget,
          reason: 'A retry button should be visible');

      scenario.recover(client);
      await tester.tap(find.text('Retry'));
      await tester.pumpAndSettle();

      expect(scenario.requests(client), 2,
          reason: 'Retry should issue another GET');
      expect(find.textContaining(scenario.errorPrefix), findsNothing,
          reason: 'Successful retry should clear the old error');
      expect(find.textContaining(scenario.successText), findsOneWidget,
          reason: 'Recovered content should be visible');

      await tester.pumpWidget(const SizedBox.shrink());
      api.dispose();
    }
  });

}
