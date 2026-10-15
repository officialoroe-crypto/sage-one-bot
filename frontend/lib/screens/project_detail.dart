import 'package:flutter/material.dart';

import '../core/sage_api.dart';
import '../theme/sage_theme.dart';

class ProjectDetailScreen extends StatefulWidget {
  const ProjectDetailScreen({required this.api, required this.project, super.key});
  final SageApi api;
  final Map<String, dynamic> project;

  @override
  State<ProjectDetailScreen> createState() => _ProjectDetailScreenState();
}

class _ProjectDetailScreenState extends State<ProjectDetailScreen> {
  bool _loading = true;
  String? _error;
  List<dynamic> _assets = const [];
  List<dynamic> _relations = const [];
  List<dynamic> _workflows = const [];
  bool _commandBusy = false;
  final TextEditingController _projectCommandController = TextEditingController();
  final TextEditingController _assetNameController = TextEditingController();

  String get _projectId => widget.project['id']?.toString() ?? '';

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _runProjectCommand() async {
    if (_projectId.isEmpty || _commandBusy) return;
    _projectCommandController.clear();
    var submitting = false;
    String? errorMessage;

    setState(() => _commandBusy = true);
    try {
      await showDialog<void>(
        context: context,
        builder: (dialogContext) => StatefulBuilder(
          builder: (dialogContext, setDialogState) => AlertDialog(
            title: const Text('Run SAGE in this project'),
            content: Column(
              mainAxisSize: MainAxisSize.min,
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                TextField(
                  controller: _projectCommandController,
                  autofocus: true,
                  minLines: 2,
                  maxLines: 5,
                  onChanged: (_) => setDialogState(() => errorMessage = null),
                  decoration: const InputDecoration(
                    hintText: 'Tell SAGE what to do with this project…',
                  ),
                ),
                if (errorMessage != null) ...[
                  const SizedBox(height: 8),
                  Text(
                    errorMessage!,
                    style: const TextStyle(color: SageTheme.failure),
                  ),
                ],
              ],
            ),
            actions: [
              TextButton(
                onPressed: submitting ? null : () => Navigator.pop(dialogContext),
                child: const Text('Cancel'),
              ),
              FilledButton(
                onPressed: _projectCommandController.text.trim().isEmpty || submitting
                    ? null
                    : () async {
                        final command = _projectCommandController.text.trim();
                        setDialogState(() {
                          submitting = true;
                          errorMessage = null;
                        });
                        try {
                          final response = await widget.api.submitCommand(
                            command,
                            projectId: _projectId,
                          );
                          final task = response['task'];
                          final taskId = task is Map
                              ? task['id']?.toString()
                              : response['task_id']?.toString();
                          if (!dialogContext.mounted) return;
                          Navigator.pop(dialogContext);
                          if (mounted) {
                            ScaffoldMessenger.of(context).showSnackBar(
                              SnackBar(
                                content: Text(
                                  taskId == null
                                      ? 'Project command queued.'
                                      : 'Project task queued: $taskId',
                                ),
                              ),
                            );
                          }
                        } catch (error) {
                          if (dialogContext.mounted) {
                            setDialogState(() {
                              submitting = false;
                              errorMessage = 'Could not queue project command: $error';
                            });
                          }
                        }
                      },
                child: submitting
                    ? const SizedBox(
                        width: 18,
                        height: 18,
                        child: CircularProgressIndicator(strokeWidth: 2),
                      )
                    : const Text('Queue'),
              ),
            ],
          ),
        ),
      );
    } finally {
      if (mounted) setState(() => _commandBusy = false);
    }
  }

  Future<void> _addAsset() async {
    if (_projectId.isEmpty) return;
    _assetNameController.clear();
    var assetType = 'image';
    var creating = false;
    String? errorMessage;
    final created = await showDialog<bool>(
      context: context,
      builder: (dialogContext) => StatefulBuilder(
        builder: (dialogContext, setDialogState) => AlertDialog(
          title: const Text('Add workflow asset'),
          content: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              TextField(
                controller: _assetNameController,
                autofocus: true,
                onChanged: (_) => setDialogState(() => errorMessage = null),
                decoration: const InputDecoration(labelText: 'Asset name'),
              ),
              const SizedBox(height: 12),
              if (errorMessage != null) ...[
                const SizedBox(height: 8),
                Text(errorMessage!, style: const TextStyle(color: SageTheme.failure)),
              ],
              DropdownButtonFormField<String>(
                value: assetType,
                decoration: const InputDecoration(labelText: 'Type'),
                items: const [
                  DropdownMenuItem(value: 'idea', child: Text('Idea')),
                  DropdownMenuItem(value: 'script', child: Text('Script')),
                  DropdownMenuItem(value: 'audio', child: Text('Audio')),
                  DropdownMenuItem(value: 'image', child: Text('Image')),
                  DropdownMenuItem(value: 'video', child: Text('Video')),
                  DropdownMenuItem(value: 'edit', child: Text('Edit')),
                  DropdownMenuItem(value: 'thumbnail', child: Text('Thumbnail')),
                  DropdownMenuItem(value: 'caption', child: Text('Caption')),
                ],
                onChanged: (value) => setDialogState(() => assetType = value ?? 'image'),
              ),
            ],
          ),
          actions: [
            TextButton(
              onPressed: () => Navigator.pop(dialogContext, false),
              child: const Text('Cancel'),
            ),
            FilledButton(
              onPressed: _assetNameController.text.trim().isEmpty || creating
                  ? null
                  : () async {
                      final value = _assetNameController.text.trim();
                      setDialogState(() {
                        creating = true;
                        errorMessage = null;
                      });
                      try {
                        await widget.api.createWorkflowAsset(
                          projectId: _projectId,
                          name: value,
                          assetType: assetType,
                        );
                        if (dialogContext.mounted) Navigator.pop(dialogContext, true);
                      } catch (error) {
                        if (dialogContext.mounted) {
                          setDialogState(() {
                            creating = false;
                            errorMessage = 'Could not create asset: $error';
                          });
                        }
                      }
                    },
              child: creating
                  ? const SizedBox(
                      width: 18,
                      height: 18,
                      child: CircularProgressIndicator(strokeWidth: 2),
                    )
                  : const Text('Create'),
            ),
          ],
        ),
      ),
    );
    if (created == true && mounted) await _load();
  }

  Future<void> _linkAssets() async {
    if (_assets.length < 2 || _projectId.isEmpty) return;
    String sourceId = _value(_assets.first, 'id');
    String targetId = _value(_assets[1], 'id');
    var relationType = 'derived_from';
    final created = await showDialog<bool>(
      context: context,
      builder: (dialogContext) => StatefulBuilder(
        builder: (dialogContext, setDialogState) {
          final ids = _assets.map((asset) => _value(asset, 'id')).toList();
          return AlertDialog(
            title: const Text('Connect assets'),
            content: Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                DropdownButtonFormField<String>(
                  value: sourceId,
                  decoration: const InputDecoration(labelText: 'Source'),
                  items: [
                    for (final asset in _assets)
                      DropdownMenuItem(
                        value: _value(asset, 'id'),
                        child: Text(_value(asset, 'name', 'Asset')),
                      ),
                  ],
                  onChanged: (value) {
                    if (value != null) setDialogState(() => sourceId = value);
                  },
                ),
                const SizedBox(height: 10),
                DropdownButtonFormField<String>(
                  value: targetId,
                  decoration: const InputDecoration(labelText: 'Target'),
                  items: [
                    for (final asset in _assets)
                      DropdownMenuItem(
                        value: _value(asset, 'id'),
                        child: Text(_value(asset, 'name', 'Asset')),
                      ),
                  ],
                  onChanged: (value) {
                    if (value != null) setDialogState(() => targetId = value);
                  },
                ),
                const SizedBox(height: 10),
                DropdownButtonFormField<String>(
                  value: relationType,
                  decoration: const InputDecoration(labelText: 'Relationship'),
                  items: const [
                    DropdownMenuItem(value: 'derived_from', child: Text('Derived from')),
                    DropdownMenuItem(value: 'version_of', child: Text('Version of')),
                    DropdownMenuItem(value: 'contains', child: Text('Contains')),
                    DropdownMenuItem(value: 'references', child: Text('References')),
                    DropdownMenuItem(value: 'selected_for', child: Text('Selected for')),
                    DropdownMenuItem(value: 'published_as', child: Text('Published as')),
                    DropdownMenuItem(value: 'generated_by', child: Text('Generated by')),
                    DropdownMenuItem(value: 'verified_by', child: Text('Verified by')),
                  ],
                  onChanged: (value) {
                    if (value != null) setDialogState(() => relationType = value);
                  },
                ),
                const SizedBox(height: 8),
                Text(
                  ids.contains(sourceId) && ids.contains(targetId)
                      ? 'SAGE will persist this relationship in the project graph.'
                      : 'Choose two project assets.',
                  style: const TextStyle(color: SageTheme.textSecondary, fontSize: 10),
                ),
              ],
            ),
            actions: [
              TextButton(
                onPressed: () => Navigator.pop(dialogContext, false),
                child: const Text('Cancel'),
              ),
              FilledButton(
                onPressed: sourceId == targetId
                    ? null
                    : () async {
                        try {
                          await widget.api.createWorkflowRelation(
                            projectId: _projectId,
                            sourceAssetId: sourceId,
                            targetAssetId: targetId,
                            relationType: relationType,
                          );
                          if (dialogContext.mounted) Navigator.pop(dialogContext, true);
                        } catch (error) {
                          if (dialogContext.mounted) {
                            ScaffoldMessenger.of(dialogContext).showSnackBar(
                              SnackBar(content: Text(error.toString())),
                            );
                          }
                        }
                      },
                child: const Text('Connect'),
              ),
            ],
          );
        },
      ),
    );
    if (created == true && mounted) await _load();
  }

  @override
  void dispose() {
    _projectCommandController.dispose();
    _assetNameController.dispose();
    super.dispose();
  }

  Future<void> _load() async {
    if (_projectId.isEmpty) {
      setState(() {
        _loading = false;
        _error = 'Project ID is missing.';
      });
      return;
    }
    try {
      final results = await Future.wait([
        widget.api.workflowAssets(_projectId),
        widget.api.workflowRelations(_projectId),
        widget.api.workflowDefinitions(_projectId),
      ]);
      if (!mounted) return;
      setState(() {
        _assets = results[0];
        _relations = results[1];
        _workflows = results[2];
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

  String _value(dynamic item, String key, [String fallback = '']) =>
      item is Map ? item[key]?.toString() ?? fallback : fallback;

  @override
  Widget build(BuildContext context) {
    final name = _value(widget.project, 'name', 'Project');
    final type = _value(widget.project, 'project_type', 'general').toUpperCase();
    final description = _value(widget.project, 'description');

    return Scaffold(
      appBar: AppBar(
        title: const Text('PROJECT'),
        actions: [
          IconButton(
            tooltip: 'Run SAGE command',
            onPressed: _commandBusy ? null : _runProjectCommand,
            icon: Icon(_commandBusy ? Icons.hourglass_top : Icons.play_circle_outline),
          ),
          IconButton(
            tooltip: 'Connect assets',
            onPressed: _loading || _assets.length < 2 ? null : _linkAssets,
            icon: const Icon(Icons.account_tree_outlined),
          ),
          IconButton(
            tooltip: 'Add asset',
            onPressed: _loading ? null : _addAsset,
            icon: const Icon(Icons.add_box_outlined),
          ),
          IconButton(
            tooltip: 'Refresh',
            onPressed: _loading ? null : _load,
            icon: const Icon(Icons.refresh),
          ),
        ],
      ),
      body: RefreshIndicator(
        onRefresh: _load,
        child: ListView(
          physics: const AlwaysScrollableScrollPhysics(),
          padding: const EdgeInsets.fromLTRB(18, 8, 18, 36),
          children: [
            _hero(name, type, description),
            const SizedBox(height: 18),
            if (_loading)
              const Padding(
                padding: EdgeInsets.symmetric(vertical: 70),
                child: Center(child: CircularProgressIndicator()),
              )
            else if (_error != null)
              _errorCard(_error!),
            if (!_loading && _error == null) ...[
              _metricRow(),
              const SizedBox(height: 18),
              _section('WORKFLOW', _workflowBody()),
              const SizedBox(height: 14),
              _section('ASSET GRAPH', _assetBody()),
              const SizedBox(height: 14),
              _section('RELATION GRAPH', _relationBody()),
            ],
          ],
        ),
      ),
    );
  }

  Widget _hero(String name, String type, String description) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(18),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Container(
                  width: 46,
                  height: 46,
                  decoration: BoxDecoration(
                    shape: BoxShape.circle,
                    color: SageTheme.violet.withValues(alpha: .09),
                    border: Border.all(
                      color: SageTheme.violet.withValues(alpha: .35),
                    ),
                  ),
                  child: const Icon(Icons.account_tree, color: SageTheme.violet),
                ),
                const SizedBox(width: 13),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(type, style: const TextStyle(
                        fontSize: 9, letterSpacing: 1.6,
                        color: SageTheme.violet, fontWeight: FontWeight.w800,
                      )),
                      const SizedBox(height: 4),
                      Text(name, style: const TextStyle(
                        fontSize: 23, fontWeight: FontWeight.w700,
                      )),
                    ],
                  ),
                ),
              ],
            ),
            if (description.isNotEmpty) ...[
              const SizedBox(height: 15),
              Text(description, style: const TextStyle(
                color: SageTheme.textSecondary, height: 1.45,
              )),
            ],
          ],
        ),
      ),
    );
  }

  Widget _metricRow() {
    return Row(
      children: [
        _metric('ASSETS', _assets.length),
        const SizedBox(width: 8),
        _metric('LINKS', _relations.length),
        const SizedBox(width: 8),
        _metric('FLOWS', _workflows.length),
      ],
    );
  }

  Widget _metric(String label, int value) {
    return Expanded(
      child: Card(
        child: Padding(
          padding: const EdgeInsets.symmetric(vertical: 13),
          child: Column(
            children: [
              Text('$value', style: const TextStyle(
                fontSize: 21, fontWeight: FontWeight.w800,
              )),
              const SizedBox(height: 3),
              Text(label, style: const TextStyle(
                fontSize: 8, letterSpacing: 1.2,
                color: SageTheme.textSecondary,
              )),
            ],
          ),
        ),
      ),
    );
  }

  Widget _section(String title, Widget body) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(15),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(title, style: const TextStyle(
              fontSize: 10, letterSpacing: 1.5,
              fontWeight: FontWeight.w800, color: SageTheme.textSecondary,
            )),
            const SizedBox(height: 11),
            body,
          ],
        ),
      ),
    );
  }

  Widget _workflowBody() {
    if (_workflows.isEmpty) {
      return const Text('No workflow has been attached yet.',
          style: TextStyle(color: SageTheme.textSecondary));
    }
    return Column(
      children: [
        for (final workflow in _workflows) ...[
          ListTile(
            contentPadding: EdgeInsets.zero,
            leading: const Icon(Icons.route, color: SageTheme.violet),
            title: Text(_value(workflow, 'name', 'Workflow'),
                style: const TextStyle(fontWeight: FontWeight.w700)),
            subtitle: Text(
              '${_value(workflow, 'workflow_type', 'workflow')} • '
              '${_value(workflow, 'current_stage', 'not started')}',
            ),
          ),
          if (workflow != _workflows.last) const Divider(height: 1),
        ],
      ],
    );
  }

  Widget _assetBody() {
    if (_assets.isEmpty) {
      return const Text(
        'No assets yet. Create or import an asset to start the graph.',
        style: TextStyle(color: SageTheme.textSecondary),
      );
    }
    return Column(
      children: [
        for (final asset in _assets) ...[
          ListTile(
            contentPadding: EdgeInsets.zero,
            leading: Icon(_assetIcon(_value(asset, 'asset_type'))),
            title: Text(_value(asset, 'name', 'Asset'),
                style: const TextStyle(fontWeight: FontWeight.w600)),
            subtitle: Text(
              '${_value(asset, 'asset_type', 'asset')} • '
              '${_value(asset, 'status', 'draft')}',
            ),
          ),
          if (asset != _assets.last) const Divider(height: 1),
        ],
      ],
    );
  }

  Widget _relationBody() {
    if (_relations.isEmpty) {
      return const Text('No asset relationships yet.',
          style: TextStyle(color: SageTheme.textSecondary));
    }
    return Column(
      children: [
        for (final relation in _relations) ...[
          ListTile(
            contentPadding: EdgeInsets.zero,
            dense: true,
            leading: const Icon(Icons.link, size: 18),
            title: Text(
              _value(relation, 'relation_type', 'relation').toUpperCase(),
              style: const TextStyle(fontSize: 10, fontWeight: FontWeight.w800),
            ),
            subtitle: Text(
              '${_value(relation, 'source_asset_id', 'source')} → '
              '${_value(relation, 'target_asset_id', 'target')}',
              maxLines: 2,
              overflow: TextOverflow.ellipsis,
            ),
          ),
          if (relation != _relations.last) const Divider(height: 1),
        ],
      ],
    );
  }

  IconData _assetIcon(String type) {
    final normalized = type.toLowerCase();
    if (normalized.contains('video')) return Icons.movie_outlined;
    if (normalized.contains('image')) return Icons.image_outlined;
    if (normalized.contains('audio')) return Icons.graphic_eq;
    if (normalized.contains('script') || normalized.contains('text')) return Icons.article_outlined;
    if (normalized.contains('thumbnail')) return Icons.photo_size_select_large;
    return Icons.insert_drive_file_outlined;
  }

  Widget _errorCard(String message) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Row(
          children: [
            const Icon(Icons.error_outline, color: SageTheme.failure),
            const SizedBox(width: 10),
            Expanded(child: Text(message)),
          ],
        ),
      ),
    );
  }
}
