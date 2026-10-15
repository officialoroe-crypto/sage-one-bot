import 'dart:convert';

import 'package:flutter/foundation.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:google_sign_in/google_sign_in.dart';
import 'package:http/http.dart' as http;

class IdentityClient {
  IdentityClient({http.Client? client, FlutterSecureStorage? storage, String? baseUrl})
      : _client = client ?? http.Client(),
        _storage = storage ?? const FlutterSecureStorage(),
        baseUrl = baseUrl ?? _defaultBaseUrl();

  static String _defaultBaseUrl() {
    const configured = String.fromEnvironment('SAGE_API_URL');
    if (configured.isNotEmpty) return configured;
    if (kIsWeb) return 'http://localhost:8010';
    // Android emulators reach the host machine through 10.0.2.2. Physical
    // devices must pass SAGE_API_URL explicitly (for example localhost with
    // adb reverse, or a reachable HTTPS backend URL).
    return 'http://10.0.2.2:8010';
  }

  static const _tokenKey = 'sage.identity.token';
  static const _googleServerClientId = String.fromEnvironment('SAGE_GOOGLE_SERVER_CLIENT_ID');
  final http.Client _client;
  final FlutterSecureStorage _storage;
  final String baseUrl;
  bool _googleInitialized = false;
  bool _developerMode = false;
  bool get developerMode => _developerMode;

  Future<void> loadConfig() async {
    final response = await _client.get(Uri.parse('$baseUrl/identity/config'));
    final data = _decode(response);
    _developerMode = data['developer_mode'] == true;
  }

  Stream<GoogleSignInAuthenticationEvent> get authenticationEvents => GoogleSignIn.instance.authenticationEvents;
  Future<String?> token() => _storage.read(key: _tokenKey);

  Future<void> initializeGoogle() async {
    if (_googleInitialized) return;

    String? clientId;
    String? serverClientId =
        _googleServerClientId.isEmpty ? null : _googleServerClientId;

    // Android requires the OAuth Web application client ID as serverClientId.
    // Never initialize the plugin with a missing server client ID: doing so
    // produces "Server client must be provided on Android null".
    if (kIsWeb || serverClientId == null) {
      final Map<String, dynamic> data;
      try {
        final response = await _client
            .get(Uri.parse('$baseUrl/identity/config'))
            .timeout(const Duration(seconds: 12));
        data = _decode(response);
      } on Exception catch (error) {
        throw Exception(
          'Could not load Google sign-in configuration from SAGE at '
          '${Uri.parse(baseUrl).host}. Check that the backend is running '
          'and this device can reach it. Details: $error',
        );
      }

      _developerMode = data['developer_mode'] == true;
      final configuredClientId = data['google_client_id'];
      if (configuredClientId is! String ||
          configuredClientId.trim().isEmpty) {
        throw Exception(
          'Google sign-in is not configured on the SAGE backend. '
          'Set GOOGLE_CLIENT_ID to the Google Cloud Web application OAuth '
          'client ID, then restart the backend.',
        );
      }

      if (kIsWeb) clientId = configuredClientId;
      serverClientId ??= configuredClientId;
    }

    // This guard is intentionally before plugin initialization so Android can
    // never pass null/empty serverClientId into GoogleSignIn.initialize().
    if (serverClientId.trim().isEmpty) {
      throw Exception(
        'Google sign-in needs a server/web OAuth client ID. '
        'Configure SAGE_GOOGLE_SERVER_CLIENT_ID at build time or set '
        'GOOGLE_CLIENT_ID on the SAGE backend.',
      );
    }

    await GoogleSignIn.instance.initialize(
      clientId: clientId,
      serverClientId: serverClientId,
    );
    _googleInitialized = true;
  }

  Future<void> signOut() async {
    try {
      await initializeGoogle();
      await GoogleSignIn.instance.signOut();
    } finally {
      await _storage.delete(key: _tokenKey);
    }
  }

