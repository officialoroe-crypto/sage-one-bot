import 'dart:async';

import 'package:flutter/foundation.dart';
import 'package:flutter/material.dart';
import 'package:google_sign_in/google_sign_in.dart';

import '../core/google_web_button.dart';
import '../core/identity_client.dart';
import '../theme/sage_theme.dart';

class LoginScreen extends StatefulWidget {
  const LoginScreen({required this.identity, required this.onSignedIn, super.key});

  final IdentityClient identity;
  final ValueChanged<Map<String, dynamic>> onSignedIn;

  @override
  State<LoginScreen> createState() => _LoginScreenState();
}

class _LoginScreenState extends State<LoginScreen> {
  bool _loading = false;
  bool _webReady = false;
  bool _developerMode = false;
    String? _error;
  StreamSubscription<GoogleSignInAuthenticationEvent>? _authSubscription;

  @override
  void initState() {
    super.initState();
    _loadIdentityConfig();
  }

  Future<void> _loadIdentityConfig() async {
    try {
      await widget.identity.loadConfig();
      if (!mounted) return;
      setState(() => _developerMode = widget.identity.developerMode);
      if (kIsWeb && !_developerMode) await _prepareWebGoogle();
    } catch (error) {
      if (mounted) setState(() => _error = _friendlyError(error));
    }
  }

  Future<void> _prepareWebGoogle() async {
    try {
      await widget.identity.initializeGoogle();
      _authSubscription = widget.identity.authenticationEvents.listen(
        _handleWebAuthentication,
        onError: _handleWebAuthenticationError,
      );
      if (mounted) setState(() => _webReady = true);
    } catch (error) {
      if (mounted) setState(() => _error = _friendlyError(error));
    }
  }

