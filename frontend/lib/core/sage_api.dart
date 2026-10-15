// ignore_for_file: use_null_aware_elements
import 'dart:convert';

import 'package:flutter/foundation.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:http/http.dart' as http;

class SageApi {
  SageApi({
    http.Client? client,
    String? baseUrl,
    FlutterSecureStorage? storage,
    String? authToken,
  })  : _client = client ?? http.Client(),
        _storage = storage ?? const FlutterSecureStorage(),
        _authToken = authToken,
        baseUrl = baseUrl ?? _defaultBaseUrl();

  static String _defaultBaseUrl() {
    const configured = String.fromEnvironment('SAGE_API_URL');
    if (configured.isNotEmpty) return configured;
    if (kIsWeb) return 'http://localhost:8010';
    return 'http://10.0.2.2:8010';
  }

  final http.Client _client;
  final FlutterSecureStorage _storage;
  final String? _authToken;
  final String baseUrl;

  Future<Map<String, dynamic>> routing() async {
    final data = await _authorizedGet('/brain/routing');
    final routing = data['routing'];
    if (routing is Map) {
      final normalized = Map<String, dynamic>.from(routing);
      final order = normalized['provider_order'];
      if (order is List && order.isNotEmpty) {
        normalized['provider'] = order.first.toString();
      }
      data['routing'] = normalized;
    }
    return data;
  }

  Future<Map<String, dynamic>> submitBackground(String prompt, {String? projectId}) async {
    final data = await _authorizedPost('/execute/background', {
      'goal': prompt,
      if (projectId case final id?) 'project_id': id,
    });
    final task = data['task'];
    final taskMap = task is Map ? task : null;
    data['task_id'] = taskMap?['id'] ?? taskMap?['task_id'] ?? data['task_id'];
    return data;
  }

  Future<Map<String, dynamic>> submitCommand(
    String message, {
    String? sessionId,
    String? projectId,
    int priority = 3,
  }) async =>
      _authorizedPost('/command', {
        'message': message,
        if (sessionId case final id?) 'session_id': id,
        if (projectId case final id?) 'project_id': id,
        'priority': priority,
      });

  Future<List<dynamic>> sessionMessages(String sessionId, {int limit = 50}) async {
    final data = await _authorizedGet('/session/$sessionId/messages?limit=$limit');
    final items = data['messages'] ?? data['items'] ?? data;
    return items is List ? items : <dynamic>[];
  }

  Future<Map<String, dynamic>> createSession() async => _authorizedPost('/session', <String, dynamic>{});

  Future<Map<String, dynamic>> workerHealth() async => _authorizedGet('/worker/health');
  Future<Map<String, dynamic>> brainHealth() async => _authorizedGet('/brain/health');

  Future<List<dynamic>> tasks() async {
    final data = await _authorizedGet('/tasks');
    final items = data['tasks'] ?? data['items'] ?? data;
    return items is List ? items : <dynamic>[];
  }

  Future<Map<String, dynamic>> cancelTask(String taskId) async =>
      _authorizedPost('/tasks/$taskId/cancel', <String, dynamic>{});

  Future<Map<String, dynamic>> task(String taskId) async => _authorizedGet('/tasks/$taskId');

  Future<List<dynamic>> notifications({bool unreadOnly = false, int limit = 50}) async {
    final uri = Uri.parse('$baseUrl/notifications').replace(
      queryParameters: {
        'unread_only': unreadOnly.toString(),
        'limit': limit.toString(),
      },
    );
    final data = await _authorizedGetUri(uri);
    final items = data['notifications'] ?? data['items'] ?? data;
    return items is List ? items : <dynamic>[];
  }

  Future<Map<String, dynamic>> markNotificationRead(String notificationId) async =>
      _authorizedPost('/notifications/$notificationId/read', <String, dynamic>{});

  Future<Map<String, dynamic>> markAllNotificationsRead() async =>
      _authorizedPost('/notifications/read-all', <String, dynamic>{});

  Future<List<dynamic>> researchHistory({String? sessionId, int limit = 20}) async {
    final arguments = <String, dynamic>{'limit': limit};
    if (sessionId != null && sessionId.isNotEmpty) arguments['session_id'] = sessionId;
    final data = await _executeTool('research_list', arguments);
    final items = data['result'] ?? data['items'] ?? data;
    return items is List ? items : <dynamic>[];
  }

  Future<Map<String, dynamic>?> research(String researchId) async {
    final data = await _executeTool('research_get', {'research_id': researchId});
    final value = data['result'];
    return value is Map<String, dynamic> ? value : null;
  }

