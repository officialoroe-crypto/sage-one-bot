import 'dart:async';

import 'package:flutter/material.dart';
import '../core/sage_api.dart';
import '../theme/sage_theme.dart';

class FeatureWorkspace extends StatefulWidget {
  const FeatureWorkspace({required this.title, required this.subtitle, required this.icon, required this.actions, super.key});
  final String title, subtitle; final IconData icon; final List<String> actions;
  @override State<FeatureWorkspace> createState() => _FeatureWorkspaceState();
}
class _FeatureWorkspaceState extends State<FeatureWorkspace> {
  Future<void> _explainAction(String action) async {
    await showDialog<void>(
      context: context,
      builder: (context) => AlertDialog(
        title: Text(action),
        content: Text(
          '${widget.title} is present in the SAGE ONE interface, but this action is not connected to a live workflow yet. '
          'It will not report success or change account data until its backend integration is implemented.',
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(context).pop(),
            child: const Text('Understood'),
          ),
        ],
      ),
    );
  }

  @override
  Widget build(BuildContext context) => Scaffold(
    backgroundColor: SageTheme.voidBlack,
    appBar: AppBar(title: Text(widget.title), backgroundColor: Colors.transparent),
    body: ListView(padding: const EdgeInsets.all(20), children: [
      Container(
        padding: const EdgeInsets.all(22),
        decoration: BoxDecoration(
          gradient: const LinearGradient(colors: [Color(0xFF0C2344), Color(0xFF07101E)]),
          borderRadius: BorderRadius.circular(24),
          border: Border.all(color: SageTheme.cyan.withValues(alpha: .18)),
        ),
        child: Row(children: [
          Container(
            width: 54,
            height: 54,
            alignment: Alignment.center,
            decoration: BoxDecoration(
              shape: BoxShape.circle,
              color: SageTheme.cyan.withValues(alpha: .1),
            ),
            child: Icon(widget.icon, color: SageTheme.cyan),
          ),
          const SizedBox(width: 16),
          Expanded(child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(widget.title, style: const TextStyle(
                fontSize: 22,
                fontWeight: FontWeight.w800,
                color: SageTheme.textPrimary,
              )),
              const SizedBox(height: 5),
              Text(widget.subtitle, style: const TextStyle(
                color: SageTheme.textSecondary,
                fontSize: 12,
                height: 1.4,
              )),
            ],
          )),
        ]),
      ),
      const SizedBox(height: 20),
      const Card(
        child: ListTile(
          leading: Icon(Icons.info_outline, color: SageTheme.textSecondary),
          title: Text('Integration status'),
          subtitle: Text(
            'Interface available • Live actions not connected yet',
          ),
        ),
      ),
      const SizedBox(height: 12),
      ...widget.actions.map((action) => Padding(
        padding: const EdgeInsets.only(bottom: 10),
        child: FilledButton.tonalIcon(
          onPressed: () => _explainAction(action),
          icon: const Icon(Icons.info_outline),
          label: Align(
            alignment: Alignment.centerLeft,
            child: Text(action),
          ),
        ),
      )),
    ]),
  );
}

enum _ChatRecoveryAction { session, command, history, taskStatus }

class ChatScreen extends StatefulWidget {
  const ChatScreen({required this.api, super.key});
  final SageApi api;

  @override
  State<ChatScreen> createState() => _ChatScreenState();
}

class _ChatScreenState extends State<ChatScreen> {
  static const int _maxPollFailures = 5;

  final _input = TextEditingController();
  final _scroll = ScrollController();
  final List<Map<String, String>> _messages = <Map<String, String>>[];
  String? _sessionId;
  String? _taskId;
  Timer? _poller;
  int _sessionGeneration = 0;
  int _pollFailures = 0;
  bool _pollInFlight = false;
  bool _sending = false;
  String _status = 'Ready';
  String? _chatError;
  _ChatRecoveryAction? _recoveryAction;

  @override
  void initState() {
    super.initState();
    _newSession();
  }

  Future<void> _newSession() async {
    // Invalidate in-flight work before clearing the previous conversation.
    final generation = ++_sessionGeneration;
    _poller?.cancel();
    _pollFailures = 0;
    if (mounted) {
      setState(() {
        _sessionId = null;
        _taskId = null;
        _sending = true;
        _status = 'Starting new session…';
        _chatError = null;
        _recoveryAction = null;
        _messages.clear();
      });
    }
    try {
      final session = await widget.api.createSession();
      final value = session['session'];
      final id = value is Map ? value['id']?.toString() : null;
      if (id == null || id.isEmpty) {
        throw Exception('SAGE did not return a session id.');
      }
      if (!mounted || generation != _sessionGeneration) return;
      setState(() {
        _sessionId = id;
        _sending = false;
        _status = 'Ready';
        _chatError = null;
        _recoveryAction = null;
      });
    } catch (error) {
      if (!mounted || generation != _sessionGeneration) return;
      setState(() {
        _sending = false;
        _status = 'Could not start chat';
        _chatError = 'Could not start chat. Check the API connection, then retry. Details: $error';
        _recoveryAction = _ChatRecoveryAction.session;
      });
    }
  }

