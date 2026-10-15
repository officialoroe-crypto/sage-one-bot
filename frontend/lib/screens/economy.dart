import 'package:flutter/material.dart';

import '../core/sage_api.dart';

class EconomyScreen extends StatefulWidget {
  const EconomyScreen({required this.api, super.key});

  final SageApi api;

  @override
  State<EconomyScreen> createState() => _EconomyScreenState();
}

class _EconomyScreenState extends State<EconomyScreen> {
  Map<String, dynamic>? _data;
  List<dynamic> _costs = const [];
  bool _loading = true;
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
      final results = await Future.wait<dynamic>([
        widget.api.economyMe(),
        widget.api.premiumWorkCosts(),
      ]);
      if (!mounted) return;
      setState(() {
        _data = Map<String, dynamic>.from(results[0] as Map);
        _costs = (results[1] is Iterable ? results[1] as Iterable : const <dynamic>[])
            .whereType<Map>()
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
      return const Scaffold(body: Center(child: CircularProgressIndicator()));
    }
    if (_error != null) {
      return Scaffold(
        appBar: AppBar(title: const Text('SAGE Spark')),
        body: _ErrorState(message: _error!, onRetry: _load),
      );
    }

    final sparkValue = _data?['spark'];
    final evolutionValue = _data?['evolution'];
    final ledgerValue = _data?['ledger'];
    final spark = sparkValue is Map ? Map<String, dynamic>.from(sparkValue) : <String, dynamic>{};
    final evolution = evolutionValue is Map ? Map<String, dynamic>.from(evolutionValue) : <String, dynamic>{};
    final ledger = ledgerValue is List
        ? ledgerValue.whereType<Map>().map((item) => Map<String, dynamic>.from(item)).toList(growable: false)
        : const <Map<String, dynamic>>[];

    return Scaffold(
      appBar: AppBar(
        title: const Text('SAGE Spark'),
        actions: [IconButton(onPressed: _load, icon: const Icon(Icons.refresh))],
      ),
      body: RefreshIndicator(
        onRefresh: _load,
        child: ListView(
          padding: const EdgeInsets.fromLTRB(20, 10, 20, 32),
          children: [
            _SparkCard(spark: spark),
            const SizedBox(height: 14),
            _EvolutionCard(evolution: evolution),
            const SizedBox(height: 24),
            const _SectionTitle('Premium work • Evolution protected'),
            const SizedBox(height: 10),
            const Text(
              'SAGE Spark is the platform currency: 1 Spark = NPR 1. Spending Spark never removes verified Evolution achievement.',
              style: TextStyle(color: Colors.white54, height: 1.4, fontSize: 12),
            ),
            const SizedBox(height: 12),
            ..._costs.map((item) => _CostTile(item: Map<String, dynamic>.from(item as Map))),
            const SizedBox(height: 24),
            const _SectionTitle('Spark ledger • Economic history only'),
            const SizedBox(height: 10),
            if (ledger.isEmpty)
              const Text('No Spark activity yet.', style: TextStyle(color: Colors.white54))
            else
              ...ledger.map((entry) => _LedgerTile(entry: Map<String, dynamic>.from(entry as Map))),
          ],
        ),
      ),
    );
  }
}

class _SparkCard extends StatelessWidget {
  const _SparkCard({required this.spark});
  final Map<String, dynamic> spark;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(22),
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(28),
        border: Border.all(color: Colors.white10),
        gradient: const LinearGradient(
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
          colors: [Color(0xFF18152A), Color(0xFF0D1117)],
        ),
      ),
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Row(children: [
          Container(
            width: 44,
            height: 44,
            decoration: BoxDecoration(
              shape: BoxShape.circle,
              border: Border.all(color: const Color(0xFFB99CFF).withValues(alpha: .35)),
            ),
            child: const Icon(Icons.auto_awesome, color: Color(0xFFB99CFF)),
          ),
          const SizedBox(width: 12),
          const Expanded(child: Text('SAGE Spark', style: TextStyle(fontSize: 20, fontWeight: FontWeight.w800))),
          Text('${spark['balance'] ?? 0}', style: const TextStyle(fontSize: 28, fontWeight: FontWeight.w800)),
        ]),
        const SizedBox(height: 6),
        Text('1 Spark = NPR 1 • worth NPR ${spark['npr_value'] ?? spark['balance'] ?? 0}', style: const TextStyle(color: Colors.white54, fontSize: 12)),
        const SizedBox(height: 18),
        Row(children: [
          _Metric(label: 'Earned', value: '${spark['lifetime_earned'] ?? 0}'),
          _Metric(label: 'Spent', value: '${spark['lifetime_spent'] ?? 0}'),
        ]),
      ]),
    );
  }
}

class _EvolutionCard extends StatelessWidget {
  const _EvolutionCard({required this.evolution});
  final Map<String, dynamic> evolution;

