import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../../core/api.dart';
import '../../core/session.dart';
import '../../widgets/common.dart';
import '../setup_screen.dart';

/// Type the code. A new number also fills name (required), referral code and
/// "how did you hear about us" (optional), then the same code is sent again.
class CodeScreen extends StatefulWidget {
  const CodeScreen({super.key, required this.phone, required this.termsVersion});
  final String phone;
  final int termsVersion;

  @override
  State<CodeScreen> createState() => _CodeScreenState();
}

class _CodeScreenState extends State<CodeScreen> {
  final _code = TextEditingController();
  final _name = TextEditingController();
  final _referral = TextEditingController();
  bool _signup = false;
  List<dynamic> _heard = [];
  int? _heardId;

  Future<void> _verify() async {
    final s = context.read<Session>();
    final body = <String, dynamic>{'phone': widget.phone, 'code': _code.text.trim()};
    if (_signup) {
      body.addAll({
        'full_name': _name.text.trim(),
        'terms_version': widget.termsVersion,
        'device_type': Theme.of(context).platform == TargetPlatform.iOS ? 'ios' : 'android',
        if (_referral.text.trim().isNotEmpty) 'referral_code': _referral.text.trim(),
        if (_heardId != null) 'heard_about': _heardId,
      });
    }
    try {
      final r = Map<String, dynamic>.from(await s.api.post('auth/otp/verify/', body));
      await s.loggedInWith(r['token'], Map<String, dynamic>.from(r['user']));
      if (!mounted) return;
      final nav = Navigator.of(context);
      nav.popUntil((route) => route.isFirst);
      if (r['is_new'] == true) {
        nav.push(MaterialPageRoute(builder: (_) => const SetupScreen()));
      }
    } on ApiError catch (e) {
      if (e.code == 'signup_required') {
        final heard = await s.api.get('heard-about-options/');
        setState(() {
          _signup = true;
          _heard = heard as List;
        });
        return;
      }
      rethrow;
    }
  }

  Future<void> _resend() async {
    await context.read<Session>().api.post('auth/otp/request/', {'phone': widget.phone, 'device_id': 'app'});
    if (mounted) showInfo(context, 'بعتنا كود جديد.');
  }

  @override
  Widget build(BuildContext context) {
    final ready = _code.text.trim().length == 6 && (!_signup || _name.text.trim().isNotEmpty);
    return Scaffold(
      appBar: AppBar(title: Text(_signup ? 'حساب جديد' : 'الكود')),
      body: ListView(padding: const EdgeInsets.all(20), children: [
        Text('اكتب الكود اللي وصلك على ${widget.phone}', textAlign: TextAlign.center,
            style: const TextStyle(fontSize: 16, fontWeight: FontWeight.w600)),
        const SizedBox(height: 16),
        TextField(
          controller: _code,
          keyboardType: TextInputType.number,
          maxLength: 6,
          textAlign: TextAlign.center,
          textDirection: TextDirection.ltr,
          style: const TextStyle(fontSize: 26, letterSpacing: 10, fontWeight: FontWeight.w700),
          decoration: const InputDecoration(counterText: '', hintText: '______'),
          onChanged: (_) => setState(() {}),
        ),
        if (_signup) ...[
          const SectionTitle('أهلاً بيك في بريق'),
          TextField(
            controller: _name,
            decoration: const InputDecoration(labelText: 'اسمك'),
            onChanged: (_) => setState(() {}),
          ),
          const SizedBox(height: 12),
          TextField(controller: _referral, decoration: const InputDecoration(labelText: 'كود دعوة من صاحبك (لو معاك)')),
          const SizedBox(height: 12),
          DropdownButtonFormField<int>(
            initialValue: _heardId,
            decoration: const InputDecoration(labelText: 'عرفتنا منين؟ (اختياري)'),
            items: [for (final h in _heard) DropdownMenuItem(value: h['id'] as int, child: Text('${h['label']}'))],
            onChanged: (v) => setState(() => _heardId = v),
          ),
        ],
        const SizedBox(height: 20),
        BusyButton(label: _signup ? 'اعمل الحساب' : 'دخول', onPressed: ready ? _verify : null),
        TextButton(onPressed: _resend, child: const Text('موصلنيش كود، ابعت تاني')),
      ]),
    );
  }
}
