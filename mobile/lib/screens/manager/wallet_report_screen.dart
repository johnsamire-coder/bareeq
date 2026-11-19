import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../../core/format.dart';
import '../../core/session.dart';
import '../../core/theme.dart';
import '../../widgets/common.dart';

/// Wallet report: what the company owes customers in gift balance now, and
/// what was credited / spent / expired in a month, by kind.
class WalletReportScreen extends StatefulWidget {
  const WalletReportScreen({super.key});

  @override
  State<WalletReportScreen> createState() => _WalletReportScreenState();
}

class _WalletReportScreenState extends State<WalletReportScreen> {
  DateTime _month = DateTime(DateTime.now().year, DateTime.now().month);
  Map<String, dynamic>? _r;
  Object? _error;

  @override
  void initState() {
    super.initState();
    _load();
  }

  String get _m => '${_month.year}-${_month.month.toString().padLeft(2, '0')}';

  Future<void> _load() async {
    try {
      final r = await context.read<Session>().api.get(
        'manage/reports/wallet/',
        {'month': _m},
      );
      setState(() => (_r = Map<String, dynamic>.from(r), _error = null));
    } catch (e) {
      setState(() => _error = e);
    }
  }

  void _shift(int months) {
    setState(() {
      _month = DateTime(_month.year, _month.month + months);
      _r = null;
    });
    _load();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('تقرير المحفظة')),
      body: _error != null
          ? ErrorRetry(error: _error!, onRetry: _load)
          : _r == null
          ? const Loading()
          : ListView(
              padding: const EdgeInsets.all(16),
              children: [
                Card(
                  color: BrandColors.razaz,
                  child: Padding(
                    padding: const EdgeInsets.all(14),
                    child: Column(
                      children: [
                        KeyValue(
                          'الرصيد المفتوح على الشركة دلوقتي',
                          money(_r!['liability_now']),
                          bold: true,
                        ),
                        const Muted(
                          'رصيد هدايا في محافظ العملاء لسه متصرفش ومنتهاش.',
                        ),
                      ],
                    ),
                  ),
                ),
                const SizedBox(height: 8),
                Row(
                  children: [
                    IconButton(
                      onPressed: () => _shift(-1),
                      icon: const Icon(Icons.chevron_right),
                    ),
                    Expanded(
                      child: Text(
                        'شهر ${_month.month}/${_month.year}',
                        textAlign: TextAlign.center,
                        style: const TextStyle(
                          fontSize: 16,
                          fontWeight: FontWeight.w700,
                        ),
                      ),
                    ),
                    IconButton(
                      onPressed: () => _shift(1),
                      icon: const Icon(Icons.chevron_left),
                    ),
                  ],
                ),
                Card(
                  child: Padding(
                    padding: const EdgeInsets.all(14),
                    child: Column(
                      children: [
                        for (final c in _r!['credited'] as List)
                          KeyValue('نزل: ${c['label']}', money(c['amount'])),
                        const Divider(color: BrandColors.line),
                        KeyValue(
                          'إجمالي اللي نزل',
                          money(_r!['credited_total']),
                          bold: true,
                        ),
                        KeyValue('اتصرف في طلبات', money(_r!['spent'])),
                        KeyValue('انتهت صلاحيته', money(_r!['expired'])),
                      ],
                    ),
                  ),
                ),
              ],
            ),
    );
  }
}
