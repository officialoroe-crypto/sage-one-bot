import 'dart:async';

import 'package:flutter/material.dart';

import '../core/sage_api.dart';

class AgentScreen extends StatefulWidget {
  const AgentScreen({required this.api, super.key});

  final SageApi api;

  @override
  State<AgentScreen> createState() => _AgentScreenState();
}

class _AgentScreenState extends State<AgentScreen> {
  Timer? _poller;
  String _status = 'Agent ready';
  String? _taskId;
  String? _result;
  bool _running = false;
  bool _hasError = false;

  Future<void> _runSystemCheck() async {
    if (_running) return;
    _stopPolling();
    setState(() {
      _running = true;
      _hasError = false;
      _status = 'Queueing system check…';
      _taskId = null;
      _result = null;
    });
    try {
      final response = await widget.api.submitBackground('Agent system check');
      final taskId = response['task_id'] ?? response['id'];
      if (taskId == null || taskId.toString().isEmpty) {
        throw Exception('SAGE did not return a task id.');
      }
      if (!mounted) return;
      setState(() {
        _taskId = taskId?.toString();
        _status = _taskId == null ? 'System check queued' : 'System check running';
      });
      if (_taskId != null) _startPolling();
    } catch (_) {
      if (mounted) {
        setState(() {
          _status = 'Could not reach Sage Core';
          _running = false;
          _hasError = true;
        });
      }
    }
  }

  void _startPolling() {
    _poller = Timer.periodic(const Duration(seconds: 5), (_) => _refreshTask());
    _refreshTask();
  }

  Future<void> _refreshTask() async {
    final taskId = _taskId;
    if (taskId == null) return;
    try {
      final task = await widget.api.task(taskId);
      if (!mounted) return;
      final status = (task['status'] ?? 'unknown').toString().toLowerCase();
      final result = task['result'] ?? task['output'] ?? task['error'] ?? task['failure_reason'];
      setState(() {
        _status = _friendlyStatus(status);
        _result = result?.toString();
        _running = !_isTerminal(status);
      });
      if (_isTerminal(status)) _stopPolling();
    } catch (_) {
      if (mounted) setState(() => _status = 'Waiting for Sage Core…');
    }
  }

  bool _isTerminal(String status) => status == 'completed' ||
      status == 'failed' ||
      status == 'cancelled' ||
      status == 'canceled';

  String _friendlyStatus(String status) {
    switch (status) {
      case 'queued':
        return 'System check queued';
      case 'claimed':
      case 'running':
      case 'processing':
        return 'System check running';
      case 'completed':
        return 'System check complete';
      case 'failed':
        return 'System check failed';
      case 'cancelled':
      case 'canceled':
        return 'System check cancelled';
      default:
        return 'System check: $status';
    }
  }

  void _stopPolling() {
    _poller?.cancel();
    _poller = null;
  }

  @override
  void dispose() {
    _stopPolling();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) => SafeArea(
        child: ListView(
          padding: const EdgeInsets.fromLTRB(20, 24, 20, 32),
          children: [
            const Row(children: [
              Icon(Icons.smart_toy_outlined),
              SizedBox(width: 12),
              Text('AGENT', style: TextStyle(fontSize: 11, letterSpacing: 2, color: Colors.white54)),
            ]),
            const SizedBox(height: 28),
            const Text('Build. Execute. Verify.', style: TextStyle(fontSize: 25, fontWeight: FontWeight.w700)),
            const SizedBox(height: 8),
            const Text('Turn intent into durable work while respecting resource and provider policies.', style: TextStyle(color: Colors.white60, height: 1.45)),
            const SizedBox(height: 22),
            const _Capability(icon: Icons.psychology, title: 'PLAN', detail: 'Break goals into executable work'),
            const _Capability(icon: Icons.cloud_queue, title: 'DELEGATE', detail: 'Route medium and heavy work to cloud'),
            const _Capability(icon: Icons.verified_outlined, title: 'VERIFY', detail: 'Validate outputs before returning results'),
            const _Capability(icon: Icons.memory, title: 'REMEMBER', detail: 'Build durable context over time'),
            const SizedBox(height: 10),
            OutlinedButton.icon(
              key: const ValueKey<String>('agent-run-system-check'),
              onPressed: _running ? null : _runSystemCheck,
              icon: Icon(_running ? Icons.hourglass_top : Icons.play_arrow),
              label: Text(_running ? 'CHECK RUNNING…' : 'RUN SYSTEM CHECK'),
            ),
            const SizedBox(height: 12),
            Text(_status, style: const TextStyle(color: Colors.white54, fontSize: 11)),
            if (_taskId != null)
              Text('TASK  $_taskId', style: const TextStyle(color: Colors.white30, fontSize: 10, letterSpacing: 1)),
            if (_hasError) ...[
              const SizedBox(height: 12),
              OutlinedButton.icon(
                onPressed: _running ? null : _runSystemCheck,
                icon: const Icon(Icons.refresh),
                label: const Text('RETRY SYSTEM CHECK'),
              ),
            ],
            if (_result != null && _result!.isNotEmpty) ...[
              const SizedBox(height: 12),
              Card(child: Padding(padding: const EdgeInsets.all(14), child: Text(_result!, style: const TextStyle(color: Colors.white70, height: 1.4)))),
            ],
          ],
        ),
      );
}

class _Capability extends StatelessWidget {
  const _Capability({required this.icon, required this.title, required this.detail});

  final IconData icon;
  final String title;
  final String detail;

  @override
  Widget build(BuildContext context) => Card(
        margin: const EdgeInsets.only(bottom: 10),
        child: ListTile(
          leading: Icon(icon),
          title: Text(title, style: const TextStyle(fontSize: 11, letterSpacing: 1.2, fontWeight: FontWeight.w700)),
          subtitle: Text(detail, style: const TextStyle(color: Colors.white54)),
        ),
      );
}
