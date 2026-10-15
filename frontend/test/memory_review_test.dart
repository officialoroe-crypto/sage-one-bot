import 'dart:convert';

import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:sage_one/core/sage_api.dart';

class _MemoryReviewClient extends http.BaseClient {
  String? lastMethod;
  String? lastPath;
  Map<String, dynamic>? lastBody;

  @override
  Future<http.StreamedResponse> send(http.BaseRequest request) async {
    lastMethod = request.method;
    lastPath = request.url.path;
    if (request is http.Request && request.body.isNotEmpty) {
      lastBody = Map<String, dynamic>.from(jsonDecode(request.body) as Map);
    }

    final body = request.method == 'GET'
        ? {
            'success': true,
            'count': 1,
            'memories': [
              {
                'id': 'learned-1',
                'profile_id': 'profile-1',
                'memory_type': 'preference',
                'content': 'Prefers concise practical answers',
                'importance': 0.7,
                'confidence': 0.8,
                'source': 'auto_learning',
                'confirmed': false,
              },
            ],
          }
        : {'success': true, 'memory': {'id': 'learned-1', 'confirmed': true}};

    return http.StreamedResponse(
      Stream.value(utf8.encode(jsonEncode(body))),
      200,
      headers: {'content-type': 'application/json'},
      request: request,
    );
  }
}

void main() {
  test('SageApi reads the pending memory review endpoint', () async {
    final client = _MemoryReviewClient();
    final api = SageApi(
      client: client,
      baseUrl: 'http://test',
      authToken: 'test-token',
    );

    final result = await api.profileMemoryReview();

    expect(client.lastMethod, 'GET');
    expect(client.lastPath, '/identity/memory/review');
    expect(result, hasLength(1));
    expect((result.single as Map)['id'], 'learned-1');
    api.dispose();
  });

  test('SageApi confirms a reviewed memory with an authenticated PATCH', () async {
    final client = _MemoryReviewClient();
    final api = SageApi(
      client: client,
      baseUrl: 'http://test',
      authToken: 'test-token',
    );

    final result = await api.updateProfileMemory('learned-1', confirmed: true);

    expect(client.lastMethod, 'PATCH');
    expect(client.lastPath, '/identity/memory/learned-1');
    expect(client.lastBody, {'confirmed': true});
    expect(result['success'], isTrue);
    api.dispose();
  });
}
