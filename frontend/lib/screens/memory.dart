import 'package:flutter/material.dart';

import '../core/sage_api.dart';
import '../theme/sage_theme.dart';

class MemoryScreen extends StatefulWidget {
  const MemoryScreen({required this.api, super.key});
  final SageApi api;

  @override
  State<MemoryScreen> createState() => _MemoryScreenState();
}

class _MemoryScreenState extends State<MemoryScreen> {
  bool _loading = true;
  bool _saving = false;
  String? _error;
  List<dynamic> _memories = const [];
  List<dynamic> _pendingMemories = const [];

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    try {
      final results = await Future.wait([
        widget.api.profileMemories(),
        widget.api.profileMemoryReview(),
      ]);
      if (!mounted) return;
      List<Map<String, dynamic>> normalize(List<dynamic> items) => items
          .whereType<Map>()
          .where((item) => item['id'] != null && item['content'] != null)
          .map((item) => Map<String, dynamic>.from(item))
          .toList(growable: false);
      setState(() {
        _memories = normalize(results[0]);
        _pendingMemories = normalize(results[1]);
        _loading = false;
        _error = null;
      });
    } catch (error) {
      if (!mounted) return;
      setState(() {
        _loading = false;
        _error = error.toString();
      });
    }
  }

  Future<void> _addMemory() async {
    final memory = await showDialog<Map<String, String>>(
      context: context,
      builder: (_) => const _AddMemoryDialog(),
    );
    if (!mounted || memory == null) return;

    final content = memory['content']?.trim() ?? '';
    if (content.isEmpty) return;

    setState(() => _saving = true);
    try {
      await widget.api.createProfileMemory(
        memoryType: memory['type'] ?? 'fact',
        content: content,
      );
      await _load();
    } catch (error) {
      if (mounted) setState(() => _error = error.toString());
    } finally {
      if (mounted) setState(() => _saving = false);
    }
  }

  Future<void> _deleteMemory(Map item) async {
    final id = item['id']?.toString();
    if (id == null) return;
    final confirm = await showDialog<bool>(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Delete this memory?'),
        content: const Text('SAGE will no longer keep this saved item. This cannot be undone.'),
        actions: [
          TextButton(onPressed: () => Navigator.pop(context, false), child: const Text('Cancel')),
          FilledButton(
            style: FilledButton.styleFrom(backgroundColor: SageTheme.failure),
            onPressed: () => Navigator.pop(context, true),
            child: const Text('Delete'),
          ),
        ],
      ),
    );
    if (confirm != true) return;
    try {
      await widget.api.deleteProfileMemory(id);
      await _load();
    } catch (error) {
      if (mounted) setState(() => _error = error.toString());
    }
  }

  Future<void> _confirmMemory(Map item) async {
    final id = item['id']?.toString();
    if (id == null) return;
    setState(() => _saving = true);
    try {
      await widget.api.updateProfileMemory(id, confirmed: true);
      await _load();
    } catch (error) {
      if (mounted) setState(() => _error = error.toString());
    } finally {
      if (mounted) setState(() => _saving = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final pendingIds = _pendingMemories
        .whereType<Map>()
        .map((item) => item['id']?.toString())
        .whereType<String>()
        .toSet();
    final savedMemories = _memories.where((item) {
      if (item is! Map) return false;
      return !pendingIds.contains(item['id']?.toString());
    }).toList(growable: false);
    return SafeArea(
      child: RefreshIndicator(
        onRefresh: _load,
        child: ListView(
          physics: const AlwaysScrollableScrollPhysics(),
          padding: const EdgeInsets.fromLTRB(20, 24, 20, 32),
          children: [
            const Row(
              children: [
                Icon(Icons.psychology_alt_outlined, color: SageTheme.cyan),
                SizedBox(width: 12),
                Text('PERSONAL MEMORY', style: TextStyle(
                  fontSize: 11, letterSpacing: 2,
                  color: SageTheme.textSecondary, fontWeight: FontWeight.w800,
                )),
              ],
            ),
            const SizedBox(height: 18),
            const Text('What SAGE remembers', style: TextStyle(fontSize: 26, fontWeight: FontWeight.w700)),
            const SizedBox(height: 8),
            const Text(
              'Review and remove saved details. These memories are private to your profile.',
              style: TextStyle(color: SageTheme.textSecondary, height: 1.45),
            ),
            const SizedBox(height: 18),
            SizedBox(
              width: double.infinity,
              child: FilledButton.icon(
                onPressed: _saving ? null : _addMemory,
                icon: const Icon(Icons.add),
                label: Text(_saving ? 'Saving…' : 'Add memory'),
              ),
            ),
            if (_pendingMemories.isNotEmpty) ...[
              const SizedBox(height: 22),
              Row(
                children: [
                  const Icon(Icons.fact_check_outlined, color: SageTheme.cyan),
                  const SizedBox(width: 10),
                  const Expanded(
                    child: Text('NEEDS YOUR REVIEW', style: TextStyle(
                      fontSize: 11, letterSpacing: 1.6,
                      color: SageTheme.cyan, fontWeight: FontWeight.w800,
                    )),
                  ),
                  Text('${_pendingMemories.length} pending',
                    style: const TextStyle(color: SageTheme.textSecondary, fontSize: 11)),
                ],
              ),
              const SizedBox(height: 10),
              for (final item in _pendingMemories)
                if (item is Map<String, dynamic>)
                  Card(
                    key: ValueKey('memory-review-${item['id']}'),
                    margin: const EdgeInsets.only(bottom: 10),
                    child: Padding(
                      padding: const EdgeInsets.all(14),
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text(
                            (item['memory_type']?.toString() ?? 'memory')
                                .replaceAll('_', ' ').toUpperCase(),
                            style: const TextStyle(
                              color: SageTheme.cyan, fontSize: 10,
                              letterSpacing: 1.2, fontWeight: FontWeight.w800,
                            ),
                          ),
                          const SizedBox(height: 8),
                          Text(item['content']?.toString() ?? '',
                            style: const TextStyle(height: 1.4)),
                          const SizedBox(height: 12),
                          Wrap(
                            spacing: 8,
                            runSpacing: 8,
                            children: [
                              FilledButton.icon(
                                onPressed: _saving ? null : () => _confirmMemory(item),
                                icon: const Icon(Icons.check, size: 18),
                                label: const Text('Keep memory'),
                              ),
                              OutlinedButton.icon(
                                onPressed: _saving ? null : () => _deleteMemory(item),
                                icon: const Icon(Icons.delete_outline, size: 18),
                                label: const Text('Reject'),
                              ),
                            ],
                          ),
                        ],
                      ),
                    ),
                  ),
            ],
            if (_error != null) ...[
              const SizedBox(height: 12),
              Card(child: Padding(
                padding: const EdgeInsets.all(14),
                child: Text(_error!, style: const TextStyle(color: SageTheme.failure)),
              )),
            ],
            const SizedBox(height: 16),
            if (_loading)
              const Padding(
                padding: EdgeInsets.symmetric(vertical: 70),
                child: Center(child: CircularProgressIndicator()),
              )
            else if (savedMemories.isEmpty && _pendingMemories.isEmpty)
              const Card(child: Padding(
                padding: EdgeInsets.all(18),
                child: Text('No saved memories yet. Add one when you want SAGE to remember something.',
                  style: TextStyle(color: SageTheme.textSecondary, height: 1.45)),
              ))
            else
              for (final raw in savedMemories)
                if (raw is Map<String, dynamic>)
                  Card(
                    margin: const EdgeInsets.only(bottom: 10),
                    child: Padding(
                      padding: const EdgeInsets.fromLTRB(14, 12, 6, 12),
                      child: Row(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          const Padding(
                            padding: EdgeInsets.only(top: 3, right: 12),
                            child: Icon(Icons.bookmark_outline, color: SageTheme.cyan),
                          ),
                          Expanded(child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              Text(
                                (raw['memory_type']?.toString() ?? 'memory').replaceAll('_', ' ').toUpperCase(),
                                style: const TextStyle(
                                  color: SageTheme.cyan, fontSize: 10,
                                  letterSpacing: 1.3, fontWeight: FontWeight.w800,
                                ),
                              ),
                              const SizedBox(height: 6),
                              Text(raw['content']?.toString() ?? '',
                                style: const TextStyle(height: 1.4)),
                              const SizedBox(height: 6),
                              Text(
                                raw['confirmed'] == true ? 'Confirmed' : 'Saved',
                                style: const TextStyle(color: SageTheme.textSecondary, fontSize: 11),
                              ),
                            ],
                          )),
                          IconButton(
                            tooltip: 'Delete memory',
                            onPressed: () => _deleteMemory(raw),
                            icon: const Icon(Icons.delete_outline, color: SageTheme.failure),
                          ),
                        ],
                      ),
                    ),
                  ),
          ],
        ),
      ),
    );
  }
}


