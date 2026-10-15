import 'package:flutter/material.dart';

import '../core/sage_api.dart';
import '../theme/sage_theme.dart';

class LearningScreen extends StatefulWidget {
  const LearningScreen({required this.api, super.key});

  final SageApi api;

  @override
  State<LearningScreen> createState() => _LearningScreenState();
}

class _LearningScreenState extends State<LearningScreen> {
  bool _loading = true;
  Object? _error;
  String? _completingLessonId;
  List<dynamic> _paths = const [];

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load({bool showLoader = true}) async {
    if (!mounted) return;
    setState(() {
      if (showLoader) _loading = true;
      _error = null;
    });
    try {
      final paths = await widget.api.learningPaths();
      if (!mounted) return;
      setState(() {
        _paths = paths;
        _error = null;
      });
    } catch (error) {
      if (!mounted) return;
      setState(() => _error = error);
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  Future<bool> _completeLesson(Map<String, dynamic> lesson) async {
    final lessonId = (lesson['id'] ?? '').toString();
    if (lessonId.isEmpty || lesson['is_completed'] == true || _completingLessonId != null) {
      return false;
    }

    setState(() => _completingLessonId = lessonId);
    try {
      await widget.api.completeLearningLesson(lessonId);
      if (!mounted) return false;
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Lesson marked complete. Your progress is saved.')),
      );
      await _load(showLoader: false);
      return true;
    } catch (error) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Could not save lesson progress: $error')),
        );
      }
      return false;
    } finally {
      if (mounted) setState(() => _completingLessonId = null);
    }
  }

  Future<void> _openLesson(
    Map<String, dynamic> path,
    Map<String, dynamic> lesson,
  ) async {
    await showDialog<void>(
      context: context,
      builder: (dialogContext) => StatefulBuilder(
        builder: (dialogContext, setDialogState) {
          final completed = lesson['is_completed'] == true;
          final lessonId = (lesson['id'] ?? '').toString();
          final busy = _completingLessonId == lessonId;
          return AlertDialog(
            title: Text((lesson['title'] ?? 'Lesson').toString()),
            content: SizedBox(
              width: 480,
              child: SingleChildScrollView(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    Text(
                      (path['title'] ?? 'Learning path').toString(),
                      style: TextStyle(
                        color: Theme.of(context).colorScheme.primary,
                        fontWeight: FontWeight.w700,
                      ),
                    ),
                    const SizedBox(height: 12),
                    Text(
                      (lesson['objective'] ?? '').toString(),
                      style: const TextStyle(fontWeight: FontWeight.w700, height: 1.4),
                    ),
                    const SizedBox(height: 12),
                    Text(
                      (lesson['content'] ?? '').toString(),
                      style: const TextStyle(height: 1.55),
                    ),
                    const SizedBox(height: 16),
                    Card(
                      child: Padding(
                        padding: const EdgeInsets.all(12),
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            const Text('TRY IT', style: TextStyle(fontWeight: FontWeight.w800)),
                            const SizedBox(height: 6),
                            Text((lesson['exercise'] ?? '').toString()),
                          ],
                        ),
                      ),
                    ),
                    const SizedBox(height: 8),
                    Text(
                      'About ${lesson['minutes'] ?? 5} minutes • Progress is saved to your account.',
                      style: const TextStyle(color: SageTheme.textSecondary, fontSize: 12),
                    ),
                  ],
                ),
              ),
            ),
            actions: [
              TextButton(
                onPressed: busy ? null : () => Navigator.pop(dialogContext),
                child: const Text('Close'),
              ),
              FilledButton.icon(
                onPressed: completed || busy
                    ? null
                    : () async {
                        setDialogState(() {});
                        final saved = await _completeLesson(lesson);
                        if (saved && dialogContext.mounted) {
                          Navigator.pop(dialogContext);
                        }
                      },
                icon: Icon(completed ? Icons.check_circle_outline : Icons.task_alt),
                label: Text(
                  completed
                      ? 'Completed'
                      : busy
                          ? 'Saving…'
                          : 'Mark complete',
                ),
              ),
            ],
          );
        },
      ),
    );
  }

  Map<String, dynamic> _asMap(dynamic value) =>
      value is Map ? Map<String, dynamic>.from(value) : <String, dynamic>{};

  List<Map<String, dynamic>> _lessons(dynamic value) {
    if (value is! List) return <Map<String, dynamic>>[];
    return value.map(_asMap).toList();
  }

  Widget _errorCard() => Card(
        child: Padding(
          padding: const EdgeInsets.all(16),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              const Text(
                'Learning paths could not load',
                style: TextStyle(color: SageTheme.failure, fontWeight: FontWeight.w700),
              ),
              const SizedBox(height: 6),
              Text(_error.toString()),
              const SizedBox(height: 8),
              Align(
                alignment: Alignment.centerRight,
                child: TextButton.icon(
                  onPressed: _loading ? null : _load,
                  icon: const Icon(Icons.refresh),
                  label: const Text('Retry'),
                ),
              ),
            ],
          ),
        ),
      );

  Widget _pathCard(Map<String, dynamic> path) {
    final lessons = _lessons(path['lessons']);
    final completed = (path['completed_lessons'] as num?)?.toInt() ?? 0;
    final total = (path['total_lessons'] as num?)?.toInt() ?? lessons.length;
    final rawProgress = path['progress_ratio'];
    final progress = rawProgress is num ? rawProgress.toDouble().clamp(0.0, 1.0).toDouble() : 0.0;
    final done = path['is_completed'] == true;
    return Card(
      clipBehavior: Clip.antiAlias,
      child: ExpansionTile(
        leading: CircleAvatar(
          backgroundColor: Theme.of(context).colorScheme.primary.withValues(alpha: .12),
          child: Icon(
            done ? Icons.check_circle_outline : Icons.school_outlined,
            color: Theme.of(context).colorScheme.primary,
          ),
        ),
        title: Text(
          (path['title'] ?? 'Learning path').toString(),
          style: const TextStyle(fontWeight: FontWeight.w800),
        ),
        subtitle: Padding(
          padding: const EdgeInsets.only(top: 5),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text((path['subtitle'] ?? '').toString()),
              const SizedBox(height: 8),
              LinearProgressIndicator(value: progress),
              const SizedBox(height: 5),
              Text(
                '$completed of $total lessons • ${path['level'] ?? 'Beginner'} • ${path['estimated_minutes'] ?? 0} min',
                style: const TextStyle(fontSize: 11, color: SageTheme.textSecondary),
              ),
            ],
          ),
        ),
        children: [
          if (lessons.isEmpty)
            const ListTile(title: Text('Lessons are not available yet.')),
          for (final lesson in lessons)
            ListTile(
              onTap: () => _openLesson(path, lesson),
              leading: Icon(
                lesson['is_completed'] == true
                    ? Icons.check_circle
                    : Icons.play_circle_outline,
                color: lesson['is_completed'] == true
                    ? Theme.of(context).colorScheme.primary
                    : SageTheme.textSecondary,
              ),
              title: Text((lesson['title'] ?? 'Lesson').toString()),
              subtitle: Text(
                '${lesson['minutes'] ?? 5} min • ${lesson['objective'] ?? ''}',
              ),
              trailing: const Icon(Icons.chevron_right),
            ),
        ],
      ),
    );
  }

  @override
  Widget build(BuildContext context) => Scaffold(
        backgroundColor: Theme.of(context).scaffoldBackgroundColor,
        appBar: AppBar(
          title: const Text('Learning'),
          backgroundColor: Colors.transparent,
          actions: [
            IconButton(
              tooltip: 'Refresh learning progress',
              onPressed: _loading ? null : _load,
              icon: const Icon(Icons.refresh),
            ),
          ],
        ),
        body: RefreshIndicator(
          onRefresh: _load,
          child: ListView(
            physics: const AlwaysScrollableScrollPhysics(),
            padding: const EdgeInsets.fromLTRB(16, 10, 16, 30),
            children: [
              Card(
                child: Padding(
                  padding: const EdgeInsets.all(16),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        'Learn by doing',
                        style: Theme.of(context).textTheme.titleLarge?.copyWith(
                              fontWeight: FontWeight.w800,
                            ),
                      ),
                      const SizedBox(height: 6),
                      const Text(
                        'Free, short lessons for digital confidence, freelancing and safer AI use. '
                        'Complete a lesson to save your progress and continue later.',
                        style: TextStyle(height: 1.45),
                      ),
                    ],
                  ),
                ),
              ),
              if (_error != null) _errorCard(),
              if (_loading && _paths.isEmpty)
                const Padding(
                  padding: EdgeInsets.symmetric(vertical: 56),
                  child: Center(child: CircularProgressIndicator()),
                )
              else if (_paths.isEmpty && _error == null)
                const Padding(
                  padding: EdgeInsets.symmetric(vertical: 56),
                  child: Text(
                    'No learning paths are available yet. Pull down to refresh.',
                    textAlign: TextAlign.center,
                  ),
                )
              else
                for (final raw in _paths) _pathCard(_asMap(raw)),
              const SizedBox(height: 8),
              const Text(
                'These are introductory learning materials, not accredited qualifications or guaranteed job training.',
                style: TextStyle(color: SageTheme.textSecondary, fontSize: 11, height: 1.4),
              ),
            ],
          ),
        ),
      );
}
