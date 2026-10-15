import 'package:flutter/material.dart';

import '../core/sage_api.dart';
import '../evolution/evolution_transition.dart';
import '../evolution/evolution_visual.dart';
import '../theme/sage_theme.dart';
import 'economy.dart';

class EvolutionScreen extends StatefulWidget {
  const EvolutionScreen({required this.api, super.key});
  final SageApi api;

  @override
  State<EvolutionScreen> createState() => _EvolutionScreenState();
}

class _EvolutionScreenState extends State<EvolutionScreen> {
  Map<String, dynamic>? _snapshot;
  List<Map<String, dynamic>> _tiers = const [];
  bool _loading = true;
  String? _error;
  EvolutionVisual? _transitionFrom;

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
      final results = await Future.wait<dynamic>([
        widget.api.economyMe(),
        widget.api.evolutionTiers(),
      ]);
      if (!mounted) return;
      final nextSnapshot = Map<String, dynamic>.from(results[0] as Map);
      final nextEvolution =
          Map<String, dynamic>.from(nextSnapshot['evolution'] ?? {});
      final nextTier = nextEvolution['tier']?.toString();
      final previousEvolution =
          Map<String, dynamic>.from(_snapshot?['evolution'] ?? {});
      final previousTier = previousEvolution['tier']?.toString();

