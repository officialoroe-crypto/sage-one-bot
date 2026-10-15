import 'dart:convert';
import 'package:flutter/material.dart';
import '../core/sage_api.dart';
import '../theme/sage_theme.dart';

class SalesScreen extends StatefulWidget {
  const SalesScreen({required this.api, super.key});
  final SageApi api;
  @override State<SalesScreen> createState() => _SalesScreenState();
}
class _SalesScreenState extends State<SalesScreen> {
  List leads = []; Object? error; bool loading = true; String filter = 'all';
  Future<void> load() async {
    setState(() => loading = true);
    try {
      final value = await widget.api.salesLeads(status: filter == 'all' ? null : filter);
      if (mounted) setState(() { leads = value; error = null; });
    } catch (e) { if (mounted) setState(() => error = e); }
    finally { if (mounted) setState(() => loading = false); }
  }
  Future<void> openLead(Map<String, dynamic> lead) async {
    await Navigator.of(context).push(MaterialPageRoute(builder: (_) => SalesLeadScreen(api: widget.api, lead: lead)));
    await load();
  }
  @override void initState() { super.initState(); load(); }
  @override Widget build(BuildContext context) => Scaffold(
    backgroundColor: SageTheme.voidBlack,
    appBar: AppBar(title: const Text('Sales'), backgroundColor: Colors.transparent,
      actions: [IconButton(onPressed: loading ? null : load, icon: const Icon(Icons.refresh))]),
    body: RefreshIndicator(onRefresh: load, child: ListView(padding: const EdgeInsets.all(16), children: [
      const Text('Lead pipeline', style: TextStyle(fontSize: 28, fontWeight: FontWeight.w900)),
      const SizedBox(height: 6),
      const Text('Audit → lead → approved outreach → customer. SAGE never sends outreach automatically.',
        style: TextStyle(color: SageTheme.textSecondary)),
      const SizedBox(height: 16),
      Wrap(spacing: 8, children: [
        for (final item in const {'all': 'All', 'outreach_pending': 'Needs approval', 'outreach_approved': 'Approved', 'customer': 'Customers'}.entries)
          ChoiceChip(label: Text(item.value), selected: filter == item.key,
            onSelected: (_) { setState(() => filter = item.key); load(); }),
      ]),
      const SizedBox(height: 16),
      if (error != null) Card(child: ListTile(
        leading: const Icon(Icons.error_outline), title: const Text('Sales data unavailable'),
        subtitle: Text(error.toString()), trailing: TextButton(onPressed: load, child: const Text('Retry')))),
      if (loading && leads.isEmpty) const Padding(padding: EdgeInsets.all(40), child: Center(child: CircularProgressIndicator())),
      if (!loading && leads.isEmpty && error == null) const Card(child: Padding(
        padding: EdgeInsets.all(28), child: Text('No leads yet. Run a Sales Audit from Chat or the API to create the first lead.'))),
      ...leads.map((raw) => _leadCard(Map<String, dynamic>.from(raw as Map))),
    ])),
  );
  Widget _leadCard(Map<String, dynamic> lead) {
    final score = lead['score'] ?? 0, tier = lead['tier']?.toString() ?? 'unknown', status = lead['status']?.toString() ?? 'unknown';
    return Card(child: ListTile(
      leading: CircleAvatar(child: Text(score.toString())),
      title: Text(lead['business_name']?.toString() ?? 'Unnamed business'),
      subtitle: Text('$tier • $status\n${lead['website'] ?? 'No website supplied'}'),
      isThreeLine: true, trailing: const Icon(Icons.chevron_right), onTap: () => openLead(lead)));
  }
}

