import 'dart:async';

import 'package:flutter/material.dart';

import 'core/sage_api.dart';
import 'screens/agent.dart';
import 'screens/splash.dart';
import 'screens/auth_gate.dart';
import 'screens/command_center.dart';
import 'screens/create.dart';
import 'screens/project_detail.dart';
import 'screens/projects.dart';
import 'screens/research.dart';
import 'screens/tasks.dart';
import 'screens/world_intelligence.dart';
import 'screens/owner_console.dart';
import 'screens/memory.dart';
import 'screens/evolution.dart';
import 'theme/sage_theme.dart';
import 'screens/feature_workspaces.dart';
import 'screens/jobs_marketplace.dart';
import 'screens/learning.dart';
import 'screens/voice_mode.dart';
import 'screens/developer_mode.dart';
import 'screens/sales.dart';
import 'screens/final_surfaces.dart' as final_surfaces;

void main() => runApp(const SageOneApp());

class SageOneApp extends StatelessWidget {
  const SageOneApp({SageApi? api, super.key}) : _api = api;
  final SageApi? _api;

  @override
  Widget build(BuildContext context) {
    return ValueListenableBuilder<ThemeMode>(
      valueListenable: SageTheme.mode,
      builder: (context, mode, _) => MaterialApp(
        title: 'SAGE ONE',
        debugShowCheckedModeBanner: false,
        theme: SageTheme.light(),
        darkTheme: SageTheme.dark(),
        themeMode: mode,
        home: SageSplashScreen(
          child: _api != null
              ? SageOneShell(api: _api)
              : AuthGate(
                  childBuilder: (identity) => const SageOneShell(),
                ),
        ),
      ),
    );
  }
}

class SageOneShell extends StatefulWidget {
  const SageOneShell({SageApi? api, super.key}) : _api = api;
  final SageApi? _api;

  @override
  State<SageOneShell> createState() => _SageOneShellState();
}

class _SageOneShellState extends State<SageOneShell> {
  late final SageApi _api;
  int _index = 0;
  bool _hasUnreadNotifications = false;
  Timer? _notificationPoller;

  @override
  void initState() {
    super.initState();
    _api = widget._api ?? SageApi();
    _restoreThemePreference();
    _refreshNotificationBadge();
    _notificationPoller = Timer.periodic(
      const Duration(seconds: 10),
      (_) => _refreshNotificationBadge(),
    );
  }

  @override
  void dispose() {
    _notificationPoller?.cancel();
    if (widget._api == null) _api.dispose();
    super.dispose();
  }

  Future<void> _restoreThemePreference() async {
    try {
      final response = await _api.profileMe();
      final rawProfile = response['profile'];
      if (rawProfile is! Map) return;
      final rawBasic = rawProfile['basic_info'];
      if (rawBasic is! Map) return;
      final rawSettings = rawBasic['settings'];
      if (rawSettings is! Map) return;
      final savedMode = rawSettings['theme_mode'];
      if (savedMode is String && mounted) {
        SageTheme.mode.value = SageTheme.modeFromPreference(savedMode);
      }
    } catch (_) {
      // Keep the default/current appearance when profile settings are offline.
    }
  }

  Future<void> _refreshNotificationBadge() async {
    try {
      final items = await _api.notifications(unreadOnly: true, limit: 1);
      if (mounted) setState(() => _hasUnreadNotifications = items.isNotEmpty);
    } catch (_) {}
  }

  void _openTasks() {
    setState(() => _index = 2);
  }