      setState(() {
        if (previousTier != null &&
            nextTier != null &&
            previousTier != nextTier) {
          _transitionFrom = evolutionVisualFor(
            previousTier,
            intensity: EvolutionIntensity.high,
          );
        }
        _snapshot = nextSnapshot;
        _tiers = (results[1] is Iterable ? results[1] as Iterable : const <dynamic>[])
            .whereType<Map>()
            .where((item) => item['tier'] != null && item['threshold'] is num)
            .map((item) => Map<String, dynamic>.from(item))
            .toList(growable: false);
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

  @override
  Widget build(BuildContext context) {
    if (_loading) {
      return const Scaffold(
        body: Center(child: CircularProgressIndicator(color: SageTheme.cyan)),
      );
    }
    if (_error != null) {
      return Scaffold(
        appBar: AppBar(title: const Text('Evolution')),
        body: _ErrorState(message: _error!, onRetry: _load),
      );
    }

    final evolution = Map<String, dynamic>.from(_snapshot?['evolution'] ?? {});
    final progress = Map<String, dynamic>.from(evolution['progress'] ?? {});
    final achievement = (evolution['lifetime_achievement'] as num?)?.toInt() ?? 0;
    final currentTier = evolution['tier']?.toString() ?? 'Bronze';
    final nextTier = progress['next_tier']?.toString();
    final nextThreshold = (progress['next_threshold'] as num?)?.toInt();
    final currentThreshold = (progress['current_threshold'] as num?)?.toInt() ?? 0;
    final ratio = ((progress['ratio'] as num?)?.toDouble() ?? 0).clamp(0.0, 1.0).toDouble();
    final visual = evolutionVisualFor(currentTier, intensity: EvolutionIntensity.mid);

    return Scaffold(
      appBar: AppBar(
        title: const Text('Evolution'),
        actions: [
          IconButton(
            tooltip: 'Refresh Evolution',
            onPressed: _load,
            icon: const Icon(Icons.refresh),
          ),
        ],
      ),
      body: Stack(
        children: [
          EvolutionAtmosphere(
            visual: visual,
            child: RefreshIndicator(
              onRefresh: _load,
              color: SageTheme.cyan,
              child: ListView(
                padding: const EdgeInsets.fromLTRB(18, 8, 18, 30),
          children: [
            _CurrentRankCard(
              tier: currentTier,
              achievement: achievement,
              currentThreshold: currentThreshold,
              nextTier: nextTier,
              nextThreshold: nextThreshold,
              ratio: ratio,
              accent: visual.accent,
            ),
            const SizedBox(height: 16),
            OutlinedButton.icon(
              onPressed: () => Navigator.of(context).push(
                MaterialPageRoute(builder: (_) => EconomyScreen(api: widget.api)),
              ),
              icon: const Icon(Icons.account_balance_wallet_outlined),
              label: const Text('Open SAGE Spark wallet'),
            ),
            const SizedBox(height: 24),
            const _SectionHeader(
              title: 'THE EVOLUTION PATH',
              subtitle: '13 ranks • verified achievement progression',
            ),
            const SizedBox(height: 12),
            if (_tiers.isEmpty)
              const Card(
                child: Padding(
                  padding: EdgeInsets.all(18),
                  child: Text('The rank catalog is not available yet. Pull to refresh.'),
                ),
              )
            else
              ..._tiers.map((tier) {
                final name = tier['tier']?.toString() ?? 'Unknown';
                final threshold = (tier['threshold'] as num?)?.toInt() ?? 0;
                final order = (tier['order'] as num?)?.toInt() ?? 0;
                final isCurrent = name == currentTier;
                final isReached = achievement >= threshold;
                return Padding(
                  padding: const EdgeInsets.only(bottom: 9),
                  child: _RankRow(
                    name: name,
                    threshold: threshold,
                    order: order,
                    isCurrent: isCurrent,
                    isReached: isReached,
                    accent: evolutionVisualFor(name).accent,
                  ),
                );
              }),
            const SizedBox(height: 8),
            const Text(
              'Rank names and thresholds are loaded from SAGE Core. Progress is based on verified achievements; this screen does not grant or modify XP.',
              style: TextStyle(color: SageTheme.textSecondary, fontSize: 11, height: 1.45),
            ),
                ],
              ),
            ),
          ),
          if (_transitionFrom != null)
            Positioned.fill(
              child: EvolutionTransition(
                key: ValueKey('${_transitionFrom!.name}->$currentTier'),
                from: _transitionFrom!,
                to: evolutionVisualFor(
                  currentTier,
                  intensity: EvolutionIntensity.low,
                ),
                onCompleted: () {
                  if (mounted) setState(() => _transitionFrom = null);
                },
                child: const SizedBox.expand(),
              ),
            ),
        ],
      ),
    );
  }
}

class _CurrentRankCard extends StatelessWidget {
  const _CurrentRankCard({
    required this.tier,
    required this.achievement,
    required this.currentThreshold,
    required this.nextTier,
    required this.nextThreshold,
    required this.ratio,
    required this.accent,
  });

  final String tier;
  final int achievement;
  final int currentThreshold;
  final String? nextTier;
  final int? nextThreshold;
  final double ratio;
  final Color accent;

  @override
  Widget build(BuildContext context) {
    final isMax = nextTier == null || nextThreshold == null;
    final remaining = isMax ? 0 : (nextThreshold! - achievement).clamp(0, 1 << 31).toInt();
    return Container(
      padding: const EdgeInsets.all(20),
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(26),
        border: Border.all(color: accent.withValues(alpha: .55)),
        gradient: LinearGradient(
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
          colors: [accent.withValues(alpha: .15), SageTheme.surface, const Color(0xFF03070D)],
        ),
        boxShadow: [BoxShadow(color: accent.withValues(alpha: .08), blurRadius: 26, spreadRadius: 1)],
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              const Expanded(
                child: Text(
                  'CURRENT RANK',
                  style: TextStyle(color: SageTheme.textSecondary, fontSize: 10, letterSpacing: 2, fontWeight: FontWeight.w700),
                ),
              ),
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 5),
                decoration: BoxDecoration(
                  color: accent.withValues(alpha: .13),
                  borderRadius: BorderRadius.circular(30),
                  border: Border.all(color: accent.withValues(alpha: .5)),
                ),
                child: Text(
                  isMax ? 'MAX RANK' : 'ACTIVE',
                  style: TextStyle(color: accent, fontSize: 9, letterSpacing: 1.1, fontWeight: FontWeight.w800),
                ),
              ),
            ],
          ),
          const SizedBox(height: 16),
          Center(
            child: Container(
              width: 138,
              height: 138,
              decoration: BoxDecoration(
                shape: BoxShape.circle,
                boxShadow: [BoxShadow(color: accent.withValues(alpha: .18), blurRadius: 30, spreadRadius: 2)],
                gradient: RadialGradient(
                  colors: [accent.withValues(alpha: .24), const Color(0xFF050A13), Colors.black],
                ),
              ),
              child: Stack(
                alignment: Alignment.center,
                children: [
                  Text(
                    'S',
                    style: TextStyle(
                      fontSize: 76,
                      height: 1,
                      fontWeight: FontWeight.w800,
                      color: accent,
                      shadows: [Shadow(color: accent.withValues(alpha: .65), blurRadius: 22)],
                    ),
                  ),
                ],
              ),
            ),
          ),
          const SizedBox(height: 16),
          Center(
            child: Text(
              tier.toUpperCase(),
              textAlign: TextAlign.center,
              style: TextStyle(color: accent, fontSize: 23, letterSpacing: 2.2, fontWeight: FontWeight.w800),
            ),
          ),
          const SizedBox(height: 5),
          Center(
            child: Text(
              '$achievement XP',
              style: const TextStyle(color: SageTheme.textPrimary, fontSize: 18, fontWeight: FontWeight.w700),
            ),
          ),
          const SizedBox(height: 18),
          ClipRRect(
            borderRadius: BorderRadius.circular(20),
            child: LinearProgressIndicator(
              value: isMax ? 1 : ratio,
              minHeight: 9,
              backgroundColor: Colors.white10,
              valueColor: AlwaysStoppedAnimation<Color>(accent),
            ),
          ),
          const SizedBox(height: 9),
          Row(
            children: [
              Expanded(
                child: Text(
                  '$currentThreshold XP',
                  style: const TextStyle(color: SageTheme.textSecondary, fontSize: 10),
                ),
              ),
              Text(
                isMax ? 'MAX RANK' : '$remaining XP to $nextTier',
                textAlign: TextAlign.end,
                style: TextStyle(color: accent, fontSize: 10, fontWeight: FontWeight.w700),
              ),
            ],
          ),
          if (!isMax) ...[
            const SizedBox(height: 5),
            Text(
              'Next milestone: $nextTier at $nextThreshold XP',
              style: const TextStyle(color: SageTheme.textSecondary, fontSize: 11),
            ),
          ],
        ],
      ),
    );
  }
}