class SalesLeadScreen extends StatefulWidget {
  const SalesLeadScreen({required this.api, required this.lead, super.key});
  final SageApi api; final Map<String, dynamic> lead;
  @override State<SalesLeadScreen> createState() => _SalesLeadScreenState();
}
class _SalesLeadScreenState extends State<SalesLeadScreen> {
  late Map<String, dynamic> lead; List history = []; Object? error; bool busy = false;
  final TextEditingController _followUpController = TextEditingController();
  Future<void> load() async {
    try {
      final current = await widget.api.salesLead(lead['id'].toString());
      final events = await widget.api.salesLeadHistory(lead['id'].toString());
      if (mounted) setState(() { lead = Map<String, dynamic>.from(current['lead'] as Map); history = events; error = null; });
    } catch (e) { if (mounted) setState(() => error = e); }
  }
  Future<void> approve() async {
    setState(() => busy = true);
    try { await widget.api.approveSalesOutreach(lead['id'].toString()); await load(); }
    catch (e) { _message('Approval failed: $e'); }
    finally { if (mounted) setState(() => busy = false); }
  }
  Future<void> convert() async {
    setState(() => busy = true);
    try { await widget.api.convertSalesCustomer(lead['id'].toString()); await load(); }
    catch (e) { _message('Conversion failed: $e'); }
    finally { if (mounted) setState(() => busy = false); }
  }
  Future<void> addFollowUp() async {
    _followUpController.clear();
    var submitting = false;
    String? errorMessage;
    final ok = await showDialog<bool>(
      context: context,
      builder: (dialogContext) => StatefulBuilder(
        builder: (dialogContext, setDialogState) => AlertDialog(
          title: const Text('Record follow-up'),
          content: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              TextField(
                controller: _followUpController,
                maxLines: 4,
                autofocus: true,
                onChanged: (_) => setDialogState(() => errorMessage = null),
                decoration: const InputDecoration(
                  labelText: 'What happened / next step',
                ),
              ),
              if (errorMessage != null) ...[
                const SizedBox(height: 8),
                Text(errorMessage!, style: const TextStyle(color: SageTheme.failure)),
              ],
            ],
          ),
          actions: [
            TextButton(
              onPressed: submitting ? null : () => Navigator.pop(dialogContext, false),
              child: const Text('Cancel'),
            ),
            FilledButton(
              onPressed: _followUpController.text.trim().isEmpty || submitting
                  ? null
                  : () async {
                      final note = _followUpController.text.trim();
                      setDialogState(() {
                        submitting = true;
                        errorMessage = null;
                      });
                      try {
                        await widget.api.addSalesFollowUp(lead['id'].toString(), note);
                        if (dialogContext.mounted) Navigator.pop(dialogContext, true);
                      } catch (error) {
                        if (dialogContext.mounted) {
                          setDialogState(() {
                            submitting = false;
                            errorMessage = 'Follow-up failed: $error';
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
                  : const Text('Save'),
            ),
          ],
        ),
      ),
    );
    if (ok == true && mounted) await load();
  }
  void _message(String value) { if (mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(value))); }
  @override void initState() { super.initState(); lead = Map<String, dynamic>.from(widget.lead); load(); }
  @override void dispose() { _followUpController.dispose(); super.dispose(); }
  @override Widget build(BuildContext context) {
    final outreach = _jsonMap(lead['outreach_json']); final audit = _jsonMap(lead['audit_json']);
    final gaps = audit['gaps'] is List ? (audit['gaps'] as List).map((e) => e.toString()).toList() : <String>[];
    return Scaffold(backgroundColor: SageTheme.voidBlack, appBar: AppBar(title: const Text('Lead'), backgroundColor: Colors.transparent),
      body: RefreshIndicator(onRefresh: load, child: ListView(padding: const EdgeInsets.all(16), children: [
        Text(lead['business_name']?.toString() ?? 'Lead', style: const TextStyle(fontSize: 30, fontWeight: FontWeight.w900)),
        Text('Score ${lead['score'] ?? 0} • ${lead['tier'] ?? 'unknown'} • ${lead['status'] ?? 'unknown'}'),
        const SizedBox(height: 18),
        if (lead['website'] != null) ListTile(leading: const Icon(Icons.language), title: Text(lead['website'].toString())),
        if (lead['instagram'] != null) ListTile(leading: const Icon(Icons.camera_alt_outlined), title: Text(lead['instagram'].toString())),
        Card(child: Padding(padding: const EdgeInsets.all(16), child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          const Text('Audit gaps', style: TextStyle(fontSize: 18, fontWeight: FontWeight.w800)),
          const SizedBox(height: 8), Text(gaps.isEmpty ? 'No gaps recorded.' : gaps.join(' • ')),
        ]))),
        if (outreach['draft'] != null) Card(child: Padding(padding: const EdgeInsets.all(16), child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          const Text('Outreach draft', style: TextStyle(fontSize: 18, fontWeight: FontWeight.w800)),
          const SizedBox(height: 8), Text(outreach['draft'].toString()),
        ]))),
        const SizedBox(height: 8),
        Wrap(spacing: 8, runSpacing: 8, children: [
          if (lead['status'] == 'outreach_pending') FilledButton.icon(onPressed: busy ? null : approve, icon: const Icon(Icons.check), label: const Text('Approve outreach')),
          if (lead['status'] == 'outreach_approved') FilledButton.icon(onPressed: busy ? null : convert, icon: const Icon(Icons.handshake_outlined), label: const Text('Convert customer')),
          if (lead['status'] != 'customer') OutlinedButton.icon(onPressed: busy ? null : addFollowUp, icon: const Icon(Icons.add_comment_outlined), label: const Text('Record follow-up')),
        ]),
        const SizedBox(height: 22), const Text('Activity history', style: TextStyle(fontSize: 20, fontWeight: FontWeight.w800)),
        if (error != null) Text(error.toString()),
        ...history.map((raw) { final item = Map<String, dynamic>.from(raw as Map); return ListTile(
          leading: const Icon(Icons.timeline), title: Text(item['event_type']?.toString() ?? 'activity'),
          subtitle: Text(item['created_at']?.toString() ?? ''), trailing: Text(item['status']?.toString() ?? '')); }),
      ])));
  }
  Map<String, dynamic> _jsonMap(dynamic value) {
    if (value is Map) return Map<String, dynamic>.from(value);
    if (value is String) {
      try {
        final decoded = jsonDecode(value);
        if (decoded is Map) return Map<String, dynamic>.from(decoded);
      } catch (_) {}
    }
    return <String, dynamic>{};
  }
}
