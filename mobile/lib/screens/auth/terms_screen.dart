import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../../core/session.dart';
import '../../core/theme.dart';
import '../../widgets/common.dart';
import '../../widgets/terms_text.dart';
import 'phone_screen.dart';

/// First screen: read the terms and agree before anything else (SPEC 2).
/// With reaccept=true: a logged-in customer must accept a new version.
class TermsScreen extends StatefulWidget {
  const TermsScreen({super.key, this.reaccept = false});
  final bool reaccept;

  @override
  State<TermsScreen> createState() => _TermsScreenState();
}

class _TermsScreenState extends State<TermsScreen> {
  Map<String, dynamic>? _terms;
  Object? _error;
  bool _agreed = false;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    setState(() => _error = null);
    try {
      final t = await context.read<Session>().api.get('terms/current/');
      setState(() => _terms = Map<String, dynamic>.from(t));
    } catch (e) {
      setState(() => _error = e);
    }
  }

  Future<void> _continue() async {
    final s = context.read<Session>();
    final version = _terms!['version'] as int;
    if (widget.reaccept) {
      await s.api.post('terms/accept/', {'terms_version': version});
      await s.refreshMe();
    } else {
      await Navigator.of(context).push(
        MaterialPageRoute(builder: (_) => PhoneScreen(termsVersion: version)),
      );
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: SafeArea(
        child: _error != null
            ? ErrorRetry(error: _error!, onRetry: _load)
            : _terms == null
            ? const Loading()
            : Column(
                children: [
                  Padding(
                    padding: const EdgeInsets.fromLTRB(20, 16, 20, 4),
                    child: Image.asset(
                      'assets/images/Bareeq-Logo-Horizontal-color.png',
                      height: 56,
                    ),
                  ),
                  if (widget.reaccept)
                    const Padding(
                      padding: EdgeInsets.symmetric(horizontal: 20),
                      child: Muted(
                        'الشروط اتحدثت. اقراها ووافق عشان تكمل.',
                        align: TextAlign.center,
                      ),
                    ),
                  Expanded(
                    child: Container(
                      margin: const EdgeInsets.fromLTRB(16, 12, 16, 0),
                      decoration: BoxDecoration(
                        color: Colors.white,
                        borderRadius: BorderRadius.circular(16),
                        border: Border.all(color: BrandColors.line),
                      ),
                      child: SingleChildScrollView(
                        padding: const EdgeInsets.all(18),
                        child: TermsText('${_terms!['text']}'),
                      ),
                    ),
                  ),
                  Padding(
                    padding: const EdgeInsets.fromLTRB(16, 8, 16, 16),
                    child: Column(
                      children: [
                        CheckboxListTile(
                          value: _agreed,
                          onChanged: (v) =>
                              setState(() => _agreed = v ?? false),
                          controlAffinity: ListTileControlAffinity.leading,
                          contentPadding: EdgeInsets.zero,
                          title: const Text(
                            'قريت الشروط وموافق عليها',
                            style: TextStyle(fontWeight: FontWeight.w600),
                          ),
                        ),
                        BusyButton(
                          label: 'موافق، كمّل',
                          onPressed: _agreed ? _continue : null,
                        ),
                      ],
                    ),
                  ),
                ],
              ),
      ),
    );
  }
}
