import 'package:flutter/material.dart';

import '../core/sage_api.dart';

class OwnerConsoleScreen extends StatefulWidget {
  const OwnerConsoleScreen({required this.api, super.key});
  final SageApi api;
  @override State<OwnerConsoleScreen> createState() => _OwnerConsoleScreenState();
}

class _OwnerConsoleScreenState extends State<OwnerConsoleScreen> with SingleTickerProviderStateMixin {
  bool _loading = true, _busy = false, _simulating = false;
  String? _error;
  Map<String, dynamic> _status = {}, _economy = {};
  List<dynamic> _audit = const [];
  Map<String, dynamic>? _simulation;
  late final AnimationController _evolutionController;
  final _spark = TextEditingController(text: '1000');
  final _achievement = TextEditingController(text: '0');
  final _reason = TextEditingController(text: 'God Mode development test');
  String _tier = 'Bronze';
  String _stage = 'LOW';
  final _tiers = const ['Bronze','Silver','Gold','Platinum','Jade','Ruby','Sapphire','Emerald','Diamond Sovereign','Black Opal Realm','Painite Core','Void Matter','Californium Overlord'];

  @override void initState() {
    super.initState();
    _evolutionController = AnimationController(vsync: this, duration: const Duration(milliseconds: 3200));
    _evolutionController.addStatusListener((status) {
      if (status == AnimationStatus.completed && mounted) setState(() => _simulating = false);
    });
    _load();
  }
  @override void dispose() { _evolutionController.dispose(); _spark.dispose(); _achievement.dispose(); _reason.dispose(); super.dispose(); }

  Future<void> _load() async {
    setState(() { _loading = true; _error = null; });
    try {
      final r = await Future.wait<dynamic>([widget.api.ownerStatus(), widget.api.economyMe(), widget.api.ownerAudit()]);
      if (!mounted) return;
      setState(() {
        _status = Map<String,dynamic>.from(r[0] as Map);
        _economy = Map<String,dynamic>.from(r[1] as Map);
        _audit = List<dynamic>.from(r[2] as List);
        _loading = false;
      });
    } catch (e) { if (mounted) setState(() { _loading=false; _error=e.toString(); }); }
  }

  Future<void> _run(Future<Map<String,dynamic>> Function() action) async {
    setState(() => _busy=true);
    try { await action(); await _load(); } catch(e) { if(mounted) setState(()=>_error=e.toString()); } finally { if(mounted) setState(()=>_busy=false); }
  }

