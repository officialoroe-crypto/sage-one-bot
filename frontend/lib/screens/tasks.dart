import 'dart:async';

import 'package:flutter/material.dart';

import '../core/sage_api.dart';

enum _TaskViewStatus {
  loading,
  ready,
  error,
}

class TasksScreen extends StatefulWidget {
  const TasksScreen({required this.api, super.key});

  final SageApi api;

  @override
  State<TasksScreen> createState() => _TasksScreenState();
}

class _TasksScreenState extends State<TasksScreen> {
  List<dynamic> _tasks = <dynamic>[];
  _TaskViewStatus _status = _TaskViewStatus.loading;
  String? _error;
  Timer? _poller;
  String _filter = 'all';
  final Set<String> _cancelling = <String>{};

  @override
  void initState() {
    super.initState();
    _loadTasks();
    _poller = Timer.periodic(const Duration(seconds: 5), (_) {
      _loadTasks(silent: true);
    });
  }

  @override
  void dispose() {
    _poller?.cancel();
    super.dispose();
  }

  Future<void> _loadTasks({bool silent = false}) async {
    if (!silent && mounted) {
      setState(() {
        _status = _TaskViewStatus.loading;
        _error = null;
      });
    }

    try {
      final tasks = await widget.api.tasks();
      if (!mounted) return;
      setState(() {
        _tasks = tasks.whereType<Map>().toList();
        _status = _TaskViewStatus.ready;
        _error = null;
      });
    } catch (error) {
      if (!mounted) return;
      setState(() {
        _status = _TaskViewStatus.error;
        _error = error.toString();
      });
    }
  }

  Future<void> _cancelTask(String taskId) async {
    if (_cancelling.contains(taskId)) return;
    setState(() => _cancelling.add(taskId));
    try {
      await widget.api.cancelTask(taskId);
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Cancellation requested')),
      );
      await _loadTasks(silent: true);
    } catch (error) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('Cancel failed: $error')),
      );
    } finally {
      if (mounted) setState(() => _cancelling.remove(taskId));
    }
  }

  Future<void> _openTask(dynamic item) async {
    final id = _taskId(item);
    if (id == null || id.isEmpty) return;

    showModalBottomSheet<void>(
      context: context,
      isScrollControlled: true,
      showDragHandle: true,
      builder: (context) => FutureBuilder<Map<String, dynamic>>(
        future: widget.api.task(id),
        builder: (context, snapshot) {
          if (snapshot.connectionState != ConnectionState.done) {
            return const SizedBox(
              height: 280,
              child: Center(child: CircularProgressIndicator()),
            );
          }
          if (snapshot.hasError) {
            return SizedBox(
              height: 280,
              child: Center(child: Text('Unable to load task: ${snapshot.error}')),
            );
          }
          final task = snapshot.data ?? <String, dynamic>{};
          return _TaskDetail(task: task);
        },
      ),
    );
  }

  String? _taskId(dynamic item) {
    if (item is Map<String, dynamic>) {
      final value = item['id'] ?? item['task_id'];
      return value?.toString();
    }
    if (item is Map) {
      final value = item['id'] ?? item['task_id'];
      return value?.toString();
    }
    return null;
  }

  String _taskTitle(dynamic item) {
    if (item is Map) {
      return (item['title'] ?? item['prompt'] ?? item['name'] ?? 'Untitled task')
          .toString();
    }
    return 'Untitled task';
  }

  String _taskStatus(dynamic item) {
    if (item is Map) {
      return (item['status'] ?? 'unknown').toString();
    }
    return 'unknown';
  }

  IconData _statusIcon(String status) {
    switch (status.toLowerCase()) {
      case 'completed':
      case 'complete':
        return Icons.check_circle_outline;
      case 'failed':
      case 'error':
        return Icons.error_outline;
      case 'cancelled':
      case 'canceled':
        return Icons.cancel_outlined;
      case 'queued':
      case 'pending':
        return Icons.schedule;
      case 'running':
      case 'claimed':
      case 'processing':
        return Icons.sync;
      default:
        return Icons.help_outline;
    }
  }

  @override
  Widget build(BuildContext context) {
    final visibleTasks = _tasks.where((item) {
      if (_filter == 'all') return true;
      final status = _taskStatus(item).toLowerCase();
      if (_filter == 'active') return {'queued','pending','running','claimed','processing'}.contains(status);
      return status == _filter;
    }).toList();

    final body = switch (_status) {
      _TaskViewStatus.loading => const Center(child: CircularProgressIndicator()),
      _TaskViewStatus.error => _Empty(
          text: _error ?? 'Unable to load tasks.',
          action: TextButton(
            onPressed: _loadTasks,
            child: const Text('Retry'),
          ),
        ),
      _TaskViewStatus.ready when _tasks.isEmpty => const _Empty(
          text: 'No durable tasks yet.',
        ),
      _TaskViewStatus.ready => visibleTasks.isEmpty
          ? _Empty(text: _filter == 'all' ? 'No durable tasks yet.' : 'No tasks match this filter.')
          : RefreshIndicator(
          onRefresh: _loadTasks,
          child: ListView.separated(
            physics: const AlwaysScrollableScrollPhysics(),
            padding: const EdgeInsets.fromLTRB(16, 8, 16, 24),
            itemCount: visibleTasks.length,
            separatorBuilder: (_, _) => const SizedBox(height: 10),
            itemBuilder: (context, index) {
              final item = visibleTasks[index];
              final id = _taskId(item) ?? 'unknown';
              final status = _taskStatus(item);
              final canCancel = {
                'queued',
                'pending',
                'running',
                'claimed',
                'processing',
              }.contains(status.toLowerCase());
              final cancelling = _cancelling.contains(id);

              return Card(
                child: InkWell(
                  borderRadius: BorderRadius.circular(12),
                  onTap: () => _openTask(item),
                  child: Padding(
                    padding: const EdgeInsets.all(16),
                    child: Row(
                      children: [
                        Icon(_statusIcon(status)),
                        const SizedBox(width: 12),
                        Expanded(
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              Text(
                                _taskTitle(item),
                                maxLines: 2,
                                overflow: TextOverflow.ellipsis,
                                style: Theme.of(context).textTheme.titleMedium,
                              ),
                              const SizedBox(height: 4),
                              Text('$status • $id'),
                            ],
                          ),
                        ),
                        if (canCancel)
                          IconButton(
                            tooltip: 'Cancel task',
                            onPressed: cancelling ? null : () => _cancelTask(id),
                            icon: cancelling
                                ? const SizedBox(
                                    width: 18,
                                    height: 18,
                                    child: CircularProgressIndicator(strokeWidth: 2),
                                  )
                                : const Icon(Icons.stop_circle_outlined),
                          ),
                        const Icon(Icons.chevron_right),
                      ],
                    ),
                  ),
                ),
              );
            },
          ),
        ),
    };

    return Scaffold(
      appBar: AppBar(
        title: const Text('Tasks'),
        actions: [
          DropdownButtonHideUnderline(
            child: DropdownButton<String>(
              value: _filter,
              items: const [
                DropdownMenuItem(value: 'all', child: Text('ALL')),
                DropdownMenuItem(value: 'active', child: Text('ACTIVE')),
                DropdownMenuItem(value: 'completed', child: Text('DONE')),
                DropdownMenuItem(value: 'failed', child: Text('FAILED')),
              ],
              onChanged: (value) => setState(() => _filter = value ?? 'all'),
            ),
          ),
          IconButton(
            tooltip: 'Refresh',
            onPressed: () => _loadTasks(),
            icon: const Icon(Icons.refresh),
          ),
        ],
      ),
      body: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Padding(
            padding: EdgeInsets.fromLTRB(16, 8, 16, 4),
            child: Text('Execution queue'),
          ),
          Expanded(child: body),
        ],
      ),
    );
  }
}