  Future<Map<String, dynamic>> devLogin({String label = 'local-owner'}) async {
    final response = await _client.post(
      Uri.parse('$baseUrl/identity/dev-login'),
      headers: {'content-type': 'application/json'},
      body: jsonEncode({'label': label}),
    );
    final data = _decode(response);
    final token = data['token'];
    if (token is! String || token.isEmpty) {
      throw Exception('Developer session token was not returned.');
    }
    await _storage.write(key: _tokenKey, value: token);
    return data;
  }

  Future<Map<String, dynamic>> signInWithGoogle() async {
    await initializeGoogle();
    if (!GoogleSignIn.instance.supportsAuthenticate()) {
      throw Exception('Use the Google sign-in button on web.');
    }
    final account = await GoogleSignIn.instance.authenticate();
    return signInWithGoogleAccount(account);
  }

  Future<Map<String, dynamic>> signInWithGoogleAccount(
      GoogleSignInAccount account) async {
    final idToken = account.authentication.idToken;
    if (idToken == null || idToken.isEmpty) {
      throw Exception('Google did not return an ID token.');
    }
    final response = await _client.post(
      Uri.parse('$baseUrl/identity/google'),
      headers: {'content-type': 'application/json'},
      body: jsonEncode({'id_token': idToken}),
    );
    final data = _decode(response);
    await _storage.write(key: _tokenKey, value: idToken);
    return data;
  }

  Future<Map<String, dynamic>> me() async => _authorized('GET', '/identity/me');
  Future<Map<String, dynamic>> onboardingOptions() async =>
      _authorized('GET', '/identity/onboarding/options');
  Future<Map<String, dynamic>> sendPhoneOtp(String phone) async =>
      _authorized('POST', '/identity/phone/send', body: {'phone': phone});
  Future<Map<String, dynamic>> verifyPhoneOtp(
          String challengeId, String code) async =>
      _authorized('POST', '/identity/phone/verify',
          body: {'challenge_id': challengeId, 'code': code});
  Future<Map<String, dynamic>> completeOnboarding({
    required String name,
    String? phone,
    required String address,
    required int age,
    required String helpIntent,
    required List<String> capabilities,
    required bool memoryConsent,
  }) async =>
      _authorized('POST', '/identity/onboarding', body: {
        'name': name,
        // Private Owner Mode allows onboarding before a phone is added.
        // Omit blank phone values because the API accepts null/omitted, not ''.
        ...?(phone == null || phone.trim().isEmpty
            ? null
            : {'phone': phone.trim()}),
        'address': address,
        'age': age,
        'basic_info': <String, dynamic>{},
        'help_intent': helpIntent,
        'capabilities': capabilities,
        'memory_consent': memoryConsent,
      });

  Future<Map<String, dynamic>> _authorized(String method, String path,
      {Map<String, dynamic>? body}) async {
    final idToken = await token();
    if (idToken == null || idToken.isEmpty) {
      throw Exception('SAGE identity session is missing. Sign in again.');
    }
    final headers = <String, String>{
      'authorization': 'Bearer $idToken',
      'content-type': 'application/json',
    };
    final uri = Uri.parse('$baseUrl$path');
    final http.Response response;
    switch (method) {
      case 'GET':
        response = await _client.get(uri, headers: headers);
        break;
      case 'POST':
        response = await _client.post(uri,
            headers: headers, body: jsonEncode(body ?? <String, dynamic>{}));
        break;
      default:
        throw UnsupportedError('Unsupported identity method: $method');
    }
    return _decode(response);
  }

  Map<String, dynamic> _decode(http.Response response) {
    final decoded =
        response.body.isEmpty ? <String, dynamic>{} : jsonDecode(response.body);
    final data = decoded is Map
        ? Map<String, dynamic>.from(decoded)
        : <String, dynamic>{'data': decoded};
    if (response.statusCode < 200 || response.statusCode >= 300) {
      throw Exception(data['detail'] ?? 'SAGE identity request failed');
    }
    return data;
  }

  void dispose() => _client.close();
}
