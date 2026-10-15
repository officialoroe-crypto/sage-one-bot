import 'package:flutter/material.dart';

import '../core/sage_api.dart';
import '../theme/sage_theme.dart';

class CreateScreen extends StatefulWidget {
  const CreateScreen({required this.api, super.key});
  final SageApi api;

  @override
  State<CreateScreen> createState() => _CreateScreenState();
}

class _CreateScreenState extends State<CreateScreen> {
  final _projectName = TextEditingController();
  final _description = TextEditingController();
  String _projectType = 'content';
  List<dynamic> _workspaces = const [];
  String? _workspaceId;
  bool _loading = true;
  bool _creating = false;

  static const _contentStages = [
    'idea', 'script', 'audio', 'images', 'video', 'edit',
    'thumbnail', 'caption', 'platform_versions', 'publish',
    'analyze', 'improve',
  ];

  @override
  void initState() {
    super.initState();
    _loadWorkspaces();
  }

  Future<void> _loadWorkspaces() async {
    try {
      final workspaces = await widget.api.workflowWorkspaces();
      if (!mounted) return;
      final validWorkspaces = workspaces
          .whereType<Map>()
          .where((item) => item['id'] != null)
          .map((item) => Map<String, dynamic>.from(item))
          .toList(growable: false);
      setState(() {
        _workspaces = validWorkspaces;
        _workspaceId = validWorkspaces.isNotEmpty ? _id(validWorkspaces.first) : null;
        _loading = false;
      });
    } catch (error) {
      if (!mounted) return;
      setState(() => _loading = false);
      _error(error);
    }
  }

  String _id(dynamic value) =>
      (value is Map ? value['id'] : null)?.toString() ?? '';

  String _name(dynamic value) =>
      (value is Map ? value['name'] : null)?.toString() ?? 'Workspace';

  Future<void> _initializeWorkspace() async {
    setState(() => _creating = true);
    try {
      final result = await widget.api.createWorkflowWorkspace(
        name: 'Personal',
        slug: 'personal',
        workspaceType: 'personal',
      );
      final workspace = result['workspace'];
      if (!mounted) return;
      if (workspace is Map) {
        setState(() {
          _workspaces = [workspace];
          _workspaceId = workspace['id']?.toString();
        });
      }
    } catch (error) {
      if (mounted) _error(error);
    } finally {
      if (mounted) setState(() => _creating = false);
    }
  }

