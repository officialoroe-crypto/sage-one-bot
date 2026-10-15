import 'package:flutter/material.dart';

import '../core/sage_api.dart';

class WorldIntelligenceScreen extends StatefulWidget {
  const WorldIntelligenceScreen({required this.api, super.key});

  final SageApi api;

  @override
  State<WorldIntelligenceScreen> createState() => _WorldIntelligenceScreenState();
}

class _WorldIntelligenceScreenState extends State<WorldIntelligenceScreen> {
  Map<String, dynamic>? _status;
  List<dynamic> _knowledge = const [];
  List<dynamic> _due = const [];
  bool _loading = true;
  bool _refreshing = false;
  String? _error;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    setState(() {
      _loading = true;
      _error = null;
    });
    try {
      final results = await Future.wait([
        widget.api.worldStatus(),
        widget.api.worldKnowledge(limit: 12),
        widget.api.worldDue(),
      ]);
      if (!mounted) return;
      setState(() {
        _status = results[0] as Map<String, dynamic>;
        _knowledge = results[1] as List<dynamic>;
        _due = results[2] as List<dynamic>;
        _loading = false;
      });
    } catch (error) {
      if (!mounted) return;
      setState(() {
        _loading = false;
        _error = error.toString();
      });
    }
  }

  Future<void> _refresh() async {
    if (_refreshing) return;
    setState(() {
      _refreshing = true;
      _error = null;
    });
    try {
      await widget.api.refreshWorld();
      await _load();
    } catch (error) {
      if (mounted) setState(() => _error = error.toString());
    } finally {
      if (mounted) setState(() => _refreshing = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final topics = (_status?['default_topics'] as List?)?.cast<dynamic>() ?? const [];
    final learning = _status?['learning_enabled'] == true;
    final selfModification = _status?['self_modification'] == true;

    return SafeArea(
      child: RefreshIndicator(
        onRefresh: _load,
        child: ListView(
          padding: const EdgeInsets.fromLTRB(18, 20, 18, 32),
          children: [
            Row(
              children: [
                Container(
                  width: 44,
                  height: 44,
                  decoration: BoxDecoration(
                    shape: BoxShape.circle,
                    border: Border.all(color: Colors.cyanAccent.withOpacity(.65)),
                    boxShadow: [
                      BoxShadow(
                        color: Colors.blueAccent.withOpacity(.18),
                        blurRadius: 18,
                        spreadRadius: 2,
                      ),
                    ],
                  ),
                  child: const Icon(Icons.public, color: Colors.cyanAccent),
                ),
                const SizedBox(width: 12),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text('World Intelligence', style: theme.textTheme.titleLarge),
                      const SizedBox(height: 2),
                      Text(
                        'SAGE learns from the public world — not your private memory. Knowledge remains source-traceable and refreshable.',
                        style: theme.textTheme.bodySmall,
                      ),
                    ],
                  ),
                ),
                IconButton(
                  tooltip: 'Refresh world knowledge',
                  onPressed: _refreshing ? null : _refresh,
                  icon: _refreshing
                      ? const SizedBox(
                          width: 20,
                          height: 20,
                          child: CircularProgressIndicator(strokeWidth: 2),
                        )
                      : const Icon(Icons.refresh),
                ),
              ],
            ),
            const SizedBox(height: 18),
            _statusCard(theme, learning, selfModification),
            if (_due.isNotEmpty) ...[
              const SizedBox(height: 14),
              _sectionHeader('Refresh needed', Icons.sync_problem),
              const SizedBox(height: 8),
              _topicWrap(_due),
            ],
            const SizedBox(height: 18),
            _sectionHeader('World coverage', Icons.language),
            const SizedBox(height: 8),
            _topicWrap(topics),
            const SizedBox(height: 18),
            _sectionHeader('Knowledge learned', Icons.auto_awesome),
            const SizedBox(height: 8),
            if (_loading)
              const Padding(
                padding: EdgeInsets.symmetric(vertical: 42),
                child: Center(child: CircularProgressIndicator()),
              )
            else if (_error != null)
              _errorCard(theme)
            else if (_knowledge.isEmpty)
              _emptyCard(theme)
            else
              ..._knowledge.map((item) => _knowledgeCard(theme, item)),
          ],
        ),
      ),
    );
  }

  Widget _statusCard(ThemeData theme, bool learning, bool selfModification) {
    return Container(
      padding: const EdgeInsets.all(18),
      decoration: BoxDecoration(
        color: const Color(0xFF050A12),
        borderRadius: BorderRadius.circular(20),
        border: Border.all(color: Colors.blueAccent.withOpacity(.32)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              const Icon(Icons.psychology_alt, color: Colors.lightBlueAccent),
              const SizedBox(width: 10),
              Text('SAGE World Layer', style: theme.textTheme.titleMedium),
            ],
          ),
          const SizedBox(height: 14),
          _statusRow('Public-world learning', learning, Colors.cyanAccent),
          _statusRow('Source-traceable knowledge', true, Colors.greenAccent),
          _statusRow('Self-modification blocked', !selfModification, Colors.purpleAccent),
          _statusRow('Human review for upgrades', true, Colors.amberAccent),
        ],
      ),
    );
  }

  Widget _statusRow(String label, bool enabled, Color accent) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 10),
      child: Row(
        children: [
          Icon(enabled ? Icons.check_circle_outline : Icons.remove_circle_outline, size: 18, color: accent),
          const SizedBox(width: 9),
          Expanded(child: Text(label)),
          Text(enabled ? 'ON' : 'OFF', style: TextStyle(fontSize: 11, color: accent)),
        ],
      ),
    );
  }

  Widget _sectionHeader(String title, IconData icon) {
    return Row(
      children: [
        Icon(icon, size: 18, color: Colors.lightBlueAccent),
        const SizedBox(width: 8),
        Text(title, style: const TextStyle(fontWeight: FontWeight.w600)),
      ],
    );
  }

  Widget _topicWrap(List<dynamic> values) {
    return Wrap(
      spacing: 7,
      runSpacing: 7,
      children: values
          .map((value) => Container(
                padding: const EdgeInsets.symmetric(horizontal: 11, vertical: 7),
                decoration: BoxDecoration(
                  color: Colors.white.withOpacity(.035),
                  borderRadius: BorderRadius.circular(30),
                  border: Border.all(color: Colors.blueAccent.withOpacity(.20)),
                ),
                child: Text('$value', style: const TextStyle(fontSize: 12)),
              ))
          .toList(),
    );
  }

  Widget _knowledgeCard(ThemeData theme, dynamic item) {
    final data = item is Map ? item : const <String, dynamic>{};
    final topic = data['topic'] ?? 'World knowledge';
    final title = data['title'] ?? data['summary'] ?? 'Knowledge update';
    final sourceCount = data['source_count'] ?? data['sources_count'];
    final updatedAt = data['updated_at'] ?? data['created_at'] ?? data['refreshed_at'];
    return Container(
      margin: const EdgeInsets.only(bottom: 9),
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: const Color(0xFF04080E),
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: Colors.white.withOpacity(.08)),
      ),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Icon(Icons.bolt, size: 18, color: Colors.cyanAccent),
          const SizedBox(width: 10),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text('$topic', style: const TextStyle(fontSize: 11, color: Colors.lightBlueAccent)),
                const SizedBox(height: 4),
                Text('$title', style: theme.textTheme.bodyMedium),
                if (sourceCount != null) ...[
                  Text(updatedAt == null ? 'No refresh timestamp' : 'Updated $updatedAt', style: theme.textTheme.bodySmall),
                  const SizedBox(width: 10),
                  const SizedBox(height: 5),
                  Text('$sourceCount sources', style: theme.textTheme.bodySmall),
                ],
              ],
            ),
          ),
        ],
      ),
    );
  }

  Widget _errorCard(ThemeData theme) {
    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: Colors.red.withOpacity(.06),
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: Colors.redAccent.withOpacity(.25)),
      ),
      child: Text(_error!, style: theme.textTheme.bodySmall),
    );
  }

  Widget _emptyCard(ThemeData theme) {
    return Container(
      padding: const EdgeInsets.all(20),
      decoration: BoxDecoration(
        color: Colors.white.withOpacity(.025),
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: Colors.white.withOpacity(.08)),
      ),
      child: Text(
        'No world knowledge has been persisted yet. Refresh to let the bounded Research OS collect and verify public information.',
        style: theme.textTheme.bodySmall,
      ),
    );
  }
}
