import 'package:flutter/material.dart';
import '../core/sage_api.dart';
import '../theme/sage_theme.dart';
import 'package:url_launcher/url_launcher.dart';


class _RetryableLoadError extends StatelessWidget {
  const _RetryableLoadError({
    required this.message,
    required this.onRetry,
  });

  final String message;
  final VoidCallback onRetry;

  @override
  Widget build(BuildContext context) => Card(
        child: Padding(
          padding: const EdgeInsets.all(14),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(message, style: const TextStyle(color: SageTheme.failure)),
              const SizedBox(height: 8),
              Align(
                alignment: Alignment.centerRight,
                child: TextButton(
                  onPressed: onRetry,
                  child: const Text('Retry'),
                ),
              ),
            ],
          ),
        ),
      );
}

class _Page extends StatelessWidget {
  const _Page({required this.title, required this.body});
  final String title; final Widget body;
  @override Widget build(BuildContext c)=>Scaffold(
    backgroundColor:Theme.of(c).scaffoldBackgroundColor,
    appBar:AppBar(title:Text(title),backgroundColor:Colors.transparent),
    body:body,
  );
}

class SparkWalletScreen extends StatefulWidget {
  const SparkWalletScreen({required this.api,super.key}); final SageApi api;
  @override State<SparkWalletScreen> createState()=>_SparkWalletState();
}
class _SparkWalletState extends State<SparkWalletScreen>{
  Map<String,dynamic>? data; Object? error;
  Future<void> load()async{try{final v=await widget.api.economyMe();if(mounted)setState((){data=v;error=null;});}catch(e){if(mounted)setState(()=>error=e);}}
  @override void initState(){super.initState();load();}
  @override Widget build(BuildContext c)=>_Page(title:'Spark Wallet',body:RefreshIndicator(onRefresh:load,child:ListView(padding:const EdgeInsets.all(20),children:[
    if(error!=null)_RetryableLoadError(message:'Wallet error: ${error.toString()}',onRetry:(){load();}),
    if(data!=null)...[
      _row('Balance',data!['spark']?['balance']),
      _row('Lifetime earned',data!['spark']?['lifetime_earned']),
      _row('Lifetime spent',data!['spark']?['lifetime_spent']),
      const SizedBox(height:20),const Text('Spark ledger',style:TextStyle(fontSize:20,fontWeight:FontWeight.w800)),
      ...(data!['ledger'] is List?data!['ledger'] as List:const []).map((e)=>ListTile(
        title:Text(e['reason']?.toString()??'Spark movement'),
        subtitle:Text(e['created_at']?.toString()??''),
        trailing:Text(e['delta']?.toString()??'0'),
      )),
    ] else if(error==null)const Center(child:CircularProgressIndicator()),
  ])));
  Widget _row(String a,d)=>Card(child:ListTile(title:Text(a),trailing:Text((d??0).toString(),style:const TextStyle(fontSize:22,fontWeight:FontWeight.w900,color:SageTheme.cyan))));
}

class TransactionsScreen extends StatefulWidget {
  const TransactionsScreen({required this.api,super.key}); final SageApi api;
  @override State<TransactionsScreen> createState()=>_TransactionsState();
}
class _TransactionsState extends State<TransactionsScreen>{
  List items=[]; Object? error;
  Future<void> load()async{try{final d=await widget.api.economyMe();if(mounted)setState((){items=d['ledger'] is List?d['ledger']:[];error=null;});}catch(e){if(mounted)setState(()=>error=e);}}
  @override void initState(){super.initState();load();}
  @override Widget build(BuildContext c)=>_Page(title:'Transactions',body:RefreshIndicator(onRefresh:load,child:ListView(padding:const EdgeInsets.all(20),children:[
    if(error!=null)_RetryableLoadError(message:'Transaction error: ${error.toString()}',onRetry:(){load();}),
    ...items.map((e)=>Card(child:ListTile(title:Text(e['reason']?.toString()??'Spark movement'),subtitle:Text(e['reference']?.toString()??e['created_at']?.toString()??''),trailing:Text(e['delta']?.toString()??'0')))),
    if(items.isEmpty&&error==null)const Padding(padding:EdgeInsets.all(40),child:Text('No Spark transactions yet.')),
  ])));
}

