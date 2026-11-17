import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../../core/session.dart';
import '../../widgets/common.dart';
import 'code_screen.dart';

class PhoneScreen extends StatefulWidget {
  const PhoneScreen({super.key, required this.termsVersion});
  final int termsVersion;

  @override
  State<PhoneScreen> createState() => _PhoneScreenState();
}

class _PhoneScreenState extends State<PhoneScreen> {
  final _phone = TextEditingController();

  Future<void> _send() async {
    final api = context.read<Session>().api;
    final r = await api.post('auth/otp/request/', {
      'phone': _phone.text.trim(),
      'device_id': 'app',
    });
    if (!mounted) return;
    await Navigator.of(context).push(
      MaterialPageRoute(
        builder: (_) => CodeScreen(
          phone: _phone.text.trim(),
          termsVersion: widget.termsVersion,
          demoCode: r is Map ? r['demo_code'] as String? : null,
        ),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('الدخول')),
      body: ListView(
        padding: const EdgeInsets.all(20),
        children: [
          Image.asset('assets/images/Bareeq-Symbol.png', height: 84),
          const SizedBox(height: 16),
          const Text(
            'اكتب رقم موبايلك',
            textAlign: TextAlign.center,
            style: TextStyle(fontSize: 20, fontWeight: FontWeight.w700),
          ),
          const SizedBox(height: 4),
          const Muted(
            'هنبعتلك كود من 6 أرقام. مفيش باسورد.',
            align: TextAlign.center,
          ),
          const SizedBox(height: 24),
          TextField(
            controller: _phone,
            keyboardType: TextInputType.phone,
            textDirection: TextDirection.ltr,
            textAlign: TextAlign.center,
            style: const TextStyle(fontSize: 20, letterSpacing: 1.5),
            decoration: const InputDecoration(hintText: '01X XXXX XXXX'),
            onChanged: (_) => setState(() {}),
          ),
          const SizedBox(height: 16),
          BusyButton(
            label: 'ابعت الكود',
            onPressed: _phone.text.trim().length >= 10 ? _send : null,
          ),
        ],
      ),
    );
  }
}
