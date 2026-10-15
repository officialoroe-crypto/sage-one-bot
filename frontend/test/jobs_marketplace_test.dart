import 'dart:convert';
import 'dart:typed_data';

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:sage_one/core/sage_api.dart';
import 'package:sage_one/screens/jobs_marketplace.dart';

class _OpportunitiesClient extends http.BaseClient {
  final List<String> requests = <String>[];
  final List<Uri> requestUris = <Uri>[];

  final Map<String, dynamic> job = {
    'id': 'job-1',
    'title': 'Junior Flutter Developer',
    'company': 'SAGE Demo',
    'employer_name': 'SAGE employer',
    'description': 'Build and test mobile features.',
    'location': 'Kathmandu, Nepal',
    'employment_type': 'full_time',
    'salary_min_npr': 30000,
    'salary_max_npr': 60000,
    'status': 'open',
  };

  final Map<String, dynamic> listing = {
    'id': 'listing-1',
    'title': 'Used Honda scooter',
    'category': 'vehicles',
    'description': 'Well-maintained scooter.',
    'location': 'Lalitpur, Nepal',
    'price_npr': 185000,
    'item_condition': 'used',
    'seller_name': 'Local seller',
    'status': 'active',
  };

  @override
  Future<http.StreamedResponse> send(http.BaseRequest request) async {
    final method = request.method;
    final path = request.url.path;
    requests.add('$method $path');
    requestUris.add(request.url);

    dynamic body;
    var status = 200;
    if (method == 'GET' && path == '/jobs') {
      body = {'success': true, 'jobs': [job]};
    } else if (method == 'GET' && path == '/jobs/mine') {
      body = {'success': true, 'jobs': [job]};
    } else if (method == 'GET' && path == '/jobs/applications/mine') {
      body = {
        'success': true,
        'applications': [
          {
            'id': 'application-1',
            'job_id': 'job-1',
            'status': 'submitted',
            'job': job,
          },
        ],
      };
    } else if (method == 'POST' && path == '/jobs') {
      status = 201;
      body = {'success': true, 'job': job};
    } else if (method == 'POST' && path == '/jobs/job-1/applications') {
      status = 201;
      body = {
        'success': true,
        'message': 'Application submitted.',
        'application': {'id': 'application-1', 'job_id': 'job-1', 'status': 'submitted'},
      };
    } else if (method == 'GET' && path == '/jobs/job-1/applications') {
      body = {'success': true, 'applications': <dynamic>[]};
    } else if (method == 'POST' && path == '/jobs/job-1/close') {
      body = {'success': true, 'job': {...job, 'status': 'closed'}};
    } else if (method == 'GET' && path == '/marketplace/listings') {
      body = {'success': true, 'listings': [listing]};
    } else if (method == 'GET' && path == '/marketplace/listings/mine') {
      body = {'success': true, 'listings': [listing]};
    } else if (method == 'GET' && path == '/marketplace/inquiries/mine') {
      body = {
        'success': true,
        'inquiries': [
          {'id': 'inquiry-1', 'listing_id': 'listing-1', 'status': 'open', 'listing': listing},
        ],
      };
    } else if (method == 'POST' && path == '/marketplace/listings') {
      status = 201;
      body = {'success': true, 'listing': listing};
    } else if (method == 'POST' && path == '/marketplace/listings/listing-1/inquiries') {
      status = 201;
      body = {'success': true, 'message': 'Interest sent to the seller.'};
    } else if (method == 'GET' && path == '/marketplace/listings/listing-1/inquiries') {
      body = {'success': true, 'inquiries': <dynamic>[]};
    } else if (method == 'POST' && path == '/marketplace/listings/listing-1/close') {
      body = {'success': true, 'listing': {...listing, 'status': 'closed'}};
    } else {
      status = 404;
      body = {'detail': 'not found'};
    }

    return http.StreamedResponse(
      Stream.value(Uint8List.fromList(utf8.encode(jsonEncode(body)))),
      status,
      headers: {'content-type': 'application/json'},
      request: request,
    );
  }
}