class EvolutionFinalScreen extends StatefulWidget {
  const EvolutionFinalScreen({required this.api,super.key}); final SageApi api;
  @override State<EvolutionFinalScreen> createState()=>_EvolutionFinalState();
}
class _EvolutionFinalState extends State<EvolutionFinalScreen>{
  Map<String,dynamic>? data; List tiers=[]; Object? error;
  Future<void> load()async{try{final d=await widget.api.economyMe();final t=await widget.api.evolutionTiers();if(mounted)setState((){data=d;tiers=t;error=null;});}catch(e){if(mounted)setState(()=>error=e);}}
  @override void initState(){super.initState();load();}
  @override Widget build(BuildContext c)=>_Page(title:'Evolution',body:RefreshIndicator(onRefresh:load,child:ListView(padding:const EdgeInsets.all(20),children:[
    if(error!=null)_RetryableLoadError(message:'Evolution error: ${error.toString()}',onRetry:(){load();}),
    if(data!=null)...[
      Text("Tier: ${data!['evolution']?['tier']?.toString() ?? 'Bronze'}",style:const TextStyle(fontSize:28,fontWeight:FontWeight.w900)),
      Text("Stage: ${data!['evolution']?['stage']?.toString() ?? 'LOW'}"),
      Text("Achievement: ${data!['evolution']?['lifetime_achievement']?.toString() ?? '0'}"),
      const SizedBox(height:12),
      LinearProgressIndicator(value:((data!['evolution']?['progress']?['ratio']??0) as num).toDouble()),
      const SizedBox(height:24),const Text('Canonical tiers',style:TextStyle(fontSize:20,fontWeight:FontWeight.w800)),
      ...tiers.map((e)=>ListTile(title:Text(e['tier']?.toString()??''),trailing:Text(e['threshold']?.toString()??'0'))),
    ] else if(error==null)const Center(child:CircularProgressIndicator()),
  ])));
}

class ProfileFinalScreen extends StatefulWidget {
  const ProfileFinalScreen({required this.api,super.key}); final SageApi api;
  @override State<ProfileFinalScreen> createState()=>_ProfileFinalState();
}
class _ProfileFinalState extends State<ProfileFinalScreen>{
  final name=TextEditingController(),intent=TextEditingController(),address=TextEditingController(),age=TextEditingController(); bool saving=false; bool memoryConsent=false;
  Future<void> load()async{try{final d=await widget.api.profileMe();if(!mounted)return;final p=d['profile'] is Map?Map<String,dynamic>.from(d['profile']):{};name.text=p['name']?.toString()??'';intent.text=p['help_intent']?.toString()??'';address.text=p['address']?.toString()??'';age.text=p['age']?.toString()??'';memoryConsent=p['memory_consent']==true;setState((){});}catch(e){_msg('Profile load failed: ${e.toString()}');}}
  Future<void> save()async{
    final cleanName=name.text.trim();
    final cleanAddress=address.text.trim();
    final cleanIntent=intent.text.trim();
    final ageText=age.text.trim();
    final parsedAge=ageText.isEmpty?null:int.tryParse(ageText);
    if(cleanName.isEmpty){_msg('Enter your name.');return;}
    if(cleanAddress.isEmpty){_msg('Enter your address.');return;}
    if(cleanIntent.isEmpty){_msg('Enter what you want SAGE to help with.');return;}
    if(ageText.isNotEmpty&&(parsedAge==null||parsedAge<1||parsedAge>120)){_msg('Enter an age from 1 to 120, or leave it blank.');return;}
    setState(()=>saving=true);
    try{await widget.api.updateProfile(name:cleanName,address:cleanAddress,age:parsedAge,helpIntent:cleanIntent,memoryConsent:memoryConsent);_msg('Profile saved.');}
    catch(e){_msg('Profile save failed: ${e.toString()}');}
    finally{if(mounted)setState(()=>saving=false);}
  }
  void _msg(String s){if(mounted)ScaffoldMessenger.of(context).showSnackBar(SnackBar(content:Text(s)));}
  @override void initState(){super.initState();load();}
  @override void dispose(){name.dispose();intent.dispose();address.dispose();age.dispose();super.dispose();}
  @override Widget build(BuildContext c)=>_Page(title:'Profile',body:ListView(padding:const EdgeInsets.all(20),children:[
    TextField(controller:name,decoration:const InputDecoration(labelText:'Name')),
    const SizedBox(height:12),TextField(controller:address,decoration:const InputDecoration(labelText:'Address')),
    const SizedBox(height:12),TextField(controller:age,keyboardType:TextInputType.number,decoration:const InputDecoration(labelText:'Age')),
    const SizedBox(height:12),TextField(controller:intent,maxLines:3,decoration:const InputDecoration(labelText:'SAGE help intent')),
    SwitchListTile(contentPadding:EdgeInsets.zero,title:const Text('Memory consent'),subtitle:const Text('Allow SAGE to remember useful preferences.'),value:memoryConsent,onChanged:(v)=>setState(()=>memoryConsent=v)),
    const SizedBox(height:16),FilledButton(onPressed:saving?null:save,child:Text(saving?'Saving…':'Save profile')),
  ]));
}