  Future<Map<String, dynamic>?> researchForTask(String taskId) async {
    final data = await _executeTool('research_by_task', {'task_id': taskId});
    final value = data['result'];
    return value is Map<String, dynamic> ? value : null;
  }

  Future<Map<String, dynamic>> worldStatus() async => _authorizedGet('/world/status');

  Future<List<dynamic>> worldKnowledge({int limit = 20}) async {
    final uri = Uri.parse('$baseUrl/world/knowledge').replace(
      queryParameters: {'limit': limit.toString()},
    );
    final data = await _authorizedGetUri(uri);
    final items = data['knowledge'] ?? data['items'] ?? data;
    return items is List ? items : <dynamic>[];
  }

  Future<List<dynamic>> worldDue() async {
    final data = await _authorizedGet('/world/due');
    final items = data['topics'] ?? data['items'] ?? data;
    return items is List ? items : <dynamic>[];
  }

  Future<Map<String, dynamic>> refreshWorld({List<String>? topics}) async =>
      _authorizedPost('/world/refresh', {'topics': topics ?? <String>[]});

  Future<List<dynamic>> workflowWorkspaces() async {
    final data = await _authorizedGet('/workflow/workspaces');
    final items = data['workspaces'] ?? data['items'] ?? data;
    return items is List ? items : <dynamic>[];
  }

  Future<Map<String, dynamic>> createWorkflowWorkspace({
    required String name,
    required String slug,
    String workspaceType = 'personal',
    Map<String, dynamic>? metadata,
  }) async =>
      _authorizedPost('/workflow/workspaces', {
        'name': name,
        'slug': slug,
        'workspace_type': workspaceType,
        'metadata': metadata ?? <String, dynamic>{},
      });

  Future<List<dynamic>> workflowProjects(String workspaceId) async {
    final data = await _authorizedGet('/workflow/workspaces/$workspaceId/projects');
    final items = data['projects'] ?? data['items'] ?? data;
    return items is List ? items : <dynamic>[];
  }

  Future<Map<String, dynamic>> createWorkflowProject({
    required String workspaceId,
    required String name,
    required String projectType,
    String? description,
    Map<String, dynamic>? metadata,
  }) async =>
      _authorizedPost('/workflow/workspaces/$workspaceId/projects', {
        'name': name,
        'project_type': projectType,
        'description': description,
        'metadata': metadata ?? <String, dynamic>{},
      });

  Future<List<dynamic>> workflowAssets(String projectId) async {
    final data = await _authorizedGet('/workflow/projects/$projectId/assets');
    final items = data['assets'] ?? data['items'] ?? data;
    return items is List ? items : <dynamic>[];
  }

  Future<Map<String, dynamic>> createWorkflowAsset({
    required String projectId,
    required String name,
    required String assetType,
    String? parentAssetId,
    String status = 'draft',
    String? path,
    String? uri,
    String? mimeType,
    String? checksum,
    Map<String, dynamic>? metadata,
  }) async =>
      _authorizedPost('/workflow/projects/$projectId/assets', {
        'name': name,
        'asset_type': assetType,
        'parent_asset_id': parentAssetId,
        'status': status,
        'path': path,
        'uri': uri,
        'mime_type': mimeType,
        'checksum': checksum,
        'metadata': metadata ?? <String, dynamic>{},
      });

  Future<List<dynamic>> workflowRelations(String projectId) async {
    final data = await _authorizedGet('/workflow/projects/$projectId/relations');
    final items = data['relations'] ?? data['items'] ?? data;
    return items is List ? items : <dynamic>[];
  }

  Future<Map<String, dynamic>> createWorkflowRelation({
    required String projectId,
    required String sourceAssetId,
    required String targetAssetId,
    required String relationType,
    Map<String, dynamic>? metadata,
  }) async =>
      _authorizedPost('/workflow/projects/$projectId/relations', {
        'source_asset_id': sourceAssetId,
        'target_asset_id': targetAssetId,
        'relation_type': relationType,
        'metadata': metadata ?? <String, dynamic>{},
      });

  Future<List<dynamic>> workflowDefinitions(String projectId) async {
    final data = await _authorizedGet('/workflow/projects/$projectId/workflows');
    final items = data['workflows'] ?? data['items'] ?? data;
    return items is List ? items : <dynamic>[];
  }

  Future<Map<String, dynamic>> createWorkflow({
    required String projectId,
    required String name,
    required String workflowType,
    required Map<String, dynamic> definition,
    String? currentStage,
  }) async =>
      _authorizedPost('/workflow/projects/$projectId/workflows', {
        'name': name,
        'workflow_type': workflowType,
        'current_stage': currentStage,
        'definition': definition,
      });