class _RankRow extends StatelessWidget {
  const _RankRow({
    required this.name,
    required this.threshold,
    required this.order,
    required this.isCurrent,
    required this.isReached,
    required this.accent,
  });

  final String name;
  final int threshold;
  final int order;
  final bool isCurrent;
  final bool isReached;
  final Color accent;

  @override
  Widget build(BuildContext context) {
    final stateLabel = isCurrent ? 'CURRENT' : isReached ? 'UNLOCKED' : 'LOCKED';
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 13, vertical: 13),
      decoration: BoxDecoration(
        color: isCurrent ? accent.withValues(alpha: .09) : SageTheme.surface,
        borderRadius: BorderRadius.circular(17),
        border: Border.all(
          color: isCurrent ? accent.withValues(alpha: .7) : Colors.white.withValues(alpha: .07),
        ),
      ),
      child: Row(
        children: [
          Container(
            width: 42,
            height: 42,
            decoration: BoxDecoration(
              shape: BoxShape.circle,
              color: accent.withValues(alpha: isReached ? .13 : .05),
              border: Border.all(color: accent.withValues(alpha: isReached ? .65 : .22)),
            ),
            child: Center(
              child: isReached
                  ? Icon(Icons.auto_awesome, color: accent, size: 19)
                  : Icon(Icons.lock_outline, color: accent.withValues(alpha: .65), size: 17),
            ),
          ),
          const SizedBox(width: 12),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  '$order  $name',
                  maxLines: 2,
                  overflow: TextOverflow.ellipsis,
                  style: TextStyle(
                    color: isReached ? SageTheme.textPrimary : SageTheme.textSecondary,
                    fontSize: 13,
                    fontWeight: isCurrent ? FontWeight.w800 : FontWeight.w600,
                  ),
                ),
                const SizedBox(height: 4),
                Text(
                  threshold == 0 ? 'Starting rank' : '$threshold XP required',
                  style: const TextStyle(color: SageTheme.textSecondary, fontSize: 10),
                ),
              ],
            ),
          ),
          const SizedBox(width: 8),
          Text(
            stateLabel,
            style: TextStyle(
              color: isCurrent ? accent : isReached ? SageTheme.success : SageTheme.textSecondary,
              fontSize: 8,
              letterSpacing: .7,
              fontWeight: FontWeight.w800,
            ),
          ),
        ],
      ),
    );
  }
}

class _SectionHeader extends StatelessWidget {
  const _SectionHeader({required this.title, required this.subtitle});
  final String title;
  final String subtitle;

  @override
  Widget build(BuildContext context) => Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(title, style: const TextStyle(color: SageTheme.cyan, fontSize: 11, letterSpacing: 1.8, fontWeight: FontWeight.w800)),
          const SizedBox(height: 4),
          Text(subtitle, style: const TextStyle(color: SageTheme.textSecondary, fontSize: 11)),
        ],
      );
}

class _ErrorState extends StatelessWidget {
  const _ErrorState({required this.message, required this.onRetry});
  final String message;
  final VoidCallback onRetry;

  @override
  Widget build(BuildContext context) => Center(
        child: Padding(
          padding: const EdgeInsets.all(28),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              const Icon(Icons.cloud_off, size: 36, color: SageTheme.textSecondary),
              const SizedBox(height: 12),
              const Text('Evolution is unavailable', style: TextStyle(fontWeight: FontWeight.w700)),
              const SizedBox(height: 8),
              Text(
                message,
                textAlign: TextAlign.center,
                style: const TextStyle(color: SageTheme.textSecondary, fontSize: 11, height: 1.4),
              ),
              const SizedBox(height: 16),
              OutlinedButton.icon(
                onPressed: onRetry,
                icon: const Icon(Icons.refresh),
                label: const Text('Try again'),
              ),
            ],
          ),
        ),
      );
}