  Future<void> _loadHistory({
    required int generation,
    required String sessionId,
  }) async {
    if (generation != _sessionGeneration || sessionId != _sessionId) return;
    try {
      final items = await widget.api.sessionMessages(sessionId);
      if (!mounted ||
          generation != _sessionGeneration ||
          sessionId != _sessionId) {
        return;
      }
      setState(() {
        _messages
          ..clear()
          ..addAll(items.whereType<Map>().map((item) => {
                'role': (item['role'] ?? '').toString(),
                'content': (item['content'] ?? '').toString(),
              }));
        if (_recoveryAction == _ChatRecoveryAction.history) {
          _chatError = null;
          _recoveryAction = null;
          _status = 'Ready';
        }
      });
    } catch (error) {
      if (!mounted ||
          generation != _sessionGeneration ||
          sessionId != _sessionId) {
        return;
      }
      setState(() {
        _status = 'History unavailable';
        _chatError = 'Chat history could not load. Your session is still active. Retry to load it again. Details: $error';
        _recoveryAction = _ChatRecoveryAction.history;
      });
    }
  }

  Future<void> _refreshHistory() async {
    final sessionId = _sessionId;
    if (sessionId == null || _sending) return;
    await _loadHistory(
      generation: _sessionGeneration,
      sessionId: sessionId,
    );
  }

  void _retryRecovery() {
    switch (_recoveryAction) {
      case _ChatRecoveryAction.session:
        _newSession();
        break;
      case _ChatRecoveryAction.command:
        _send();
        break;
      case _ChatRecoveryAction.history:
        _refreshHistory();
        break;
      case _ChatRecoveryAction.taskStatus:
        final sessionId = _sessionId;
        if (sessionId != null && _taskId != null) {
          _startPolling(
            generation: _sessionGeneration,
            sessionId: sessionId,
          );
        }
        break;
      case null:
        return;
    }
  }

  Future<void> _send() async {
    final text = _input.text.trim();
    if (text.isEmpty || _sending) return;
    if (_sessionId == null) await _newSession();
    final sessionId = _sessionId;
    if (sessionId == null || _sending) return;
    final generation = _sessionGeneration;

    setState(() {
      _sending = true;
      _status = 'Queued';
      _chatError = null;
      _recoveryAction = null;
      _messages.add({'role': 'user', 'content': text});
      _input.clear();
    });

    try {
      final response = await widget.api.submitCommand(text, sessionId: sessionId);
      if (!mounted || generation != _sessionGeneration) return;
      final task = response['task'];
      _taskId = task is Map
          ? (task['id'] ?? task['task_id'])?.toString()
          : response['task_id']?.toString();
      if (_taskId == null || _taskId!.isEmpty) {
        throw Exception('SAGE did not return a task id.');
      }
      _startPolling(generation: generation, sessionId: sessionId);
    } catch (error) {
      if (!mounted || generation != _sessionGeneration) return;
      setState(() {
        if (_messages.isNotEmpty &&
            _messages.last['role'] == 'user' &&
            _messages.last['content'] == text) {
          _messages.removeLast();
        }
        _input.value = TextEditingValue(
          text: text,
          selection: TextSelection.collapsed(offset: text.length),
        );
        _sending = false;
        _status = 'Could not queue command';
        _chatError = 'Command was not queued. Your message has been restored so you can retry. Details: $error';
        _recoveryAction = _ChatRecoveryAction.command;
      });
    }
  }

  void _startPolling({
    required int generation,
    required String sessionId,
  }) {
    _poller?.cancel();
    _pollFailures = 0;
    if (mounted) {
      setState(() {
        _sending = true;
        _status = 'Waiting for task…';
        _chatError = null;
        _recoveryAction = null;
      });
    }
    _poller = Timer.periodic(
      const Duration(seconds: 2),
      (_) => _pollTask(generation: generation, sessionId: sessionId),
    );
    _pollTask(generation: generation, sessionId: sessionId);
  }