  Future<void> _simulateEvolution() async {
    if (_busy || _simulating) return;
    setState(() { _busy = true; _error = null; });
    try {
      final simulation = await widget.api.ownerSimulateEvolution(_number(_achievement), durationMs: 3200);
      if (!mounted) return;
      final duration = ((simulation['duration_ms'] as num?)?.toInt() ?? 3200);
      _evolutionController.duration = Duration(milliseconds: duration);
      setState(() { _simulation = simulation; _simulating = true; });
      _evolutionController.forward(from: 0);
    } catch (e) {
      if (mounted) setState(() => _error = e.toString());
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  String _tierFor(int achievement) {
    const thresholds = <int, String>{0:'Bronze',1000:'Silver',5000:'Gold',25000:'Platinum',100000:'Jade',250000:'Ruby',500000:'Sapphire',1000000:'Emerald',2500000:'Diamond Sovereign',5000000:'Black Opal Realm',10000000:'Painite Core',25000000:'Void Matter',100000000:'Californium Overlord'};
    var result = 'Bronze';
    for (final entry in thresholds.entries) {
      if (achievement >= entry.key) {
        result = entry.value;
      } else {
        break;
      }
    }
    return result;
  }

  String get _reasonText => _reason.text.trim().isEmpty ? 'Owner development action' : _reason.text.trim();
  int _number(TextEditingController c) => int.tryParse(c.text.trim()) ?? 0;

  @override Widget build(BuildContext context) {
    if (_loading) return const Scaffold(body: Center(child:CircularProgressIndicator()));
    if (_error != null && _status.isEmpty) return Scaffold(appBar:AppBar(title:const Text('Owner Console')),body:_Error(message:_error!,retry:_load));
    final spark=Map<String,dynamic>.from(_economy['spark']??{});
    final evo=Map<String,dynamic>.from(_economy['evolution']??{});
    return Scaffold(
      appBar:AppBar(title:const Text('SAGE Owner Console'),actions:[IconButton(onPressed:_load,icon:const Icon(Icons.refresh))]),
      body:RefreshIndicator(onRefresh:_load,child:ListView(padding:const EdgeInsets.all(20),children:[
        _GodBanner(god:_status['god_mode']==true), const SizedBox(height:14),
        _Card(title:'Internal authority',child:Column(crossAxisAlignment:CrossAxisAlignment.start,children:[
          Text('Scope: ${_status['scope']??'internal_sage_development'}'), const SizedBox(height:6),
          Text('External authority: ${_status['external_authority']==true?'enabled':'false'}',style:const TextStyle(color:Colors.white54)),
          const SizedBox(height:12), const Text('This console controls SAGE development state only.',style:TextStyle(color:Colors.white54))
        ])),
        const SizedBox(height:14),
        _Card(title:'Spark control',child:Column(children:[
          _Value('Current balance','${spark['balance']??0} ✦'), const SizedBox(height:12),
          TextField(controller:_spark,keyboardType:TextInputType.number,decoration:const InputDecoration(labelText:'Set balance',prefixIcon:Icon(Icons.bolt))),
          const SizedBox(height:10), Row(children:[
            Expanded(child:FilledButton(onPressed:_busy?null:()=>_run(()=>widget.api.ownerSetSpark(_number(_spark),_reasonText)),child:const Text('SET SPARK'))),
            const SizedBox(width:8), Expanded(child:OutlinedButton(onPressed:_busy?null:()=>_run(()=>widget.api.ownerResetSpark(_reasonText)),child:const Text('RESET')))
          ])
        ])),
        const SizedBox(height:14),
        _Card(title:'Evolution simulation',child:Column(children:[
          _Value('Persisted','${evo['tier'] ?? 'Bronze'} • ${evo['lifetime_achievement'] ?? 0} achievement'),
          const SizedBox(height:12),
          if (_simulation != null) AnimatedBuilder(animation:_evolutionController,builder:(context,_){
            final from=Map<String,dynamic>.from(_simulation!['from']??{});
            final to=Map<String,dynamic>.from(_simulation!['to']??{});
            final startValue=((from['lifetime_achievement'] as num?)?.toDouble()??0);
            final endValue=((to['lifetime_achievement'] as num?)?.toDouble()??startValue);
            final value=(startValue+(endValue-startValue)*_evolutionController.value).round();
            return AnimatedContainer(duration:const Duration(milliseconds:120),padding:const EdgeInsets.all(18),decoration:BoxDecoration(borderRadius:BorderRadius.circular(18),border:Border.all(color:_simulating?const Color(0xFFE7C76A):Colors.white10),boxShadow:_simulating?const [BoxShadow(blurRadius:24,spreadRadius:1,color:Color(0x55E7C76A))]:const []),child:Column(children:[const Icon(Icons.auto_awesome,size:30),const SizedBox(height:8),Text(_tierFor(value),style:const TextStyle(fontSize:20,fontWeight:FontWeight.w900)),const SizedBox(height:4),Text('$value achievement',style:const TextStyle(color:Colors.white70)),const SizedBox(height:12),LinearProgressIndicator(value:_evolutionController.value,minHeight:7),const SizedBox(height:8),Text(_simulating?'EVOLUTION IN PROGRESS':'SIMULATION COMPLETE • DATABASE UNCHANGED',style:const TextStyle(color:Colors.white54,fontSize:9,letterSpacing:1.1))]));
          }),
          if (_simulation != null) const SizedBox(height:14),
          TextField(controller:_achievement,keyboardType:TextInputType.number,decoration:const InputDecoration(labelText:'Target achievement')),
          const SizedBox(height:10),
          Row(children:[Expanded(child:FilledButton.icon(onPressed:_busy||_simulating?null:_simulateEvolution,icon:const Icon(Icons.auto_awesome),label:const Text('SIMULATE'))),const SizedBox(width:8),Expanded(child:OutlinedButton(onPressed:_busy?null:()=>_run(()=>widget.api.ownerSetEvolution(_number(_achievement),_tier,_stage,_reasonText)),child:const Text('APPLY')))]),
          const SizedBox(height:10),
          DropdownButtonFormField<String>(value:_tiers.contains(_tier)?_tier:null,items:_tiers.map((t)=>DropdownMenuItem(value:t,child:Text(t))).toList(),onChanged:(v){if(v!=null)setState(()=>_tier=v);},decoration:const InputDecoration(labelText:'Apply tier')),
          const SizedBox(height:10), TextFormField(initialValue:_stage,onChanged:(v)=>_stage=v,decoration:const InputDecoration(labelText:'Apply stage')),
          const SizedBox(height:10), TextField(controller:_reason,decoration:const InputDecoration(labelText:'Reason')),
          const SizedBox(height:10), OutlinedButton(onPressed:_busy?null:()=>_run(()=>widget.api.ownerResetEvolution(_reasonText)),child:const Text('RESET EVOLUTION'))
        ])),
        const SizedBox(height:14),
        _Card(title:'Owner audit log',child:_audit.isEmpty?const Text('No owner actions yet.',style:TextStyle(color:Colors.white54)):Column(children:_audit.take(25).map((e){
          final x=Map<String,dynamic>.from(e as Map);
          return ListTile(contentPadding:EdgeInsets.zero,leading:const Icon(Icons.receipt_long_outlined),title:Text('${x['action']} • ${x['target']}'),subtitle:Text('${x['reason']}\n${x['created_at']}',style:const TextStyle(color:Colors.white54,fontSize:11)),trailing:Text(x['amount']?.toString()??''));
        }).toList())),
        if(_error!=null) Padding(padding:const EdgeInsets.only(top:12),child:Text(_error!,style:const TextStyle(color:Colors.redAccent))),
      ])));
  }
}

class _GodBanner extends StatelessWidget {
  const _GodBanner({required this.god}); final bool god;
  @override Widget build(BuildContext c)=>Container(padding:const EdgeInsets.all(18),decoration:BoxDecoration(borderRadius:BorderRadius.circular(20),border:Border.all(color:god?const Color(0xFFE7C76A):Colors.white10),gradient:const LinearGradient(colors:[Color(0xFF19152A),Color(0xFF0D1117)])),child:Row(children:[Icon(god?Icons.bolt:Icons.admin_panel_settings_outlined,color:const Color(0xFFE7C76A)),const SizedBox(width:12),Expanded(child:Column(crossAxisAlignment:CrossAxisAlignment.start,children:[Text(god?'GOD MODE ACTIVE':'OWNER AUTHORITY',style:const TextStyle(fontWeight:FontWeight.w900,letterSpacing:1.5)),const SizedBox(height:4),Text(god?'Unrestricted internal development controls are available.':'Owner controls are authenticated.',style:const TextStyle(color:Colors.white54,fontSize:12))]))]));
}
class _Card extends StatelessWidget {
  const _Card({required this.title,required this.child}); final String title; final Widget child;
  @override Widget build(BuildContext c)=>Card(child:Padding(padding:const EdgeInsets.all(18),child:Column(crossAxisAlignment:CrossAxisAlignment.start,children:[Text(title,style:const TextStyle(fontSize:17,fontWeight:FontWeight.w800)),const SizedBox(height:14),child])));
}
class _Value extends StatelessWidget {
  const _Value(this.label,this.value); final String label,value;
  @override Widget build(BuildContext c)=>Row(children:[Expanded(child:Text(label,style:const TextStyle(color:Colors.white54))),Text(value,style:const TextStyle(fontWeight:FontWeight.w800,fontSize:18))]);
}
class _Error extends StatelessWidget {
  const _Error({required this.message,required this.retry}); final String message; final VoidCallback retry;
  @override Widget build(BuildContext c)=>Center(child:Padding(padding:const EdgeInsets.all(28),child:Column(mainAxisSize:MainAxisSize.min,children:[Text(message,textAlign:TextAlign.center),const SizedBox(height:12),OutlinedButton(onPressed:retry,child:const Text('Retry'))])));
}
