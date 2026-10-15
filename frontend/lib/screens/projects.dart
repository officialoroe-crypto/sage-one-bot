import 'package:flutter/material.dart';

import '../core/sage_api.dart';
import '../theme/sage_theme.dart';

class ProjectsScreen extends StatefulWidget {
  const ProjectsScreen({required this.api, required this.onProjectTap, super.key});
  final SageApi api;
  final ValueChanged<Map<String, dynamic>> onProjectTap;

  @override
  State<ProjectsScreen> createState() => _ProjectsScreenState();
}

class _ProjectsScreenState extends State<ProjectsScreen> {
  bool _loading = true;
  String? _error;
  List<dynamic> _projects = const [];

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    try {
      final workspaces = await widget.api.workflowWorkspaces();
      if (workspaces.isEmpty) {
        if (!mounted) return;
        setState(() {
          _projects = const [];
          _loading = false;
        });
        return;
      }
      final results = await Future.wait(
        workspaces.map((workspace) {
          final id = workspace is Map ? workspace['id']?.toString() : null;
          return id == null ? Future.value(<dynamic>[]) : widget.api.workflowProjects(id);
        }),
      );
      if (!mounted) return;
      setState(() {
        _projects = results
            .expand((items) => items)
            .whereType<Map>()
            .where((item) => item['id'] != null)
            .map((item) => Map<String, dynamic>.from(item))
            .toList(growable: false);
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
    return SafeArea(
      child: RefreshIndicator(
        onRefresh: _load,
        child: ListView(
          physics: const AlwaysScrollableScrollPhysics(),
          padding: const EdgeInsets.fromLTRB(20, 24, 20, 32),
          children: [
            const Row(
              children: [
                Icon(Icons.account_tree, color: SageTheme.violet),
                SizedBox(width: 12),
                Text('WORKFLOW', style: TextStyle(
                  fontSize: 11, letterSpacing: 2,
                  color: SageTheme.textSecondary,
                  fontWeight: FontWeight.w800,
                )),
              ],
            ),
            const SizedBox(height: 18),
            const Text('Projects', style: TextStyle(fontSize: 27, fontWeight: FontWeight.w700)),
            const SizedBox(height: 7),
            const Text(
              'Projects are living workspaces connecting outcomes, assets and workflows.',
              style: TextStyle(color: SageTheme.textSecondary, height: 1.45),
            ),
            const SizedBox(height: 20),
            if (_loading)
              const Padding(
                padding: EdgeInsets.symmetric(vertical: 80),
                child: Center(child: CircularProgressIndicator()),
              )
            else if (_error != null)
              Card(
                child: Padding(
                  padding: const EdgeInsets.all(16),
                  child: Text(_error!),
                ),
              )
            else if (_projects.isEmpty)
              const Card(
                child: Padding(
                  padding: EdgeInsets.all(18),
                  child: Text(
                    'No workflow projects yet. Use Create to initialize your first project.',
                    style: TextStyle(color: SageTheme.textSecondary, height: 1.45),
                  ),
                ),
              )
            else
              for (final project in _projects)
                Card(
                  margin: const EdgeInsets.only(bottom: 10),
                  child: ListTile(
                    onTap: project is Map<String, dynamic>
                        ? () => widget.onProjectTap(project)
                        : null,
                    leading: const Icon(Icons.folder_open, color: SageTheme.violet),
                    title: Text(
                      _value(project, 'name', 'Project'),
                      style: const TextStyle(fontWeight: FontWeight.w700),
                    ),
                    subtitle: Text(
                      '${_value(project, 'project_type', 'general')} • '
                      '${_value(project, 'status', 'active')}',
                    ),
                    trailing: const Icon(Icons.chevron_right),
                  ),
                ),
          ],
        ),
      ),
    );
  }
}