/// Owns its text controller for the full lifetime of the dialog route. Flutter
/// keeps the route mounted during its reverse transition after Navigator.pop,
/// so the controller must not be disposed by the awaiting caller immediately.
class _AddMemoryDialog extends StatefulWidget {
  const _AddMemoryDialog();

  @override
  State<_AddMemoryDialog> createState() => _AddMemoryDialogState();
}

class _AddMemoryDialogState extends State<_AddMemoryDialog> {
  static const _types = <String>[
    'fact', 'interest', 'inference', 'skill', 'skill_evidence',
    'goal', 'preference', 'experience',
  ];

  final TextEditingController _content = TextEditingController();
  String _type = 'fact';

  @override
  void dispose() {
    _content.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) => AlertDialog(
        title: const Text('Add a memory'),
        content: SingleChildScrollView(
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              DropdownButtonFormField<String>(
                initialValue: _type,
                decoration: const InputDecoration(labelText: 'Memory type'),
                items: _types
                    .map((value) => DropdownMenuItem(
                          value: value,
                          child: Text(value.replaceAll('_', ' ')),
                        ))
                    .toList(),
                onChanged: (value) {
                  if (value != null) setState(() => _type = value);
                },
              ),
              const SizedBox(height: 12),
              TextField(
                controller: _content,
                autofocus: true,
                onChanged: (_) => setState(() {}),
                minLines: 3,
                maxLines: 6,
                maxLength: 5000,
                decoration: const InputDecoration(
                  labelText: 'What should SAGE remember?',
                  alignLabelWithHint: true,
                ),
              ),
            ],
          ),
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context),
            child: const Text('Cancel'),
          ),
          FilledButton(
            onPressed: _content.text.trim().isEmpty
                ? null
                : () => Navigator.pop(context, {
                      'type': _type,
                      'content': _content.text.trim(),
                    }),
            child: const Text('Save memory'),
          ),
        ],
      );
}