class SettingsFinalScreen extends StatefulWidget {
  const SettingsFinalScreen({required this.api,super.key}); final SageApi api;
  @override State<SettingsFinalScreen> createState()=>_SettingsFinalState();
}
class _SettingsFinalState extends State<SettingsFinalScreen> {
  bool notifications = true;
  bool compact = false;
  String themeMode = 'dark';
  bool saving = false;
  bool loading = true;
  bool _loaded = false;
  Object? _loadError;
  Map<String, dynamic> basic = <String, dynamic>{};

  Future<void> load() async {
    setState(() {
      loading = true;
      _loadError = null;
    });
    try {
      final response = await widget.api.profileMe();
      if (!mounted) return;

      final rawProfile = response['profile'];
      if (rawProfile is! Map) {
        throw const FormatException('The profile response did not include profile data.');
      }
      final profile = Map<String, dynamic>.from(rawProfile);
      final rawBasic = profile['basic_info'];
      final nextBasic = rawBasic is Map
          ? Map<String, dynamic>.from(rawBasic)
          : <String, dynamic>{};
      final rawSettings = nextBasic['settings'];
      final settings = rawSettings is Map
          ? Map<String, dynamic>.from(rawSettings)
          : <String, dynamic>{};

      setState(() {
        basic = nextBasic;
        notifications = settings['notifications'] is bool
            ? settings['notifications'] as bool
            : true;
        compact = settings['compact_mode'] is bool
            ? settings['compact_mode'] as bool
            : false;
        themeMode = settings['theme_mode'] is String &&
                const ['dark', 'light', 'system']
                    .contains(settings['theme_mode'])
            ? settings['theme_mode'] as String
            : SageTheme.preferenceFromMode(SageTheme.mode.value);
        _loaded = true;
        loading = false;
        _loadError = null;
      });
      SageTheme.mode.value = SageTheme.modeFromPreference(themeMode);
    } catch (error) {
      if (!mounted) return;
      setState(() {
        _loaded = false;
        loading = false;
        _loadError = error;
      });
    }
  }

  Future<void> save() async {
    // Never replace basic_info with defaults when the saved profile could
    // not be loaded. Keep the write path gated on a successful profile read.
    if (!_loaded || saving) return;
    setState(() => saving = true);
    try {
      // Update only settings owned by this screen. Preserve future or
      // server-managed preferences (for example theme mode) that this UI
      // does not expose yet.
      final currentSettings = basic['settings'] is Map
          ? Map<String, dynamic>.from(basic['settings'] as Map)
          : <String, dynamic>{};
      currentSettings['notifications'] = notifications;
      currentSettings['compact_mode'] = compact;
      currentSettings['theme_mode'] = themeMode;
      basic['settings'] = currentSettings;
      await widget.api.updateProfile(basicInfo: basic);
      if (mounted) {
        SageTheme.mode.value = SageTheme.modeFromPreference(themeMode);
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('Settings saved.')),
        );
      }
    } catch (error) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Settings save failed: ${error.toString()}')),
        );
      }
    } finally {
      if (mounted) setState(() => saving = false);
    }
  }

  @override
  void initState() {
    super.initState();
    load();
  }

  @override
  Widget build(BuildContext context) => _Page(
        title: 'Settings',
        body: ListView(
          padding: const EdgeInsets.all(20),
          children: [
            if (loading) const LinearProgressIndicator(),
            if (_loadError != null)
              Card(
                child: ListTile(
                  leading: const Icon(Icons.error_outline),
                  title: const Text('Settings could not be loaded'),
                  subtitle: const Text(
                    'Your existing profile was not changed. Retry loading before saving settings.',
                  ),
                  trailing: TextButton(
                    onPressed: loading ? null : load,
                    child: const Text('Retry'),
                  ),
                ),
              ),
            SwitchListTile(
              title: const Text('Notifications'),
              value: notifications,
              onChanged: !_loaded || saving
                  ? null
                  : (value) => setState(() => notifications = value),
            ),
            SwitchListTile(
              title: const Text('Compact mode'),
              value: compact,
              onChanged: !_loaded || saving
                  ? null
                  : (value) => setState(() => compact = value),
            ),
            const SizedBox(height: 8),
            DropdownButtonFormField<String>(
              value: themeMode,
              decoration: const InputDecoration(labelText: 'Appearance'),
              items: const [
                DropdownMenuItem(value: 'dark', child: Text('Dark')),
                DropdownMenuItem(value: 'light', child: Text('Light')),
                DropdownMenuItem(value: 'system', child: Text('System default')),
              ],
              onChanged: !_loaded || saving
                  ? null
                  : (value) {
                      if (value != null) setState(() => themeMode = value);
                    },
            ),
            const SizedBox(height: 16),
            FilledButton(
              onPressed: !_loaded || saving ? null : save,
              child: Text(saving ? 'Saving…' : 'Save settings'),
            ),
          ],
        ),
      );
}

