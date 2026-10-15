import 'package:flutter/material.dart';

import '../core/identity_client.dart';
import 'login.dart';
import 'onboarding.dart';

bool shouldRequireOnboarding(
  Map<String, dynamic> profile, {
  required bool developerMode,
  required bool ownerMode,
}) {
  return profile['onboarding_completed'] != true;
}

class AuthGate extends StatefulWidget {
  const AuthGate({
    required this.childBuilder,
    this.identity,
    super.key,
  });

  final Widget Function(IdentityClient identity) childBuilder;
  final IdentityClient? identity;

  @override
  State<AuthGate> createState() => _AuthGateState();
}

class _AuthGateState extends State<AuthGate> {
  late final IdentityClient _identity;
  Map<String, dynamic>? _profile;
  bool _developerMode = false;
  bool _ownerMode = false;
  bool _loading = true;

  @override
  void initState() {
    super.initState();
    _identity = widget.identity ?? IdentityClient();
    _restore();
  }

  @override
  void dispose() {
    _identity.dispose();
    super.dispose();
  }

  Future<void> _restore() async {
    setState(() {
      _loading = true;
    });

    try {
      final token = await _identity.token();
      if (token == null || token.isEmpty) {
        if (mounted) setState(() => _loading = false);
        return;
      }

      final result = await _identity.me();
      final profile = result['profile'];
      if (!mounted) return;

      setState(() {
        _profile = profile is Map
            ? Map<String, dynamic>.from(profile)
            : null;
        _developerMode = result['developer_mode'] == true;
        _ownerMode = result['owner_mode'] == true;
        _loading = false;
      });
    } catch (_) {
      // Clearing a stale local session must not depend on the identity
      // provider being reachable or configured (for example in private
      // owner mode without Google sign-in).
      try {
        await _identity.signOut();
      } catch (_) {
        // IdentityClient clears its stored token in a finally block. A
        // provider sign-out error must not leave the app on an endless loader.
      }
      if (mounted) {
        setState(() {
          _profile = null;
          _developerMode = false;
          _ownerMode = false;
          _loading = false;
        });
      }
    }
  }

  void _signedIn(Map<String, dynamic> result) {
    final profile = result['profile'];
    setState(() {
      _profile = profile is Map
          ? Map<String, dynamic>.from(profile)
          : <String, dynamic>{};
      _developerMode = result['developer_mode'] == true;
      _ownerMode = result['owner_mode'] == true;
      _loading = false;
    });
  }

  void _completed() {
    _restore();
  }

  @override
  Widget build(BuildContext context) {
    if (_loading) {
      return const Scaffold(
        backgroundColor: Colors.black,
        body: Center(child: CircularProgressIndicator()),
      );
    }

    if (_profile == null) {
      return LoginScreen(
        identity: _identity,
        onSignedIn: _signedIn,
      );
    }

    final onboardingRequired = shouldRequireOnboarding(
      _profile!,
      developerMode: _developerMode,
      ownerMode: _ownerMode,
    );
    if (onboardingRequired) {
      return OnboardingScreen(
        identity: _identity,
        initialProfile: _profile,
        onComplete: _completed,
        privateOwnerMode: _developerMode || _ownerMode,
      );
    }

    return widget.childBuilder(_identity);
  }
}
