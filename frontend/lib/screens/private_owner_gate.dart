import 'package:flutter/material.dart';

import '../core/identity_client.dart';

/// Private-first entry point.
///
/// SAGE ONE currently runs as a single-owner local app. The older Google,
/// phone OTP, and onboarding flows remain in the identity layer for a future
/// multi-user/public mode, but they are deliberately not part of the private
/// app entry path.
class PrivateOwnerGate extends StatefulWidget {
  const PrivateOwnerGate({required this.child, this.identity, super.key});

  final Widget child;
  final IdentityClient? identity;

  @override
  State<PrivateOwnerGate> createState() => _PrivateOwnerGateState();
}

class _PrivateOwnerGateState extends State<PrivateOwnerGate> {
  late final IdentityClient _identity;
  String? _error;

  @override
  void initState() {
    super.initState();
    _identity = widget.identity ?? IdentityClient();
    _enter();
  }

  Future<void> _enter() async {
    try {
      final existing = await _identity.token();
      if (existing == null || existing.isEmpty) {
        await _identity.devLogin();
      }
      if (!mounted) return;
      Navigator.of(context).pushReplacement(
        MaterialPageRoute(builder: (_) => widget.child),
      );
    } catch (error) {
      if (mounted) {
        setState(() => _error = error.toString());
      }
    }
  }

  @override
  void dispose() {
    _identity.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: Colors.black,
      body: Center(
        child: _error == null
            ? const Column(
                mainAxisSize: MainAxisSize.min,
                children: [
                  CircularProgressIndicator(),
                  SizedBox(height: 18),
                  Text(
                    'ENTERING SAGE ONE',
                    style: TextStyle(
                      fontSize: 11,
                      letterSpacing: 2,
                      fontWeight: FontWeight.w700,
                    ),
                  ),
                ],
              )
            : Padding(
                padding: const EdgeInsets.all(28),
                child: Column(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    const Text(
                      'SAGE ONE PRIVATE MODE',
                      style: TextStyle(
                        fontSize: 14,
                        letterSpacing: 1.5,
                        fontWeight: FontWeight.w800,
                      ),
                    ),
                    const SizedBox(height: 12),
                    Text(
                      _error!,
                      textAlign: TextAlign.center,
                      style: const TextStyle(color: Colors.white60, fontSize: 12),
                    ),
                    const SizedBox(height: 18),
                    FilledButton(
                      onPressed: () {
                        setState(() => _error = null);
                        _enter();
                      },
                      child: const Text('Retry'),
                    ),
                  ],
                ),
              ),
      ),
    );
  }
}