  Future<void> _createProject() async {
    final name = _projectName.text.trim();
    final workspaceId = _workspaceId;
    if (name.isEmpty || name.length > 120 || workspaceId == null || _creating) {
      if (mounted && name.length > 120) {
        _error(const FormatException('Project name must be 120 characters or fewer.'));
      }
      return;
    }

    setState(() => _creating = true);
    try {
      final result = await widget.api.createWorkflowProject(
        workspaceId: workspaceId,
        name: name,
        projectType: _projectType,
        description:
            _description.text.trim().isEmpty ? null : _description.text.trim(),
        metadata: {
          'created_from': 'mobile_create',
          'workflow_version': 1,
        },
      );
      final project = result['project'];

      if (project is Map &&
          project['id'] != null &&
          _projectType == 'content') {
        await widget.api.createWorkflow(
          projectId: project['id'].toString(),
          name: '$name Content Pipeline',
          workflowType: 'content',
          currentStage: 'idea',
          definition: {
            'version': 1,
            'stages': _contentStages,
            'next_stage': 'idea',
          },
        );
      }

      if (!mounted) return;
      _projectName.clear();
      _description.clear();
      final workspaceName = _workspaces
          .where((item) => _id(item) == workspaceId)
          .map(_name)
          .firstOrNull ?? 'workspace';
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('$name created in $workspaceName.')),
      );
    } catch (error) {
      if (mounted) _error(error);
    } finally {
      if (mounted) setState(() => _creating = false);
    }
  }

  void _error(Object error) {
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        backgroundColor: SageTheme.failure,
        content: Text(error.toString()),
      ),
    );
  }

  @override
  void dispose() {
    _projectName.dispose();
    _description.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return SafeArea(
      child: CustomScrollView(
        slivers: [
          SliverPadding(
            padding: const EdgeInsets.fromLTRB(18, 18, 18, 8),
            sliver: SliverToBoxAdapter(child: _header()),
          ),
          SliverPadding(
            padding: const EdgeInsets.fromLTRB(18, 8, 18, 32),
            sliver: SliverToBoxAdapter(child: _body()),
          ),
        ],
      ),
    );
  }

  Widget _header() {
    return Row(
      children: [
        Container(
          width: 42,
          height: 42,
          decoration: BoxDecoration(
            shape: BoxShape.circle,
            color: SageTheme.surface,
            border: Border.all(
              color: SageTheme.violet.withValues(alpha: .42),
            ),
            boxShadow: [
              BoxShadow(
                color: SageTheme.violet.withValues(alpha: .14),
                blurRadius: 18,
              ),
            ],
          ),
          child: const Icon(Icons.auto_awesome, color: SageTheme.violet),
        ),
        const SizedBox(width: 12),
        const Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              'CREATE',
              style: TextStyle(
                fontSize: 11,
                letterSpacing: 2,
                color: SageTheme.violet,
                fontWeight: FontWeight.w800,
              ),
            ),
            SizedBox(height: 3),
            Text(
              'Turn an idea into a project',
              style: TextStyle(fontSize: 21, fontWeight: FontWeight.w700),
            ),
          ],
        ),
      ],
    );
  }

  Widget _body() {
    if (_loading) {
      return const Padding(
        padding: EdgeInsets.only(top: 70),
        child: Center(child: CircularProgressIndicator()),
      );
    }

    if (_workspaces.isEmpty) {
      return Card(
        child: Padding(
          padding: const EdgeInsets.all(20),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              const Icon(Icons.account_tree, color: SageTheme.violet, size: 28),
              const SizedBox(height: 14),
              const Text(
                'Initialize your workspace',
                style: TextStyle(fontSize: 19, fontWeight: FontWeight.w700),
              ),
              const SizedBox(height: 7),
              const Text(
                'SAGE WORKFLOW needs one workspace before it can persist '
                'projects, assets and workflows.',
                style: TextStyle(
                  color: SageTheme.textSecondary,
                  height: 1.45,
                ),
              ),
              const SizedBox(height: 18),
              FilledButton.icon(
                onPressed: _creating ? null : _initializeWorkspace,
                icon: const Icon(Icons.add),
                label: Text(
                  _creating ? 'Initializing…' : 'Initialize Personal',
                ),
              ),
            ],
          ),
        ),
      );
    }

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        _sectionLabel('WORKSPACE'),
        const SizedBox(height: 8),
        DropdownButtonFormField<String>(
          initialValue: _workspaceId,
          decoration: const InputDecoration(
            prefixIcon: Icon(Icons.folder_open),
            hintText: 'Choose workspace',
          ),
          items: [
            for (final workspace in _workspaces)
              DropdownMenuItem(
                value: _id(workspace),
                child: Text(_name(workspace)),
              ),
          ],
          onChanged: (value) => setState(() => _workspaceId = value),
        ),
        const SizedBox(height: 22),
        _sectionLabel('PROJECT'),
        const SizedBox(height: 8),
        TextField(
          controller: _projectName,
          textCapitalization: TextCapitalization.sentences,
          decoration: const InputDecoration(
            prefixIcon: Icon(Icons.auto_awesome),
            hintText: 'Project name',
          ),
          onChanged: (_) => setState(() {}),
        ),
        const SizedBox(height: 12),
        DropdownButtonFormField<String>(
          initialValue: _projectType,
          decoration: const InputDecoration(
            prefixIcon: Icon(Icons.category_outlined),
            hintText: 'Project type',
          ),
          items: const [
            DropdownMenuItem(
              value: 'content',
              child: Text('Content Project'),
            ),
            DropdownMenuItem(value: 'brand', child: Text('Brand Project')),
            DropdownMenuItem(
              value: 'general',
              child: Text('General Project'),
            ),
          ],
          onChanged: (value) =>
              setState(() => _projectType = value ?? 'content'),
        ),
        const SizedBox(height: 12),
        TextField(
          controller: _description,
          minLines: 3,
          maxLines: 5,
          decoration: const InputDecoration(
            hintText: 'What are we trying to achieve?',
            alignLabelWithHint: true,
          ),
        ),
        const SizedBox(height: 18),
        _pipelinePreview(),
        const SizedBox(height: 20),
        SizedBox(
          width: double.infinity,
          child: FilledButton.icon(
            onPressed: _creating || _projectName.text.trim().isEmpty
                ? null
                : _createProject,
            icon: Icon(
              _creating ? Icons.hourglass_top : Icons.rocket_launch,
            ),
            label: Text(_creating ? 'Building…' : 'Create Project'),
          ),
        ),
      ],
    );
  }

  Widget _sectionLabel(String text) => Text(
        text,
        style: const TextStyle(
          fontSize: 9,
          letterSpacing: 1.8,
          color: SageTheme.textSecondary,
          fontWeight: FontWeight.w800,
        ),
      );

  Widget _pipelinePreview() {
    if (_projectType != 'content') return const SizedBox.shrink();

    return Card(
      child: Padding(
        padding: const EdgeInsets.all(15),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Row(
              children: [
                Icon(Icons.route, size: 17, color: SageTheme.violet),
                SizedBox(width: 8),
                Text(
                  'SAGE CONTENT PIPELINE',
                  style: TextStyle(
                    fontSize: 10,
                    letterSpacing: 1.3,
                    fontWeight: FontWeight.w800,
                  ),
                ),
              ],
            ),
            const SizedBox(height: 11),
            Wrap(
              spacing: 6,
              runSpacing: 6,
              children: [
                for (final stage in _contentStages)
                  Container(
                    padding: const EdgeInsets.symmetric(
                      horizontal: 8,
                      vertical: 5,
                    ),
                    decoration: BoxDecoration(
                      color: SageTheme.violet.withValues(alpha: .08),
                      borderRadius: BorderRadius.circular(8),
                      border: Border.all(
                        color: SageTheme.violet.withValues(alpha: .18),
                      ),
                    ),
                    child: Text(
                      stage.replaceAll('_', ' ').toUpperCase(),
                      style: const TextStyle(
                        fontSize: 7,
                        letterSpacing: .6,
                        color: SageTheme.textSecondary,
                      ),
                    ),
                  ),
              ],
            ),
          ],
        ),
      ),
    );
  }
}
