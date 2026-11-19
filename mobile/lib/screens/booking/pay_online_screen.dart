import 'dart:async';

import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:url_launcher/url_launcher.dart';

import '../../core/format.dart';
import '../../core/session.dart';
import '../../core/theme.dart';
import '../../widgets/common.dart';

/// Card / mobile wallet: opens the payment company's page, then waits for the
/// company to tell our server (the app never decides «paid» by itself).
/// Pops with true when paid.
class PayOnlineScreen extends StatefulWidget {
  const PayOnlineScreen({super.key, required this.payment});
  final Map<String, dynamic> payment; // ref, amount, redirect_url

  @override
  State<PayOnlineScreen> createState() => _PayOnlineScreenState();
}

class _PayOnlineScreenState extends State<PayOnlineScreen> {
  String _status = 'created';
  Timer? _timer;

  @override
  void initState() {
    super.initState();
    _open();
    _timer = Timer.periodic(const Duration(seconds: 3), (_) => _check());
  }

  @override
  void dispose() {
    _timer?.cancel();
    super.dispose();
  }

  Future<void> _open() => launchUrl(
    Uri.parse('${widget.payment['redirect_url']}'),
    mode: LaunchMode.externalApplication,
  );

  Future<void> _check() async {
    try {
      final r = await context.read<Session>().api.get(
        'pay/${widget.payment['ref']}/',
      );
      if (!mounted) return;
      setState(() => _status = '${r['status']}');
      if (_status != 'created') _timer?.cancel();
      if (_status == 'paid') {
        await Future<void>.delayed(const Duration(milliseconds: 800));
        if (mounted) Navigator.pop(context, true);
      }
    } catch (_) {}
  }

  @override
  Widget build(BuildContext context) {
    final failed = _status == 'failed' || _status == 'late';
    return Scaffold(
      appBar: AppBar(title: const Text('الدفع بالكارت')),
      body: ListView(
        padding: const EdgeInsets.all(20),
        children: [
          Icon(
            _status == 'paid'
                ? Icons.check_circle
                : failed
                ? Icons.error_outline
                : Icons.credit_card,
            size: 72,
            color: _status == 'paid'
                ? BrandColors.good
                : failed
                ? BrandColors.danger
                : BrandColors.mayya,
          ),
          const SizedBox(height: 12),
          Text(
            _status == 'paid'
                ? 'الدفع تم'
                : _status == 'late'
                ? 'الدفع وصل بعد ما وقت الحجز خلص. الفلوس هترجعلك.'
                : failed
                ? 'الدفع مكملش. جرّب تاني أو اختار طريقة تانية.'
                : 'كمّل الدفع في الصفحة اللي اتفتحت (${money(widget.payment['amount'])})، وبعدين ارجع هنا.',
            textAlign: TextAlign.center,
            style: const TextStyle(fontSize: 17, fontWeight: FontWeight.w700),
          ),
          const SizedBox(height: 20),
          if (_status == 'created') ...[
            const Center(child: CircularProgressIndicator()),
            const SizedBox(height: 20),
            BusyButton(label: 'اتأكد دلوقتي', onPressed: _check),
            const SizedBox(height: 8),
            BusyButton(
              label: 'افتح صفحة الدفع تاني',
              outlined: true,
              onPressed: _open,
            ),
          ] else if (failed)
            BusyButton(
              label: 'رجوع',
              onPressed: () async => Navigator.pop(context, false),
            ),
        ],
      ),
    );
  }
}