  Future<void> _pollTask({
    required int generation,
    required String sessionId,
  }) async {
    if (generation != _sessionGeneration ||
        sessionId != _sessionId ||
        _pollInFlight) {
      return;
    }
    final id = _taskId;
    if (id == null) return;
    _pollInFlight = true;
    try {
      final task = await widget.api.task(id);
      if (!mounted ||
          generation != _sessionGeneration ||
          sessionId != _sessionId) {
        return;
      }
      final status = (task['status'] ?? 'unknown').toString().toLowerCase();
      final result = task['result']?.toString();
      final error = task['error']?.toString();
      _pollFailures = 0;
      setState(() {
        _chatError = null;
        _recoveryAction = null;
        _status = status.toUpperCase();
        if (status == 'completed' && result != null && result.isNotEmpty) {
          _messages.add({'role': 'assistant', 'content': result});
        } else if (status == 'failed' && error != null && error.isNotEmpty) {
          _messages.add({'role': 'system', 'content': error});
        }
        _sending = !{'completed', 'failed', 'cancelled', 'canceled'}.contains(status);
      });
      if (!_sending) {
        _poller?.cancel();
        await _loadHistory(generation: generation, sessionId: sessionId);
      }
    } catch (error) {
      if (!mounted ||
          generation != _sessionGeneration ||
          sessionId != _sessionId) {
        return;
      }
      _pollFailures++;
      if (_pollFailures >= _maxPollFailures) {
        _poller?.cancel();
        setState(() {
          _status = 'Status check paused';
          _chatError = 'SAGE has not confirmed the task status after $_maxPollFailures attempts. The task may still be running; retry the status check before sending another command. Details: $error';
          _recoveryAction = _ChatRecoveryAction.taskStatus;
        });
      } else {
        setState(() {
          _status = 'Connection issue • retry $_pollFailures/$_maxPollFailures';
        });
      }
    } finally {
      _pollInFlight = false;
    }
  }