  Future<void> _handleWebAuthentication(GoogleSignInAuthenticationEvent event) async {
    if (event is! GoogleSignInAuthenticationEventSignIn) return;
    setState(() { _loading = true; _error = null; });
    try {
      final result = await widget.identity.signInWithGoogleAccount(event.user);
      if (mounted) widget.onSignedIn(result);
    } catch (error) {
      if (mounted) setState(() => _error = _friendlyError(error));
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  void _handleWebAuthenticationError(Object error) {
    if (mounted) setState(() => _error = _friendlyError(error));
  }

  Future<void> _developerLogin() async {
    setState(() { _loading = true; _error = null; });
    try {
      final result = await widget.identity.devLogin();
      if (mounted) widget.onSignedIn(result);
    } catch (error) {
      if (mounted) setState(() => _error = _friendlyError(error));
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  Future<void> _google() async {
    if (kIsWeb) return;
    setState(() { _loading = true; _error = null; });
    try {
      final result = await widget.identity.signInWithGoogle();
      if (mounted) widget.onSignedIn(result);
    } catch (error) {
      if (mounted) setState(() => _error = _friendlyError(error));
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  String _friendlyError(Object error) {
    final message = error.toString().replaceFirst('Exception: ', '').trim();
    return message.isEmpty ? 'Google sign-in failed. Please try again.' : message;
  }

  @override
  void dispose() {
    _authSubscription?.cancel();
      super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: SageTheme.voidBlack,
      body: Stack(
        children: [
          const Positioned.fill(child: _LoginBackdrop()),
          SafeArea(
            child: Center(
              child: SingleChildScrollView(
                padding: const EdgeInsets.fromLTRB(24, 34, 24, 28),
                child: ConstrainedBox(
                  constraints: const BoxConstraints(maxWidth: 440),
                  child: Column(
                    children: [
                      const _SageLoginMark(),
                      const SizedBox(height: 22),
                      const Text(
                        'SAGE ONE',
                        style: TextStyle(fontSize: 25, fontWeight: FontWeight.w800, letterSpacing: 4),
                      ),
                      const SizedBox(height: 7),
                      const Text(
                        'YOUR PERSONAL AI MENTOR',
                        style: TextStyle(color: SageTheme.cyan, fontSize: 9, letterSpacing: 2.2, fontWeight: FontWeight.w800),
                      ),
                      const SizedBox(height: 18),
                      const Text(
                        'Enter a workspace built to\nthink, research and execute with you.',
                        textAlign: TextAlign.center,
                        style: TextStyle(color: SageTheme.textSecondary, fontSize: 13, height: 1.5),
                      ),
                      const SizedBox(height: 34),
                      if (_developerMode)
                        _LoginAction(
                          icon: Icons.bolt,
                          label: _loading ? 'Opening SAGE…' : 'Enter SAGE Owner Mode',
                          onPressed: _loading ? null : _developerLogin,
                        )
                      else if (kIsWeb)
                        SizedBox(
                          width: double.infinity,
                          child: _webReady
                              ? buildGoogleWebButton()
                              : const Padding(
                                  padding: EdgeInsets.all(18),
                                  child: CircularProgressIndicator(),
                                ),
                        )
                      else
                        _LoginAction(
                          icon: Icons.g_mobiledata,
                          label: _loading ? 'Connecting to Google…' : 'Continue with Google',
                          onPressed: _loading ? null : _google,
                        ),
                      const SizedBox(height: 14),
                      Text(
                        _developerMode
                            ? 'Local owner access • no Google, SMS or OTP required'
                            : 'Your Google identity is verified by SAGE Core.',
                        textAlign: TextAlign.center,
                        style: const TextStyle(color: SageTheme.textSecondary, fontSize: 10, height: 1.4),
                      ),
                      if (_error != null) ...[
                        const SizedBox(height: 18),
                        Container(
                          width: double.infinity,
                          padding: const EdgeInsets.all(14),
                          decoration: BoxDecoration(
                            color: SageTheme.failure.withValues(alpha: .08),
                            borderRadius: BorderRadius.circular(16),
                            border: Border.all(color: SageTheme.failure.withValues(alpha: .28)),
                          ),
                          child: Row(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              const Icon(Icons.error_outline, color: SageTheme.failure, size: 18),
                              const SizedBox(width: 10),
                              Expanded(child: Text(_error!, style: const TextStyle(color: SageTheme.textPrimary, fontSize: 12, height: 1.4))),
                            ],
                          ),
                        ),
                      ],
                      const SizedBox(height: 34),
                      const Text(
                        'PRIVATE-FIRST • SECURE • EXECUTION READY',
                        style: TextStyle(color: SageTheme.textSecondary, fontSize: 8, letterSpacing: 1.5, fontWeight: FontWeight.w700),
                      ),
                    ],
                  ),
                ),
              ),
            ),
          ),
        ],
      ),
    );
  }
}

class _LoginAction extends StatelessWidget {
  const _LoginAction({required this.icon, required this.label, required this.onPressed});
  final IconData icon;
  final String label;
  final VoidCallback? onPressed;

  @override
  Widget build(BuildContext context) => SizedBox(
    width: double.infinity,
    height: 56,
    child: FilledButton.icon(
      onPressed: onPressed,
      icon: onPressed == null ? const SizedBox(width: 18, height: 18, child: CircularProgressIndicator(strokeWidth: 2)) : Icon(icon, size: 22),
      label: Text(label, style: const TextStyle(fontWeight: FontWeight.w700)),
    ),
  );
}

class _SageLoginMark extends StatelessWidget {
  const _SageLoginMark();

  @override
  Widget build(BuildContext context) => Container(
    width: 92,
    height: 92,
    alignment: Alignment.center,
    decoration: BoxDecoration(
      shape: BoxShape.circle,
      gradient: const RadialGradient(
        center: Alignment(-.35, -.4),
        colors: [Color(0xFF61E9FF), Color(0xFF1265D7), Color(0xFF020306)],
        stops: [0, .34, 1],
      ),
      border: Border.all(color: SageTheme.cyan.withValues(alpha: .65)),
      boxShadow: [BoxShadow(color: SageTheme.cyan.withValues(alpha: .22), blurRadius: 34)],
    ),
    child: const Text('S', style: TextStyle(fontSize: 54, fontWeight: FontWeight.w300, color: Colors.white)),
  );
}

class _LoginBackdrop extends StatelessWidget {
  const _LoginBackdrop();

  @override
  Widget build(BuildContext context) => DecoratedBox(
    decoration: const BoxDecoration(
      gradient: RadialGradient(
        center: Alignment(0, -.2),
        radius: 1.15,
        colors: [Color(0xFF0A2442), Color(0xFF04101F), SageTheme.voidBlack],
      ),
    ),
    child: CustomPaint(painter: _LoginStars(), child: const SizedBox.expand()),
  );
}

class _LoginStars extends CustomPainter {
  @override
  void paint(Canvas canvas, Size size) {
    final paint = Paint()..color = Colors.white.withValues(alpha: .2);
    for (var i = 0; i < 42; i++) {
      final x = ((i * 83 + 17) % 997) / 997 * size.width;
      final y = ((i * 149 + 29) % 991) / 991 * size.height;
      canvas.drawCircle(Offset(x, y), i % 8 == 0 ? .9 : .45, paint);
    }
  }
  @override
  bool shouldRepaint(covariant _LoginStars oldDelegate) => false;
}