  Future<List<dynamic>> profileMemories() async {
    final data = await _authorizedGet('/identity/memory');
    final items = data['memories'] ?? data['items'] ?? data;
    return items is List ? items : <dynamic>[];
  }

  Future<List<dynamic>> profileMemoryReview() async {
    final data = await _authorizedGet('/identity/memory/review');
    final items = data['memories'] ?? data['items'] ?? data;
    return items is List ? items : <dynamic>[];
  }

  Future<Map<String, dynamic>> createProfileMemory({
    required String memoryType,
    required String content,
  }) async =>
      _authorizedPost('/identity/memory', {
        'memory_type': memoryType,
        'content': content,
        'source': 'user',
        'confirmed': true,
      });

  Future<Map<String, dynamic>> updateProfileMemory(
    String memoryId, {
    required bool confirmed,
  }) async =>
      _authorizedPatch('/identity/memory/$memoryId', {'confirmed': confirmed});

  Future<Map<String, dynamic>> deleteProfileMemory(String memoryId) async =>
      _authorizedDelete('/identity/memory/$memoryId');

  Future<Map<String, dynamic>> economyMe() async => _authorizedGet('/economy/me');
  Future<List<dynamic>> evolutionTiers() async {
    final data = await _authorizedGet('/economy/evolution/tiers');
    final items = data['tiers'] ?? const [];
    return items is List ? items : <dynamic>[];
  }
  Future<List<dynamic>> premiumWorkCosts() async {
    final data = await _authorizedGet('/economy/costs');
    final items = data['costs'] ?? data['items'] ?? data;
    return items is List ? items : <dynamic>[];
  }

  Future<List<dynamic>> learningPaths() async {
    final data = await _authorizedGet('/learning/paths');
    final items = data['paths'] ?? data['items'] ?? data;
    return items is List ? items : <dynamic>[];
  }

  Future<Map<String, dynamic>> completeLearningLesson(String lessonId) async =>
      _authorizedPost('/learning/lessons/$lessonId/complete', <String, dynamic>{});

  Future<List<dynamic>> jobPostings({
    String? query,
    String? location,
    String status = 'open',
    int limit = 50,
  }) async {
    final parameters = <String, String>{
      'status': status,
      'limit': limit.toString(),
    };
    if (query != null && query.trim().isNotEmpty) parameters['query'] = query.trim();
    if (location != null && location.trim().isNotEmpty) parameters['location'] = location.trim();
    final uri = Uri.parse('$baseUrl/jobs').replace(queryParameters: parameters);
    final data = await _authorizedGetUri(uri);
    final items = data['jobs'] ?? data['items'] ?? data;
    return items is List ? items : <dynamic>[];
  }

  Future<Map<String, dynamic>> createJobPosting({
    required String title,
    required String company,
    required String description,
    required String location,
    String employmentType = 'full_time',
    double? salaryMinNpr,
    double? salaryMaxNpr,
  }) async =>
      _authorizedPost('/jobs', {
        'title': title,
        'company': company,
        'description': description,
        'location': location,
        'employment_type': employmentType,
        'salary_min_npr': salaryMinNpr,
        'salary_max_npr': salaryMaxNpr,
      });

  Future<List<dynamic>> myJobPostings() async {
    final data = await _authorizedGet('/jobs/mine');
    final items = data['jobs'] ?? data['items'] ?? data;
    return items is List ? items : <dynamic>[];
  }

  Future<Map<String, dynamic>> applyForJob(
    String jobId, {
    String coverNote = '',
  }) async =>
      _authorizedPost('/jobs/$jobId/applications', {'cover_note': coverNote});

  Future<List<dynamic>> myJobApplications() async {
    final data = await _authorizedGet('/jobs/applications/mine');
    final items = data['applications'] ?? data['items'] ?? data;
    return items is List ? items : <dynamic>[];
  }

  Future<Map<String, dynamic>> jobApplications(String jobId) async =>
      _authorizedGet('/jobs/$jobId/applications');

  Future<Map<String, dynamic>> closeJobPosting(String jobId) async =>
      _authorizedPost('/jobs/$jobId/close', <String, dynamic>{});

  Future<List<dynamic>> marketplaceListings({
    String? query,
    String? category,
    String? location,
    String status = 'active',
    int limit = 50,
  }) async {
    final parameters = <String, String>{
      'status': status,
      'limit': limit.toString(),
    };
    if (query != null && query.trim().isNotEmpty) parameters['query'] = query.trim();
    if (category != null && category.trim().isNotEmpty) parameters['category'] = category.trim();
    if (location != null && location.trim().isNotEmpty) parameters['location'] = location.trim();
    final uri = Uri.parse('$baseUrl/marketplace/listings').replace(queryParameters: parameters);
    final data = await _authorizedGetUri(uri);
    final items = data['listings'] ?? data['items'] ?? data;
    return items is List ? items : <dynamic>[];
  }