void main() {
  testWidgets('Jobs screen lists real job data and submits an application', (tester) async {
    final client = _OpportunitiesClient();
    final api = SageApi(client: client, baseUrl: 'http://test', authToken: 'test-token');
    await tester.pumpWidget(MaterialApp(home: JobsScreen(api: api)));
    await tester.pumpAndSettle();

    expect(find.text('Junior Flutter Developer'), findsOneWidget);
    expect(find.text('SAGE Demo'), findsOneWidget);
    expect(find.text('NPR 30000 – NPR 60000'), findsOneWidget);

    await tester.tap(find.text('Apply'));
    await tester.pumpAndSettle();
    expect(find.text('Apply for this job'), findsOneWidget);
    await tester.enterText(find.byType(TextField).last, 'I have Flutter and Dart experience.');
    await tester.tap(find.text('Submit application'));
    await tester.pumpAndSettle();

    expect(client.requests, contains('POST /jobs/job-1/applications'));
    expect(find.text('Application submitted successfully.'), findsOneWidget);
    await tester.pumpWidget(const SizedBox.shrink());
    api.dispose();
  });

  testWidgets('Employer can publish a job through the form', (tester) async {
    final client = _OpportunitiesClient();
    final api = SageApi(client: client, baseUrl: 'http://test', authToken: 'test-token');
    await tester.pumpWidget(MaterialApp(home: JobsScreen(api: api)));
    await tester.pumpAndSettle();

    await tester.tap(find.text('My postings'));
    await tester.pumpAndSettle();
    await tester.tap(find.text('Post a job'));
    await tester.pumpAndSettle();

    expect(find.byType(AlertDialog), findsOneWidget);
    await tester.enterText(find.byType(TextFormField).at(0), 'Junior Flutter Developer');
    await tester.enterText(find.byType(TextFormField).at(1), 'SAGE Demo');
    await tester.enterText(find.byType(TextFormField).at(2), 'Build mobile features.');
    await tester.enterText(find.byType(TextFormField).at(3), 'Kathmandu, Nepal');
    await tester.tap(find.text('Publish job'));
    await tester.pumpAndSettle();

    expect(client.requests, contains('POST /jobs'));
    expect(find.text('Junior Flutter Developer'), findsOneWidget);
    await tester.pumpWidget(const SizedBox.shrink());
    api.dispose();
  });

  testWidgets('Jobs search forwards location filter to the backend', (tester) async {
    final client = _OpportunitiesClient();
    final api = SageApi(client: client, baseUrl: 'http://test', authToken: 'test-token');
    await tester.pumpWidget(MaterialApp(home: JobsScreen(api: api)));
    await tester.pumpAndSettle();

    await tester.enterText(find.byWidgetPredicate((widget) =>
        widget is TextField && widget.decoration?.hintText == 'Search title, company or description'), 'Flutter');
    await tester.enterText(find.byWidgetPredicate((widget) =>
        widget is TextField && widget.decoration?.hintText == 'Filter by city, district or Remote'), 'Kathmandu');
    await tester.tap(find.byTooltip('Search jobs'));
    await tester.pumpAndSettle();

    expect(
      client.requestUris.any((uri) =>
          uri.path == '/jobs' &&
          uri.queryParameters['query'] == 'Flutter' &&
          uri.queryParameters['location'] == 'Kathmandu'),
      isTrue,
    );
    await tester.pumpWidget(const SizedBox.shrink());
    api.dispose();
  });


  testWidgets('Marketplace lets a buyer send a seller inquiry', (tester) async {
    final client = _OpportunitiesClient();
    final api = SageApi(client: client, baseUrl: 'http://test', authToken: 'test-token');
    await tester.pumpWidget(MaterialApp(home: MarketplaceScreen(api: api)));
    await tester.pumpAndSettle();

    expect(find.text('Used Honda scooter'), findsOneWidget);
    expect(find.text('NPR 185000'), findsOneWidget);
    expect(find.textContaining('Checkout and payment settlement are not connected yet.'), findsOneWidget);

    await tester.tap(find.text('Contact seller'));
    await tester.pumpAndSettle();
    await tester.enterText(find.byType(TextField).last, 'Can I view it this weekend?');
    await tester.pump();
    await tester.tap(find.text('Send inquiry'));
    await tester.pumpAndSettle();

    expect(client.requests, contains('POST /marketplace/listings/listing-1/inquiries'));
    expect(find.text('Your inquiry was sent to the seller.'), findsOneWidget);
    await tester.pumpWidget(const SizedBox.shrink());
    api.dispose();
  });

  testWidgets('Marketplace filters by category and location', (tester) async {
    final client = _OpportunitiesClient();
    final api = SageApi(client: client, baseUrl: 'http://test', authToken: 'test-token');
    await tester.pumpWidget(MaterialApp(home: MarketplaceScreen(api: api)));
    await tester.pumpAndSettle();

    await tester.enterText(find.byWidgetPredicate((widget) =>
        widget is TextField && widget.decoration?.hintText == 'Search items, services and courses'), 'Honda');
    await tester.enterText(find.byWidgetPredicate((widget) =>
        widget is TextField && widget.decoration?.hintText == 'City or district'), 'Lalitpur');
    await tester.tap(find.byType(DropdownButtonFormField<String>));
    await tester.pumpAndSettle();
    await tester.tap(find.text('Vehicles').last);
    await tester.pumpAndSettle();
    await tester.tap(find.byTooltip('Search marketplace'));
    await tester.pumpAndSettle();

    expect(
      client.requestUris.any((uri) =>
          uri.path == '/marketplace/listings' &&
          uri.queryParameters['query'] == 'Honda' &&
          uri.queryParameters['category'] == 'vehicles' &&
          uri.queryParameters['location'] == 'Lalitpur'),
      isTrue,
    );
    await tester.pumpWidget(const SizedBox.shrink());
    api.dispose();
  });

  testWidgets('Seller can publish a listing through the form', (tester) async {
    final client = _OpportunitiesClient();
    final api = SageApi(client: client, baseUrl: 'http://test', authToken: 'test-token');
    await tester.pumpWidget(MaterialApp(home: MarketplaceScreen(api: api)));
    await tester.pumpAndSettle();

    await tester.tap(find.text('My listings'));
    await tester.pumpAndSettle();
    await tester.tap(find.text('Sell an item'));
    await tester.pumpAndSettle();

    await tester.enterText(find.byType(TextFormField).at(0), 'Used Honda scooter');
    await tester.enterText(find.byType(TextFormField).at(1), 'Well-maintained scooter.');
    await tester.enterText(find.byType(TextFormField).at(2), 'Lalitpur, Nepal');
    await tester.enterText(find.byType(TextFormField).at(3), '185000');
    await tester.tap(find.text('Publish listing'));
    await tester.pumpAndSettle();

    expect(client.requests, contains('POST /marketplace/listings'));
    expect(find.text('Used Honda scooter'), findsOneWidget);
    await tester.pumpWidget(const SizedBox.shrink());
    api.dispose();
  });
}
