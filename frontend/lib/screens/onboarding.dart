import 'package:flutter/material.dart';

import '../core/identity_client.dart';
import '../theme/sage_theme.dart';

class OnboardingScreen extends StatefulWidget {
  const OnboardingScreen({
    required this.identity,
    required this.onComplete,
    this.initialProfile,
    this.privateOwnerMode = false,
    super.key,
  });

  final IdentityClient identity;
  final VoidCallback onComplete;
  final Map<String, dynamic>? initialProfile;
  final bool privateOwnerMode;

  @override
  State<OnboardingScreen> createState() => _OnboardingScreenState();
}

class _OnboardingScreenState extends State<OnboardingScreen> {
  final _nameController = TextEditingController();
  final _phoneController = TextEditingController();
  final _addressController = TextEditingController();
  final _ageController = TextEditingController();
  final _intentController = TextEditingController();
  final _otpController = TextEditingController();

  int _step = 0;
  bool _memoryConsent = false;
  bool _sendingOtp = false;
  bool _verifyingOtp = false;
  bool _saving = false;
  String? _challengeId;
  String? _error;
  String? _delivery;
  final Set<String> _capabilities = <String>{};

  static const _capabilityOptions = <Map<String, String>>[
    {'id': 'personal_mentor', 'label': 'Personal mentor'},
    {'id': 'learning', 'label': 'Learn & improve skills'},
    {'id': 'research', 'label': 'Research & find information'},
    {'id': 'work', 'label': 'Find work & opportunities'},
    {'id': 'business', 'label': 'Business, marketing & sales'},
    {'id': 'content', 'label': 'Content, video & creative work'},
    {'id': 'planning', 'label': 'Plan goals & execute tasks'},
    {'id': 'productivity', 'label': 'Organize life & productivity'},
  ];

  @override
  void initState() {
    super.initState();
    final profile = widget.initialProfile;
    if (profile != null) {
      _nameController.text = profile['name']?.toString() ?? '';
      _phoneController.text = profile['phone']?.toString() ?? '';
      _addressController.text = profile['address']?.toString() ?? '';
      final age = profile['age'];
      if (age != null) _ageController.text = age.toString();
    }
  }

  @override
  void dispose() {
    for (final c in [
      _nameController,
      _phoneController,
      _addressController,
      _ageController,
      _intentController,
      _otpController,
    ]) {
      c.dispose();
    }
    super.dispose();
  }

  Future<void> _sendOtp() async {
    final phone = _phoneController.text.trim();
    if (phone.isEmpty) {
      setState(() => _error = 'Enter your phone number first.');
      return;
    }
    setState(() {
      _sendingOtp = true;
      _error = null;
    });
    try {
      final result = await widget.identity.sendPhoneOtp(phone);
      if (!mounted) return;
      setState(() {
        _challengeId = result['challenge_id'] as String?;
        _delivery = result['delivery'] as String?;
      });
    } catch (error) {
      if (mounted) setState(() => _error = error.toString());
    } finally {
      if (mounted) setState(() => _sendingOtp = false);
    }
  }

  Future<void> _verifyOtp() async {
    final challenge = _challengeId;
    final code = _otpController.text.trim();
    if (challenge == null) {
      setState(() => _error = 'Send a verification code first.');
      return;
    }
    if (code.length != 6) {
      setState(() => _error = 'Enter the 6-digit verification code.');
      return;
    }
    setState(() {
      _verifyingOtp = true;
      _error = null;
    });
    try {
      await widget.identity.verifyPhoneOtp(challenge, code);
      if (mounted) {
        setState(() {
          _step = 1;
          _error = null;
        });
      }
    } catch (error) {
      if (mounted) setState(() => _error = error.toString());
    } finally {
      if (mounted) setState(() => _verifyingOtp = false);
    }
  }