  Future<Map<String, dynamic>> createMarketplaceListing({
    required String title,
    required String category,
    required String description,
    required String location,
    required double priceNpr,
    String itemCondition = 'used',
  }) async =>
      _authorizedPost('/marketplace/listings', {
        'title': title,
        'category': category,
        'description': description,
        'location': location,
        'price_npr': priceNpr,
        'item_condition': itemCondition,
      });

  Future<List<dynamic>> myMarketplaceListings() async {
    final data = await _authorizedGet('/marketplace/listings/mine');
    final items = data['listings'] ?? data['items'] ?? data;
    return items is List ? items : <dynamic>[];
  }

  Future<Map<String, dynamic>> inquireMarketplaceListing(
    String listingId, {
    required String message,
  }) async =>
      _authorizedPost('/marketplace/listings/$listingId/inquiries', {'message': message});

  Future<List<dynamic>> myMarketplaceInquiries() async {
    final data = await _authorizedGet('/marketplace/inquiries/mine');
    final items = data['inquiries'] ?? data['items'] ?? data;
    return items is List ? items : <dynamic>[];
  }

  Future<Map<String, dynamic>> marketplaceListingInquiries(String listingId) async =>
      _authorizedGet('/marketplace/listings/$listingId/inquiries');

  Future<Map<String, dynamic>> closeMarketplaceListing(String listingId) async =>
      _authorizedPost('/marketplace/listings/$listingId/close', <String, dynamic>{});

  Future<Map<String, dynamic>> developerPreview(String task, {String? workspace}) async =>
      _authorizedPost('/developer/preview', {
        'task': task,
        if (workspace != null && workspace.isNotEmpty) 'workspace': workspace,
      });

  Future<Map<String, dynamic>> developerApply(String proposalId, {required bool approved}) async =>
      _authorizedPost('/developer/apply', {
        'proposal_id': proposalId,
        'approved': approved,
      });

  Future<Map<String, dynamic>> ownerStatus() async => _authorizedGet('/economy/owner/status');
  Future<List<dynamic>> ownerAudit({int limit = 100}) async {
    final data = await _authorizedGet('/economy/owner/audit?limit=$limit');
    final items = data['events'] ?? const [];
    return items is List ? items : <dynamic>[];
  }
  Future<Map<String, dynamic>> ownerSetSpark(int amount, String reason) async =>
      _authorizedPost('/economy/owner/spark/set', {'amount': amount, 'reason': reason});
  Future<Map<String, dynamic>> ownerResetSpark(String reason) async =>
      _authorizedPost('/economy/owner/spark/reset', {'reason': reason});
  Future<Map<String, dynamic>> ownerSetEvolution(int achievement, String tier, String stage, String reason) async =>
      _authorizedPost('/economy/owner/evolution/set', {
        'lifetime_achievement': achievement, 'tier': tier, 'stage': stage, 'reason': reason,
      });
  Future<Map<String, dynamic>> ownerSimulateEvolution(int achievement, {int durationMs = 3000}) async =>
      _authorizedPost('/economy/owner/evolution/simulate', {
        'target_achievement': achievement, 'duration_ms': durationMs,
      });
  Future<Map<String, dynamic>> ownerResetEvolution(String reason) async =>
      _authorizedPost('/economy/owner/evolution/reset', {'reason': reason});

  Future<Map<String, dynamic>> profileMe() async => _authorizedGet('/identity/me');

  Future<Map<String, dynamic>> updateProfile({
    String? name,
    String? phone,
    String? address,
    int? age,
    Map<String, dynamic>? basicInfo,
    String? helpIntent,
    List<String>? capabilities,
    bool? memoryConsent,
  }) async {
    final body = <String, dynamic>{};
    if (name != null) body['name'] = name;
    if (phone != null) body['phone'] = phone;
    if (address != null) body['address'] = address;
    if (age != null) body['age'] = age;
    if (basicInfo != null) body['basic_info'] = basicInfo;
    if (helpIntent != null) body['help_intent'] = helpIntent;
    if (capabilities != null) body['capabilities'] = capabilities;
    if (memoryConsent != null) body['memory_consent'] = memoryConsent;
    return _authorizedPatch('/identity/me', body);
  }