  Future<void> _openMore() async {
    final destination = await showModalBottomSheet<int>(
      context: context,
      backgroundColor: Theme.of(context).colorScheme.surface,
      showDragHandle: true,
      builder: (context) => SafeArea(
        child: SingleChildScrollView(
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
            const ListTile(
              title: Text('SAGE ONE', style: TextStyle(
                fontSize: 10, letterSpacing: 2,
                color: SageTheme.violet, fontWeight: FontWeight.w800,
              )),
              subtitle: Text('Workspace destinations'),
            ),
            ListTile(
              leading: const Icon(Icons.folder_open),
              title: const Text('Projects'),
              onTap: () => Navigator.pop(context, 4),
            ),
            ListTile(
              leading: const Icon(Icons.psychology_alt_outlined),
              title: const Text('Memory'),
              onTap: () => Navigator.pop(context, 8),
            ),
            ListTile(
              leading: const Icon(Icons.auto_awesome),
              title: const Text('Evolution'),
              onTap: () => Navigator.pop(context, 9),
            ),
            ListTile(
              leading: const Icon(Icons.smart_toy_outlined),
              title: const Text('Agent'),
              onTap: () => Navigator.pop(context, 5),
            ),
            ListTile(
              leading: const Icon(Icons.public),
              title: const Text('World Intelligence'),
              onTap: () => Navigator.pop(context, 6),
            ),
            ListTile(
              leading: const Icon(Icons.admin_panel_settings_outlined),
              title: const Text('Owner Console'),
              onTap: () => Navigator.pop(context, 7),
            ),
            ListTile(leading: const Icon(Icons.code), title: const Text('Developer Mode'), onTap: () { Navigator.pop(context); Navigator.push(context, MaterialPageRoute(builder: (_) => DeveloperModeScreen(api: _api))); }),
            ListTile(leading: const Icon(Icons.verified_user_outlined), title: const Text('Identity Verification'), onTap: () { Navigator.pop(context); Navigator.push(context, MaterialPageRoute(builder: (_) => const KycScreen())); }),
            ListTile(leading: const Icon(Icons.flag_outlined), title: const Text('First Run'), onTap: () { Navigator.pop(context); Navigator.push(context, MaterialPageRoute(builder: (_) => const FirstRunScreen())); }),
            ListTile(leading: const Icon(Icons.mic), title: const Text('Voice'), onTap: () { Navigator.pop(context); Navigator.push(context, MaterialPageRoute(builder: (_) => SageVoiceScreen(api: _api))); }),
            ListTile(leading: const Icon(Icons.chat_bubble_outline), title: const Text('Chat'), onTap: () { Navigator.pop(context); Navigator.push(context, MaterialPageRoute(builder: (_) => ChatScreen(api: _api))); }),
            ListTile(leading: const Icon(Icons.apps), title: const Text('Apps'), onTap: () { Navigator.pop(context); Navigator.push(context, MaterialPageRoute(builder: (_) => const AppsScreen())); }),
            ListTile(leading: const Icon(Icons.trending_up), title: const Text('Earnings'), onTap: () { Navigator.pop(context); Navigator.push(context, MaterialPageRoute(builder: (_) => const EarningsScreen())); }),
            ListTile(leading: const Icon(Icons.storefront), title: const Text('Marketplace'), onTap: () { Navigator.pop(context); Navigator.push(context, MaterialPageRoute(builder: (_) => MarketplaceScreen(api: _api))); }),
            ListTile(leading: const Icon(Icons.work_outline), title: const Text('Jobs'), onTap: () { Navigator.pop(context); Navigator.push(context, MaterialPageRoute(builder: (_) => JobsScreen(api: _api))); }),
            ListTile(leading: const Icon(Icons.school_outlined), title: const Text('Learning'), onTap: () { Navigator.pop(context); Navigator.push(context, MaterialPageRoute(builder: (_) => LearningScreen(api: _api))); }),
            ListTile(leading: const Icon(Icons.groups_outlined), title: const Text('Community'), onTap: () { Navigator.pop(context); Navigator.push(context, MaterialPageRoute(builder: (_) => const CommunityScreen())); }),
            ListTile(leading: const Icon(Icons.handshake_outlined), title: const Text('Sales'), onTap: () { Navigator.pop(context); Navigator.push(context, MaterialPageRoute(builder: (_) => SalesScreen(api: _api))); }),
            ListTile(leading: const Icon(Icons.folder_copy_outlined), title: const Text('File Manager'), onTap: () { Navigator.pop(context); Navigator.push(context, MaterialPageRoute(builder: (_) => final_surfaces.FileManagerFinalScreen(api: _api))); }),
            ListTile(leading: const Icon(Icons.auto_awesome), title: const Text('AI Studio'), onTap: () { Navigator.pop(context); Navigator.push(context, MaterialPageRoute(builder: (_) => final_surfaces.AiStudioFinalScreen(api: _api))); }),
            ListTile(leading: const Icon(Icons.account_balance_wallet_outlined), title: const Text('Spark Wallet'), onTap: () { Navigator.pop(context); Navigator.push(context, MaterialPageRoute(builder: (_) => final_surfaces.SparkWalletScreen(api: _api))); }),
            ListTile(leading: const Icon(Icons.payments_outlined), title: const Text('Payments'), onTap: () { Navigator.pop(context); Navigator.push(context, MaterialPageRoute(builder: (_) => final_surfaces.PaymentFinalScreen(api: _api))); }),
            ListTile(leading: const Icon(Icons.receipt_long_outlined), title: const Text('Transactions'), onTap: () { Navigator.pop(context); Navigator.push(context, MaterialPageRoute(builder: (_) => final_surfaces.TransactionsScreen(api: _api))); }),
            ListTile(leading: const Icon(Icons.person_outline), title: const Text('Profile'), onTap: () { Navigator.pop(context); Navigator.push(context, MaterialPageRoute(builder: (_) => final_surfaces.ProfileFinalScreen(api: _api))); }),
            ListTile(leading: const Icon(Icons.settings_outlined), title: const Text('Settings'), onTap: () { Navigator.pop(context); Navigator.push(context, MaterialPageRoute(builder: (_) => final_surfaces.SettingsFinalScreen(api: _api))); }),
            ListTile(leading: const Icon(Icons.notifications_none), title: const Text('Notifications'), onTap: () { Navigator.pop(context); Navigator.push(context, MaterialPageRoute(builder: (_) => final_surfaces.NotificationsFinalScreen(api: _api))); }),

            ],
          ),
        ),
      ),
    );
    if (destination != null && mounted) setState(() => _index = destination);
  }

  Future<void> _openProject(Map<String, dynamic> project) async {
    await Navigator.of(context).push(
      MaterialPageRoute(
        builder: (_) => ProjectDetailScreen(api: _api, project: project),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final screens = <Widget>[
      CommandCenter(api: _api, onCreate: () => setState(() => _index = 3)),
      ResearchScreen(api: _api),
      TasksScreen(api: _api),
      CreateScreen(api: _api),
      ProjectsScreen(api: _api, onProjectTap: _openProject),
      AgentScreen(api: _api),
      WorldIntelligenceScreen(api: _api),
      OwnerConsoleScreen(api: _api),
      MemoryScreen(api: _api),
      EvolutionScreen(api: _api),
    ];

    return Scaffold(
      body: IndexedStack(index: _index, children: screens),
      bottomNavigationBar: Stack(
        clipBehavior: Clip.none,
        children: [
          NavigationBar(
            selectedIndex: _index > 3 ? 4 : _index,
            onDestinationSelected: (value) {
              if (value == 0) {
                setState(() => _index = 0);
              } else if (value == 1) {
                setState(() => _index = 1);
              } else if (value == 2) {
                _openTasks();
              } else if (value == 3) {
                setState(() => _index = 3);
              } else {
                _openMore();
              }
            },
            destinations: const [
              NavigationDestination(icon: Icon(Icons.auto_awesome), label: 'Sage'),
              NavigationDestination(icon: Icon(Icons.search), label: 'Research'),
              NavigationDestination(icon: Icon(Icons.task_alt), label: 'Tasks'),
              NavigationDestination(icon: Icon(Icons.auto_awesome_motion), label: 'Create'),
              NavigationDestination(icon: Icon(Icons.more_horiz), label: 'More'),
            ],
          ),
          if (_hasUnreadNotifications)
            Positioned(
              top: 8,
              left: MediaQuery.sizeOf(context).width * 0.5 + 8,
              child: const IgnorePointer(
                child: DecoratedBox(
                  decoration: BoxDecoration(color: Colors.red, shape: BoxShape.circle),
                  child: SizedBox(width: 9, height: 9),
                ),
              ),
            ),
        ],
      ),
    );
  }
}