  Future<void> _complete() async {
    final age = int.tryParse(_ageController.text.trim());
    if (age == null) {
      setState(() => _error = 'Enter a valid age.');
      return;
    }
    if (_nameController.text.trim().isEmpty ||
        _addressController.text.trim().isEmpty ||
        _intentController.text.trim().isEmpty) {
      setState(() => _error = 'Complete your name, address and help intent.');
      return;
    }

    setState(() {
      _saving = true;
      _error = null;
    });

    try {
      await widget.identity.completeOnboarding(
        name: _nameController.text.trim(),
        phone: _phoneController.text.trim(),
        address: _addressController.text.trim(),
        age: age,
        helpIntent: _intentController.text.trim(),
        capabilities: _capabilities.toList(),
        memoryConsent: _memoryConsent,
      );
      if (mounted) widget.onComplete();
    } catch (error) {
      if (mounted) setState(() => _error = error.toString());
    } finally {
      if (mounted) setState(() => _saving = false);
    }
  }

  Future<void> _next() async {
    if (_step == 0) {
      if (widget.privateOwnerMode) {
        setState(() {
          _step = 1;
          _error = null;
        });
        return;
      }
      if (_challengeId == null) {
        await _sendOtp();
      } else {
        await _verifyOtp();
      }
      return;
    }
    if (_step < 3) {
      setState(() {
        _step++;
        _error = null;
      });
    } else {
      await _complete();
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: SageTheme.voidBlack,
      body: DecoratedBox(
        decoration: const BoxDecoration(
          gradient: RadialGradient(
            center: Alignment(0, -.18),
            radius: 1.18,
            colors: [
              Color(0xFF0B2242),
              Color(0xFF061326),
              Color(0xFF020306),
            ],
            stops: [0, .5, 1],
          ),
        ),
        child: SafeArea(
        child: Column(
          children: [
            _topBar(),
            _progress(),
            Expanded(
              child: SingleChildScrollView(
                padding: const EdgeInsets.fromLTRB(20, 8, 20, 20),
                child: _page(),
              ),
            ),
            if (_error != null)
              Padding(
                padding: const EdgeInsets.fromLTRB(20, 0, 20, 10),
                child: Text(
                  _error!,
                  textAlign: TextAlign.center,
                  style: const TextStyle(color: SageTheme.failure, fontSize: 11),
                ),
              ),
            Padding(
              padding: const EdgeInsets.fromLTRB(20, 8, 20, 18),
              child: SizedBox(
                width: double.infinity,
                height: 54,
                child: FilledButton(
                  onPressed: (_saving || _sendingOtp || _verifyingOtp) ? null : _next,
                  child: Text(_buttonLabel),
                ),
              ),
            ),
          ],
        ),
      ),
      ),
    );
  }

  Widget _topBar() {
    return Padding(
      padding: const EdgeInsets.fromLTRB(20, 14, 12, 8),
      child: Row(
        children: [
          const _SageMark(size: 38),
          const SizedBox(width: 10),
          const Expanded(
            child: Text(
              'SAGE ONE',
              style: TextStyle(
                fontSize: 14,
                fontWeight: FontWeight.w800,
                letterSpacing: 1.5,
              ),
            ),
          ),
          if (_step > 0)
            IconButton(
              onPressed: _saving ? null : () => setState(() => _step--),
              icon: const Icon(Icons.arrow_back),
            ),
        ],
      ),
    );
  }

  Widget _progress() {
    return Padding(
      padding: const EdgeInsets.fromLTRB(20, 8, 20, 18),
      child: Row(
        children: List.generate(
          4,
          (index) => Expanded(
            child: AnimatedContainer(
              duration: const Duration(milliseconds: 220),
              height: 3,
              margin: EdgeInsets.only(right: index == 3 ? 0 : 6),
              decoration: BoxDecoration(
                color: index <= _step
                    ? SageTheme.cyan
                    : Colors.white.withValues(alpha: 0.07),
                borderRadius: BorderRadius.circular(8),
              ),
            ),
          ),
        ),
      ),
    );
  }