  Future<List<dynamic>> salesLeads({String? status}) async {
    final path = status == null || status.isEmpty ? '/sales/leads' : '/sales/leads?status=${Uri.encodeQueryComponent(status)}';
    final data = await _authorizedGet(path);
    final items = data['leads'] ?? data['items'] ?? data;
    return items is List ? items : <dynamic>[];
  }

  Future<Map<String, dynamic>> salesLead(String leadId) async => _authorizedGet('/sales/leads/$leadId');

  Future<List<dynamic>> salesLeadHistory(String leadId) async {
    final data = await _authorizedGet('/sales/leads/$leadId/history');
    final items = data['history'] ?? data['activities'] ?? data['items'] ?? data;
    return items is List ? items : <dynamic>[];
  }

  Future<Map<String, dynamic>> approveSalesOutreach(String leadId) async =>
      _authorizedPost('/sales/leads/$leadId/approve-outreach', <String, dynamic>{});

  Future<Map<String, dynamic>> convertSalesCustomer(String leadId) async =>
      _authorizedPost('/sales/leads/$leadId/convert-customer', <String, dynamic>{});

  Future<Map<String, dynamic>> addSalesFollowUp(String leadId, String note, {String status = 'planned'}) async =>
      _authorizedPost('/sales/leads/$leadId/follow-up', {'note': note, 'status': status});

  Future<Map<String, dynamic>> paymentStatus() async => _authorizedGet('/economy/payment/status');

  Future<Map<String, dynamic>> _authorizedDelete(String path) async {
    final token = await _identityToken();
    final headers = <String, String>{};
    if (token != null) headers['authorization'] = 'Bearer $token';
    final response = await _client.delete(Uri.parse('$baseUrl$path'), headers: headers);
    return _decode(response);
  }

  Future<Map<String, dynamic>> _authorizedPatch(String path, Map<String, dynamic> body) async {
    final token = await _identityToken();
    final headers = <String, String>{'content-type': 'application/json'};
    if (token != null) headers['authorization'] = 'Bearer $token';
    final response = await _client.patch(
      Uri.parse('$baseUrl$path'), headers: headers, body: jsonEncode(body),
    );
    return _decode(response);
  }

  Future<Map<String, dynamic>> _authorizedPost(String path, Map<String, dynamic> body) async {
    final token = await _identityToken();
    final headers = <String, String>{'content-type': 'application/json'};
    if (token != null) headers['authorization'] = 'Bearer $token';
    final response = await _client.post(
      Uri.parse('$baseUrl$path'), headers: headers, body: jsonEncode(body),
    );
    return _decode(response);
  }

  Future<String?> _identityToken() async {
    if (_authToken != null && _authToken.isNotEmpty) return _authToken;
    String? token;
    try {
      token = await _storage.read(key: 'sage.google.id_token') ??
          await _storage.read(key: 'sage.identity.token');
    } catch (_) {
      token = null;
    }
    if (token != null && token.isNotEmpty) return token;
    final host = Uri.parse(baseUrl).host;
    if (host == 'localhost' || host == '127.0.0.1' || host == '10.0.2.2') return null;
    throw Exception('SAGE identity session is missing. Sign in again.');
  }

  Future<Map<String, dynamic>> _authorizedGet(String path) async =>
      _authorizedGetUri(Uri.parse('$baseUrl$path'));

  Future<Map<String, dynamic>> _authorizedGetUri(Uri uri) async {
    final token = await _identityToken();
    final headers = <String, String>{};
    if (token != null) headers['authorization'] = 'Bearer $token';
    final response = await _client.get(uri, headers: headers);
    return _decode(response);
  }

  Future<Map<String, dynamic>> _executeTool(
    String toolName,
    Map<String, dynamic> arguments,
  ) async {
    final uri = Uri.parse('$baseUrl/tools/execute').replace(
      queryParameters: {
        'tool_name': toolName,
        'arguments': jsonEncode(arguments),
      },
    );
    final token = await _identityToken();
    final headers = <String, String>{};
    if (token != null) headers['authorization'] = 'Bearer $token';
    final response = await _client.post(uri, headers: headers);
    return _decode(response);
  }

  Map<String, dynamic> _decode(http.Response response) {
    final decoded = response.body.isEmpty ? <String, dynamic>{} : jsonDecode(response.body);
    final body = decoded is Map
        ? Map<String, dynamic>.from(decoded)
        : <String, dynamic>{'data': decoded};
    if (response.statusCode < 200 || response.statusCode >= 300) {
      throw Exception(body['detail'] ?? body['error'] ?? 'SAGE API request failed');
    }
    return body;
  }

  void dispose() => _client.close();
}