  @override
  Widget build(BuildContext context) {
    final progress = Map<String, dynamic>.from(evolution['progress'] ?? {});
    final ratioValue = progress['ratio'];
    final ratio = ratioValue is num ? ratioValue.toDouble().clamp(0.0, 1.0) : 0.0;
    final current = evolution['tier'] ?? 'Bronze';
    final next = progress['next_tier'] ?? 'MAX';

    return Card(
      child: Padding(
        padding: const EdgeInsets.all(20),
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Row(children: [
            const Icon(Icons.auto_awesome, color: Color(0xFF8ED8FF)),
            const SizedBox(width: 10),
            const Expanded(child: Text('Evolution', style: TextStyle(fontSize: 18, fontWeight: FontWeight.w800))),
            Text(current.toString(), style: const TextStyle(color: Color(0xFFB99CFF), fontWeight: FontWeight.w700)),
          ]),
          const SizedBox(height: 12),
          Text('${evolution['lifetime_achievement'] ?? 0} lifetime achievement', style: const TextStyle(color: Colors.white60)),
          const SizedBox(height: 14),
          ClipRRect(
            borderRadius: BorderRadius.circular(8),
            child: LinearProgressIndicator(value: ratio, minHeight: 7),
          ),
          const SizedBox(height: 8),
          Row(children: [
            Text('${progress['current_threshold'] ?? 0}', style: const TextStyle(color: Colors.white38, fontSize: 11)),
            const Spacer(),
            Text(next.toString(), style: const TextStyle(color: Colors.white54, fontSize: 11)),
            const SizedBox(width: 6),
            Text('${progress['next_threshold'] ?? 'MAX'}', style: const TextStyle(color: Colors.white38, fontSize: 11)),
          ]),
        ]),
      ),
    );
  }
}

class _Metric extends StatelessWidget {
  const _Metric({required this.label, required this.value});
  final String label;
  final String value;

  @override
  Widget build(BuildContext context) => Expanded(
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Text(value, style: const TextStyle(fontWeight: FontWeight.w700, fontSize: 15)),
          const SizedBox(height: 3),
          Text(label, style: const TextStyle(color: Colors.white38, fontSize: 11)),
        ]),
      );
}

class _CostTile extends StatelessWidget {
  const _CostTile({required this.item});
  final Map<String, dynamic> item;

  @override
  Widget build(BuildContext context) => Card(
        child: ListTile(
          leading: const Icon(Icons.bolt_outlined, color: Color(0xFFB99CFF)),
          title: Text(item['name']?.toString() ?? 'Premium work'),
          subtitle: Text(item['description']?.toString() ?? '', style: const TextStyle(color: Colors.white54)),
          trailing: Text('${item['spark_cost'] ?? 0} ✦', style: const TextStyle(fontWeight: FontWeight.w800)),
        ),
      );
}

class _LedgerTile extends StatelessWidget {
  const _LedgerTile({required this.entry});
  final Map<String, dynamic> entry;

  @override
  Widget build(BuildContext context) {
    final delta = (entry['delta'] as num?)?.toInt() ?? 0;
    return ListTile(
      contentPadding: const EdgeInsets.symmetric(horizontal: 4),
      leading: Icon(delta >= 0 ? Icons.south_west : Icons.north_east, size: 19),
      title: Text(entry['reason']?.toString() ?? 'Spark activity'),
      subtitle: Text(entry['created_at']?.toString() ?? '', style: const TextStyle(color: Colors.white30, fontSize: 10)),
      trailing: Text(
        '${delta >= 0 ? '+' : ''}$delta',
        style: TextStyle(fontWeight: FontWeight.w800, color: delta >= 0 ? const Color(0xFFE7C76A) : Colors.white70),
      ),
    );
  }
}

class _SectionTitle extends StatelessWidget {
  const _SectionTitle(this.text);
  final String text;
  @override
  Widget build(BuildContext context) => Text(text, style: const TextStyle(fontSize: 16, fontWeight: FontWeight.w800, letterSpacing: .2));
}

class _ErrorState extends StatelessWidget {
  const _ErrorState({required this.message, required this.onRetry});
  final String message;
  final VoidCallback onRetry;
  @override
  Widget build(BuildContext context) => Center(
        child: Padding(
          padding: const EdgeInsets.all(28),
          child: Column(mainAxisSize: MainAxisSize.min, children: [
            const Icon(Icons.cloud_off, size: 34),
            const SizedBox(height: 12),
            const Text('SAGE Spark is unavailable right now', style: TextStyle(fontWeight: FontWeight.w700)),
            const SizedBox(height: 8),
            Text(message, textAlign: TextAlign.center, style: const TextStyle(color: Colors.white54, fontSize: 11)),
            const SizedBox(height: 16),
            OutlinedButton(onPressed: onRetry, child: const Text('Retry')),
          ]),
        ),
      );
}