  String get _buttonLabel {
    if (_step == 0) {
      if (_sendingOtp) return 'Sending code…';
      if (_verifyingOtp) return 'Verifying…';
      if (widget.privateOwnerMode) return 'Continue';
      return _challengeId == null ? 'Send verification code' : 'Verify phone';
    }
    if (_saving) return 'Preparing your workspace…';
    return _step == 3 ? 'Enter SAGE ONE' : 'Continue';
  }

  Widget _page() {
    switch (_step) {
      case 0:
        return _phonePage();
      case 1:
        return _profilePage();
      case 2:
        return _capabilitiesPage();
      default:
        return _memoryPage();
    }
  }

  Widget _heading(String eyebrow, String title, String subtitle, IconData icon) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Icon(icon, color: _step == 3 ? SageTheme.violet : SageTheme.cyan, size: 25),
        const SizedBox(height: 14),
        Text(
          eyebrow,
          style: const TextStyle(
            color: SageTheme.cyan,
            fontSize: 9,
            fontWeight: FontWeight.w800,
            letterSpacing: 1.8,
          ),
        ),
        const SizedBox(height: 7),
        Text(
          title,
          style: const TextStyle(
            fontSize: 28,
            height: 1.08,
            fontWeight: FontWeight.w800,
          ),
        ),
        const SizedBox(height: 9),
        Text(
          subtitle,
          style: const TextStyle(
            color: SageTheme.textSecondary,
            fontSize: 12,
            height: 1.45,
          ),
        ),
        const SizedBox(height: 22),
      ],
    );
  }

  Widget _field(
    TextEditingController controller,
    String label,
    IconData icon, {
    TextInputType? keyboardType,
  }) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 12),
      child: TextField(
        controller: controller,
        keyboardType: keyboardType,
        decoration: InputDecoration(
          labelText: label,
          prefixIcon: Icon(icon, size: 20),
        ),
      ),
    );
  }

  Widget _phonePage() {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        _heading(
          'SECURE IDENTITY',
          widget.privateOwnerMode ? 'Start with your context.' : 'Verify your phone.',
          widget.privateOwnerMode
              ? 'Private Owner Mode does not require Google, SMS or OTP. You can add a phone later when external identity providers are configured.'
              : 'Your verified number protects your SAGE ONE identity and completes the first layer of your workspace.',
          Icons.verified_user_outlined,
        ),
        if (!widget.privateOwnerMode) _field(
          _phoneController,
          'Phone number',
          Icons.phone_outlined,
          keyboardType: TextInputType.phone,
        ),
        if (!widget.privateOwnerMode && _challengeId != null) ...[
          _field(
            _otpController,
            '6-digit verification code',
            Icons.password_outlined,
            keyboardType: TextInputType.number,
          ),
          Container(
            padding: const EdgeInsets.all(13),
            decoration: BoxDecoration(
              color: SageTheme.surface,
              borderRadius: BorderRadius.circular(14),
              border: Border.all(color: SageTheme.cyan.withValues(alpha: 0.18)),
            ),
            child: Text(
              _delivery == 'not_configured'
                  ? 'SMS delivery is not configured on this server yet.'
                  : 'Verification code sent to your number.',
              style: const TextStyle(color: SageTheme.textSecondary, fontSize: 11),
            ),
          ),
          TextButton(
            onPressed: _sendingOtp || _verifyingOtp ? null : _sendOtp,
            child: const Text('Send a new code'),
          ),
        ],
      ],
    );
  }

  Widget _profilePage() {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        _heading(
          'YOUR CONTEXT',
          'Build your context.',
          'A few basics give SAGE enough context to personalize planning, research and execution.',
          Icons.person_outline,
        ),
        _field(_nameController, 'Your name', Icons.badge_outlined),
        _field(_addressController, 'Address', Icons.location_on_outlined),
        _field(
          _ageController,
          'Age',
          Icons.cake_outlined,
          keyboardType: TextInputType.number,
        ),
      ],
    );
  }

  Widget _capabilitiesPage() {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        _heading(
          'SAGE CONFIGURATION',
          'What should SAGE understand?',
          'Choose the areas where you want SAGE to become your mentor and execution partner.',
          Icons.hub_outlined,
        ),
        Wrap(
          spacing: 8,
          runSpacing: 8,
          children: _capabilityOptions.map((option) {
            final id = option['id']!;
            final selected = _capabilities.contains(id);
            return FilterChip(
              selected: selected,
              label: Text(option['label']!),
              onSelected: (enabled) => setState(() {
                if (enabled) {
                  _capabilities.add(id);
                } else {
                  _capabilities.remove(id);
                }
              }),
            );
          }).toList(),
        ),
        const SizedBox(height: 18),
        TextField(
          controller: _intentController,
          minLines: 5,
          maxLines: 8,
          decoration: const InputDecoration(
            labelText: 'What should SAGE help with?',
            hintText: 'Tell SAGE the outcomes you want to work toward…',
            alignLabelWithHint: true,
          ),
        ),
      ],
    );
  }

  Widget _memoryPage() {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        _heading(
          'PRIVATE BY DEFAULT',
          'Your memory. Your control.',
          'SAGE can remember useful context, but permission comes first.',
          Icons.lock_outline,
        ),
        for (final item in const [
          (
            'YOU CONTROL MEMORY',
            'View, edit or delete saved memories.',
            Icons.tune_outlined,
          ),
          (
            'NO SILENT LEARNING',
            'Private context is not silently turned into memory.',
            Icons.visibility_off_outlined,
          ),
          (
            'WORLD INTELLIGENCE IS SEPARATE',
            'Public-world knowledge stays separate from personal memory.',
            Icons.public_outlined,
          ),
        ])
          Padding(
            padding: const EdgeInsets.only(bottom: 10),
            child: Card(
              child: ListTile(
                contentPadding: const EdgeInsets.symmetric(horizontal: 14, vertical: 4),
                leading: Icon(item.$3, color: SageTheme.violet, size: 20),
                title: Text(
                  item.$1,
                  style: const TextStyle(fontSize: 10, fontWeight: FontWeight.w800, letterSpacing: .7),
                ),
                subtitle: Padding(
                  padding: const EdgeInsets.only(top: 4),
                  child: Text(
                    item.$2,
                    style: const TextStyle(color: SageTheme.textSecondary, fontSize: 11, height: 1.35),
                  ),
                ),
              ),
            ),
          ),
        SwitchListTile.adaptive(
          contentPadding: EdgeInsets.zero,
          value: _memoryConsent,
          onChanged: (value) => setState(() => _memoryConsent = value),
          title: const Text(
            'Allow SAGE to remember useful setup preferences',
            style: TextStyle(fontSize: 12, fontWeight: FontWeight.w700),
          ),
          subtitle: const Text(
            'You can change or delete memory later.',
            style: TextStyle(fontSize: 10),
          ),
        ),
      ],
    );
  }
}


class _SageMark extends StatelessWidget {
  const _SageMark({required this.size});

  final double size;

  @override
  Widget build(BuildContext context) {
    return Container(
      width: size,
      height: size,
      alignment: Alignment.center,
      decoration: BoxDecoration(
        shape: BoxShape.circle,
        gradient: const RadialGradient(
          center: Alignment(-.3, -.35),
          radius: .95,
          colors: [
            Color(0xFF5FE6FF),
            Color(0xFF1263D2),
            Color(0xFF061630),
            Color(0xFF020306),
          ],
          stops: [0, .3, .72, 1],
        ),
        border: Border.all(color: SageTheme.cyan.withValues(alpha: .5)),
        boxShadow: [
          BoxShadow(
            color: SageTheme.cyan.withValues(alpha: .18),
            blurRadius: 24,
            spreadRadius: 1,
          ),
        ],
      ),
      child: Text(
        'S',
        style: TextStyle(
          color: Colors.white,
          fontSize: size * .54,
          height: 1,
          fontWeight: FontWeight.w300,
          shadows: const [Shadow(color: SageTheme.cyan, blurRadius: 10)],
        ),
      ),
    );
  }
}