class NotificationsFinalScreen extends StatefulWidget {
  const NotificationsFinalScreen({required this.api,super.key}); final SageApi api;
  @override State<NotificationsFinalScreen> createState()=>_NotificationsFinalState();
}
class _NotificationsFinalState extends State<NotificationsFinalScreen>{
  List items=[]; Object? error;
  Future<void> load()async{try{final v=await widget.api.notifications();if(mounted)setState((){items=v;error=null;});}catch(e){if(mounted)setState(()=>error=e);}}
  Future<void> read(String id) async {
  try {
    await widget.api.markNotificationRead(id);
    await load();
  } catch (e) {
    if (mounted) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('Could not mark notification read: ${e.toString()}')),
      );
    }
  }
}
  @override void initState(){super.initState();load();}
  @override Widget build(BuildContext c)=>_Page(title:'Notifications',body:RefreshIndicator(onRefresh:load,child:ListView(padding:const EdgeInsets.all(20),children:[
    Row(mainAxisAlignment:MainAxisAlignment.spaceBetween,children:[const Text('Activity',style:TextStyle(fontSize:20,fontWeight:FontWeight.w800)),TextButton(onPressed:()async{
      try {
        await widget.api.markAllNotificationsRead();
        await load();
      } catch (e) {
        if (mounted) {
          ScaffoldMessenger.of(context).showSnackBar(
            SnackBar(content: Text('Could not mark notifications read: ${e.toString()}')),
          );
        }
      }
    },child:const Text('Mark all read'))]),
    if(error!=null)_RetryableLoadError(message:'Notification error: ${error.toString()}',onRetry:(){load();}),
    ...items.map((n)=>Card(child:ListTile(title:Text(n['title']?.toString()??n['message']?.toString()??'SAGE update'),subtitle:Text(n['created_at']?.toString()??''),trailing:IconButton(icon:const Icon(Icons.done),onPressed:()=>read(n['id'].toString()))))),
    if(items.isEmpty&&error==null)const Padding(padding:EdgeInsets.all(40),child:Text('You are all caught up.')),
  ])));
}

class PaymentFinalScreen extends StatefulWidget {
  const PaymentFinalScreen({required this.api,super.key}); final SageApi api;
  @override State<PaymentFinalScreen> createState()=>_PaymentFinalState();
}
class _PaymentFinalState extends State<PaymentFinalScreen>{
  Map<String,dynamic>? status; Object? error;
  Future<void> load()async{try{final v=await widget.api.paymentStatus();if(mounted)setState((){status=v;error=null;});}catch(e){if(mounted)setState(()=>error=e);}}
  @override void initState(){super.initState();load();}
  @override Widget build(BuildContext c)=>_Page(title:'Payments',body:ListView(padding:const EdgeInsets.all(20),children:[
    const Text('Provider readiness',style:TextStyle(fontSize:22,fontWeight:FontWeight.w800)),
    if(status!=null)Card(child:ListTile(title:Text(status!['configured']==true?'Provider configured':'Not configured'),subtitle:Text(status!['message']?.toString()??''))),
    if(error!=null)_RetryableLoadError(message:'Payment status error: ${error.toString()}',onRetry:(){load();}),
    const SizedBox(height:20),const Text('No payment action is exposed until a real provider is configured.',style:TextStyle(color:SageTheme.textSecondary)),
  ]));
}