  @override
  void dispose() {
    _poller?.cancel();
    _input.dispose();
    _scroll.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: SageTheme.voidBlack,
      appBar: AppBar(
        title: const Text('SAGE Chat'),
        backgroundColor: Colors.transparent,
        actions: [
          IconButton(
            tooltip: 'Refresh chat history',
            onPressed: _sessionId == null || _sending ? null : _refreshHistory,
            icon: const Icon(Icons.refresh),
          ),
          IconButton(
            tooltip: 'New chat session',
            onPressed: _newSession,
            icon: const Icon(Icons.add_comment_outlined),
          ),
        ],
      ),
      body: Column(
        children: [
          if (_chatError != null)
            Padding(
              padding: const EdgeInsets.fromLTRB(12, 8, 12, 0),
              child: Card(
                child: Padding(
                  padding: const EdgeInsets.all(12),
                  child: Row(
                    children: [
                      const Icon(Icons.error_outline, color: SageTheme.failure),
                      const SizedBox(width: 10),
                      Expanded(
                        child: Text(
                          _chatError!,
                          style: const TextStyle(color: SageTheme.textPrimary),
                        ),
                      ),
                      const SizedBox(width: 8),
                      TextButton(
                        onPressed: _recoveryAction == null ? null : _retryRecovery,
                        child: const Text('Retry'),
                      ),
                    ],
                  ),
                ),
              ),
            ),
          Expanded(
            child: _messages.isEmpty
                ? const Center(
                    child: Text(
                      'Talk to SAGE. Every command enters the durable execution pipeline.',
                      textAlign: TextAlign.center,
                      style: TextStyle(color: SageTheme.textSecondary),
                    ),
                  )
                : ListView.builder(
                    controller: _scroll,
                    padding: const EdgeInsets.all(16),
                    itemCount: _messages.length,
                    itemBuilder: (context, index) {
                      final item = _messages[index];
                      final role = item['role'] ?? 'system';
                      final isUser = role == 'user';
                      return Align(
                        alignment: isUser ? Alignment.centerRight : Alignment.centerLeft,
                        child: Container(
                          constraints: const BoxConstraints(maxWidth: 620),
                          margin: const EdgeInsets.only(bottom: 10),
                          padding: const EdgeInsets.all(14),
                          decoration: BoxDecoration(
                            color: isUser ? SageTheme.blue.withValues(alpha: .24) : SageTheme.cyan.withValues(alpha: .08),
                            borderRadius: BorderRadius.circular(16),
                            border: Border.all(color: SageTheme.cyan.withValues(alpha: .12)),
                          ),
                          child: SelectableText(
                            item['content'] ?? '',
                            style: const TextStyle(color: SageTheme.textPrimary, height: 1.45),
                          ),
                        ),
                      );
                    },
                  ),
          ),
          Padding(
            padding: const EdgeInsets.fromLTRB(16, 8, 16, 18),
            child: Row(
              children: [
                Expanded(
                  child: TextField(
                    controller: _input,
                    minLines: 1,
                    maxLines: 5,
                    enabled: !_sending,
                    onSubmitted: (_) => _send(),
                    decoration: InputDecoration(
                      hintText: 'Ask SAGE to do something…',
                      suffixText: _status,
                    ),
                  ),
                ),
                const SizedBox(width: 10),
                IconButton.filled(
                  onPressed: _sending ? null : _send,
                  icon: const Icon(Icons.arrow_upward),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}

class AppsScreen extends StatelessWidget { const AppsScreen({super.key}); @override Widget build(BuildContext c)=>const FeatureWorkspace(title:'Apps',subtitle:'Connected tools and future integrations in one control surface.',icon:Icons.apps,actions:['Browse connected apps','Connect an app','Manage permissions']);}
class EarningsScreen extends StatelessWidget { const EarningsScreen({super.key}); @override Widget build(BuildContext c)=>const FeatureWorkspace(title:'Earnings',subtitle:'Track completed work, payouts and creator income.',icon:Icons.trending_up,actions:['View earnings','View pending payouts','Open earnings history']);}
class CommunityScreen extends StatelessWidget { const CommunityScreen({super.key}); @override Widget build(BuildContext c)=>const FeatureWorkspace(title:'Community',subtitle:'Private-first collaboration and future SAGE community spaces.',icon:Icons.groups_outlined,actions:['Open community','Create a post','View activity']);}
class FileManagerScreen extends StatelessWidget { const FileManagerScreen({super.key}); @override Widget build(BuildContext c)=>const FeatureWorkspace(title:'File Manager',subtitle:'Organize SAGE artifacts, project files and exports.',icon:Icons.folder_copy_outlined,actions:['Browse files','Recent artifacts','Export workspace']);}
class AiStudioScreen extends StatelessWidget { const AiStudioScreen({super.key}); @override Widget build(BuildContext c)=>const FeatureWorkspace(title:'AI Studio',subtitle:'Build reusable prompts, agents and execution recipes.',icon:Icons.auto_awesome,actions:['Create a workflow','Prompt library','Agent templates']);}
class SparkWalletScreen extends StatelessWidget { const SparkWalletScreen({super.key}); @override Widget build(BuildContext c)=>const FeatureWorkspace(title:'Spark Wallet',subtitle:'SAGE Spark balance and internal work-credit controls.',icon:Icons.account_balance_wallet_outlined,actions:['View Spark balance','Open Spark history','Reserve Spark']);}
class PaymentScreen extends StatelessWidget { const PaymentScreen({super.key}); @override Widget build(BuildContext c)=>const FeatureWorkspace(title:'Payments',subtitle:'Payment setup and provider readiness.',icon:Icons.payments_outlined,actions:['Payment methods','Provider status','Payment preferences']);}
class TransactionsScreen extends StatelessWidget { const TransactionsScreen({super.key}); @override Widget build(BuildContext c)=>const FeatureWorkspace(title:'Transactions',subtitle:'Unified record of work, Spark and payment movements.',icon:Icons.receipt_long_outlined,actions:['View transactions','Filter records','Export records']);}
class ProfileScreen extends StatelessWidget { const ProfileScreen({super.key}); @override Widget build(BuildContext c)=>const FeatureWorkspace(title:'Profile',subtitle:'Identity, capabilities and personal SAGE preferences.',icon:Icons.person_outline,actions:['Edit profile','Capabilities','Privacy controls']);}
class SettingsScreen extends StatelessWidget { const SettingsScreen({super.key}); @override Widget build(BuildContext c)=>const FeatureWorkspace(title:'Settings',subtitle:'Themes, behavior, language and security controls.',icon:Icons.settings_outlined,actions:['Appearance','Language','Security']);}
class NotificationsScreen extends StatelessWidget { const NotificationsScreen({super.key}); @override Widget build(BuildContext c)=>const FeatureWorkspace(title:'Notifications',subtitle:'Activity, alerts and SAGE execution updates.',icon:Icons.notifications_none,actions:['View notifications','Mark all read','Notification preferences']);}

class KycScreen extends StatelessWidget { const KycScreen({super.key}); @override Widget build(BuildContext c)=>const FeatureWorkspace(title:'Identity Verification',subtitle:'KYC readiness with provider-backed verification when configured.',icon:Icons.verified_user_outlined,actions:['Start verification','Check verification status','Review requirements']);}
class FirstRunScreen extends StatelessWidget { const FirstRunScreen({super.key}); @override Widget build(BuildContext c)=>const FeatureWorkspace(title:'First Run',subtitle:'Finish setup and choose how SAGE should work with you.',icon:Icons.flag_outlined,actions:['Complete setup','Choose capabilities','Finish workspace setup']);}
