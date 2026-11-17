import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../../core/format.dart';
import '../../core/session.dart';
import '../../core/theme.dart';
import '../../widgets/common.dart';

/// End of day: cash collected per job, and how much the technician hands over.
class ClosingScreen extends StatefulWidget {
  const ClosingScreen({super.key});

  @override
  State<ClosingScreen> createState() => _ClosingScreenState();
}

class _ClosingScreenState extends State<ClosingScreen> {
  Map<String, dynamic>? _s;
  Object? _error;
  final _handed = TextEditingController();
  final _note = TextEditingController();
  final DateTime _day = DateTime.now();

  String get _iso => '${_day.year}-${_day.month.toString().padLeft(2, '0')}-${_day.day.toString().padLeft(2, '0')}';

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    try {
      final s = await context.read<Session>().api.get('technician/closing/', {'date': _iso});
      setState(() => (_s = Map<String, dynamic>.from(s), _error = null));
    } catch (e) {
      setState(() => _error = e);
    }
  }

  Future<void> _submit() async {
    final pounds = int.tryParse(_handed.text.trim());
    if (pounds == null) return;
    await context.read<Session>().api.post('technician/closing/', {'date': _iso, 'cash_handed': pounds * 100, 'note': _note.text.trim()});
    if (mounted) showInfo(context, 'التقفيل اتبعت للمدير.');
    _load();
  }

  @override
  Widget build(BuildContext context) {
    if (_error != null) return ErrorRetry(error: _error!, onRetry: _load);
    if (_s == null) return const Loading();
    final closing = _s!['closing'] as Map?;
    final confirmed = closing?['status'] == 'confirmed';
    return RefreshIndicator(
      onRefresh: _load,
      child: ListView(padding: const EdgeInsets.all(16), children: [
        Text('${dayLabel(_day)} ${shortDate(_day)}', style: const TextStyle(fontSize: 16, fontWeight: FontWeight.w700)),
        const SizedBox(height: 10),
        Card(
          child: Padding(
            padding: const EdgeInsets.all(14),
            child: Column(children: [
              for (final o in _s!['orders'] as List)
                KeyValue('طلب ${o['order']} (${clock(parseServerTime('${o['scheduled_start']}'))})', money(o['cash_collected'])),
              if ((_s!['orders'] as List).isEmpty) const Muted('مفيش طلبات خلصت النهارده.'),
              const Divider(color: BrandColors.line),
              KeyValue('الكاش اللي معاك', money(_s!['cash_collected']), bold: true),
              KeyValue('تكلفة الخامات', money(_s!['materials_cost'])),
            ]),
          ),
        ),
        if (closing != null) ...[
          const SizedBox(height: 10),
          Card(
            color: confirmed ? const Color(0xFFE3F4E5) : BrandColors.razaz,
            child: Padding(
              padding: const EdgeInsets.all(14),
              child: Column(children: [
                KeyValue('سلّمت', money(closing['cash_handed'])),
                KeyValue('الفرق', money(closing['difference']),
                    color: (closing['difference'] as int) < 0 ? BrandColors.danger : null),
                KeyValue('الحالة', confirmed ? 'المدير استلم' : 'مستني المدير', bold: true),
              ]),
            ),
          ),
        ],
        if (!confirmed) ...[
          const SectionTitle('سلّم الكاش'),
          TextField(controller: _handed, keyboardType: TextInputType.number,
              decoration: const InputDecoration(labelText: 'المبلغ اللي هتسلمه', suffixText: 'ج.م')),
          const SizedBox(height: 10),
          TextField(controller: _note, decoration: const InputDecoration(labelText: 'ملاحظة (لو فيه فرق)')),
          const SizedBox(height: 12),
          BusyButton(label: closing == null ? 'ابعت التقفيل' : 'عدّل التقفيل', onPressed: _submit),
        ],
      ]),
    );
  }
}