class FileManagerFinalScreen extends StatefulWidget {
  const FileManagerFinalScreen({required this.api,super.key}); final SageApi api;
  @override State<FileManagerFinalScreen> createState()=>_FileManagerFinalState();
}
class _FileManagerFinalState extends State<FileManagerFinalScreen>{
  List items=[]; Object? error;
  Future<void> load()async{try{final v=await widget.api.tasks();if(mounted)setState((){items=v;error=null;});}catch(e){if(mounted)setState(()=>error=e);}}
  @override void initState(){super.initState();load();}
  @override Widget build(BuildContext c)=>_Page(title:'File Manager',body:RefreshIndicator(onRefresh:load,child:ListView(padding:const EdgeInsets.all(20),children:[
    const Text('Task artifacts',style:TextStyle(fontSize:22,fontWeight:FontWeight.w800)),
    if(error!=null)_RetryableLoadError(message:'File manager error: ${error.toString()}',onRetry:(){load();}),
    ...items.map((t){final a=t is Map&&t['artifact'] is Map?t['artifact']:null;return a==null?const SizedBox.shrink():Card(child:ListTile(title:Text(a['name']?.toString()??'Artifact'),subtitle:Text(a['mime_type']?.toString()??''),onTap:() async {
  final raw = a['url'] ?? a['uri'];
  final uri = raw == null ? null : Uri.tryParse(raw.toString());
  if (uri == null || !(uri.scheme == 'http' || uri.scheme == 'https')) {
    if (mounted) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('This artifact does not have an openable URL.')),
      );
    }
    return;
  }
  var opened = false;
  try {
    opened = await launchUrl(uri, mode: LaunchMode.externalApplication);
  } catch (_) {
    // Platform channels may throw when no compatible handler is installed.
    opened = false;
  }
  if (!opened && mounted) {
    ScaffoldMessenger.of(context).showSnackBar(
      const SnackBar(content: Text('SAGE could not open this artifact. Check that a browser is installed and try again.')),
    );
  }
},));}),
    if(items.isEmpty&&error==null)const Padding(padding:EdgeInsets.all(40),child:Text('No task artifacts found yet.')),
  ])));
}

class AiStudioFinalScreen extends StatefulWidget {
  const AiStudioFinalScreen({required this.api,super.key}); final SageApi api;
  @override State<AiStudioFinalScreen> createState()=>_AiStudioFinalState();
}
class _AiStudioFinalState extends State<AiStudioFinalScreen>{
  List items=[]; Object? error;
  final TextEditingController _workspaceName = TextEditingController();
  final TextEditingController _workspaceSlug = TextEditingController();
  Future<void> load()async{try{final v=await widget.api.workflowWorkspaces();if(mounted)setState((){items=v;error=null;});}catch(e){if(mounted)setState(()=>error=e);}}
  Future<void> createWorkspace()async{
    _workspaceName.clear();
    _workspaceSlug.clear();
    final ok=await showDialog<bool>(context:context,builder:(c)=>StatefulBuilder(builder:(c,setDialogState)=>AlertDialog(
      title:const Text('Create workspace'),
      content:Column(mainAxisSize:MainAxisSize.min,children:[
        TextField(controller:_workspaceName,onChanged:(_)=>setDialogState((){}),decoration:const InputDecoration(labelText:'Name')),
        TextField(controller:_workspaceSlug,onChanged:(_)=>setDialogState((){}),decoration:const InputDecoration(labelText:'Slug')),
      ]),
      actions:[
        TextButton(onPressed:()=>Navigator.pop(c,false),child:const Text('Cancel')),
        FilledButton(onPressed:_workspaceName.text.trim().isEmpty||_workspaceSlug.text.trim().isEmpty?null:()=>Navigator.pop(c,true),child:const Text('Create')),
      ],
    )));
    if(ok==true){try{await widget.api.createWorkflowWorkspace(name:_workspaceName.text.trim(),slug:_workspaceSlug.text.trim());await load();}catch(e){if(mounted)ScaffoldMessenger.of(context).showSnackBar(SnackBar(content:Text('Create failed: ${e.toString()}')));}}
  }
  @override void initState(){super.initState();load();}
  @override void dispose(){_workspaceName.dispose();_workspaceSlug.dispose();super.dispose();}
  @override Widget build(BuildContext c)=>_Page(title:'AI Studio',body:ListView(padding:const EdgeInsets.all(20),children:[
    Row(mainAxisAlignment:MainAxisAlignment.spaceBetween,children:[const Text('Workflow Studio',style:TextStyle(fontSize:22,fontWeight:FontWeight.w800)),FilledButton.icon(onPressed:createWorkspace,icon:const Icon(Icons.add),label:const Text('Workspace'))]),
    if(error!=null)_RetryableLoadError(message:'AI Studio error: ${error.toString()}',onRetry:(){load();}),
    ...items.map((w)=>Card(child:ListTile(title:Text(w['name']?.toString()??w['slug']?.toString()??'Workspace'),subtitle:Text(w['workspace_type']?.toString()??'personal')))),
    if(items.isEmpty&&error==null)const Padding(padding:EdgeInsets.all(40),child:Text('No workspaces yet.')),
  ]));
}