class _TaskDetail extends StatelessWidget {
  const _TaskDetail({required this.task});

  final Map<String, dynamic> task;

  @override
  Widget build(BuildContext context) {
    final status = (task['status'] ?? 'unknown').toString();
    final id = (task['id'] ?? task['task_id'] ?? 'unknown').toString();
    final result = task['result'] ?? task['output'];
    final error = task['error'] ?? task['failure_reason'];

    return SafeArea(
      child: SingleChildScrollView(
        padding: const EdgeInsets.fromLTRB(20, 8, 20, 28),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text('Task detail', style: Theme.of(context).textTheme.headlineSmall),
            const SizedBox(height: 18),
            _DetailRow(label: 'Status', value: status),
            _DetailRow(label: 'Task ID', value: id),
            _DetailRow(
              label: 'Created',
              value: (task['created_at'] ?? task['created'] ?? '—').toString(),
            ),
            _DetailRow(
              label: 'Updated',
              value: (task['updated_at'] ?? task['updated'] ?? '—').toString(),
            ),
            if (result != null) _DetailBlock(label: 'Result', value: result.toString()),
            if (error != null) _DetailBlock(label: 'Error', value: error.toString()),
          ],
        ),
      ),
    );
  }
}

class _DetailRow extends StatelessWidget {
  const _DetailRow({required this.label, required this.value});

  final String label;
  final String value;

  @override
  Widget build(BuildContext context) => Padding(
        padding: const EdgeInsets.only(bottom: 10),
        child: Row(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            SizedBox(width: 82, child: Text(label)),
            Expanded(child: Text(value)),
          ],
        ),
      );
}

class _DetailBlock extends StatelessWidget {
  const _DetailBlock({required this.label, required this.value});

  final String label;
  final String value;

  @override
  Widget build(BuildContext context) => Padding(
        padding: const EdgeInsets.only(top: 8),
        child: Card(
          child: Padding(
            padding: const EdgeInsets.all(14),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(label, style: Theme.of(context).textTheme.titleSmall),
                const SizedBox(height: 8),
                SelectableText(value),
              ],
            ),
          ),
        ),
      );
}

class _Empty extends StatelessWidget {
  const _Empty({required this.text, this.action});

  final String text;
  final Widget? action;

  @override
  Widget build(BuildContext context) => Card(
        child: Padding(
          padding: const EdgeInsets.all(24),
          child: Row(
            children: [
              const Icon(Icons.inbox_outlined),
              const SizedBox(width: 12),
              Expanded(child: Text(text)),
              ?action,
            ],
          ),
        ),
      );
}
