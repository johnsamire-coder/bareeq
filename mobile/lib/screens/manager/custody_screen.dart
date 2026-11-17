import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../../core/format.dart';
import '../../core/session.dart';
import '../../core/theme.dart';
import '../../widgets/common.dart';
import 'pricing_screens.dart';

/// Technician custody (عهدة): cash shortages and overages from the daily
/// closings, what each technician paid back, and what is still on him.
class CustodyScreen extends StatefulWidget {
  const CustodyScreen({super.key});

  @override
  State<CustodyScreen> createState() => _CustodyScreenState();
}

class _CustodyScreenState extends State<CustodyScreen> {
  List<dynamic>? _rows;
  Object? _error;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    try {
      final r = await context.read<Session>().api.get(
        'manage/technician-custody/',
      );
      setState(() => (_rows = r as List, _error = null));
    } catch (e) {
      setState(() => _error = e);
    }
  }

  @override
  Widget build(BuildContext context) {
    final rows = _rows;
    final total = rows == null
        ? 0
        : rows.fold<int>(
            0,
            (s, r) => s + ((r['balance'] as int) > 0 ? r['balance'] as int : 0),
          );
    return Scaffold(
      appBar: AppBar(title: const Text('عهدة الفنيين')),
      body: _error != null
          ? ErrorRetry(error: _error!, onRetry: _load)
          : rows == null
          ? const Loading()
          : RefreshIndicator(
              onRefresh: _load,
              child: ListView(
                padding: const EdgeInsets.all(16),
                children: [
                  Card(
                    color: BrandColors.razaz,
                    child: Padding(
                      padding: const EdgeInsets.all(14),
                      child: KeyValue(
                        'إجمالي العهدة على الفنيين',
                        money(total),
                        bold: true,
                      ),
                    ),
                  ),
                  const SizedBox(height: 4),
                  const Muted(
                    'العهدة = العجز − الزيادة − اللي اتسدد. '
                    'بتتسجل لوحدها لما تستلم تقفيل فيه فرق.',
                  ),
                  const SizedBox(height: 8),
                  if (rows.isEmpty) const Muted('مفيش فنيين لسه.'),
                  for (final r in rows) _techCard(r as Map),
                ],
              ),
            ),
    );
  }

  Widget _techCard(Map r) {
    final balance = r['balance'] as int;
    return Card(
      margin: const EdgeInsets.only(bottom: 8),
      child: InkWell(
        borderRadius: BorderRadius.circular(16),
        onTap: () async {
          await Navigator.push(
            context,
            MaterialPageRoute(
              builder: (_) =>
                  CustodyDetailScreen(techId: r['technician'] as int),
            ),
          );
          _load();
        },
        child: Padding(
          padding: const EdgeInsets.all(14),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              KeyValue(
                '${r['technician_name']}',
                balanceText(balance),
                bold: true,
                color: balanceColor(balance),
              ),
              KeyValue('إجمالي العجز', money(r['shortages'])),
              KeyValue('إجمالي الزيادة', money(r['overages'])),
              KeyValue('اتسدد', money(r['settled'])),
            ],
          ),
        ),
      ),
    );
  }
}

String balanceText(int balance) => balance > 0
    ? 'عليه ${money(balance)}'
    : balance < 0
    ? 'ليه ${money(-balance)}'
    : 'مفيش عهدة';

Color? balanceColor(int balance) => balance > 0
    ? BrandColors.danger
    : balance < 0
    ? BrandColors.good
    : null;

/// One technician: totals, every line (newest first), and recording a payback.
class CustodyDetailScreen extends StatefulWidget {
  const CustodyDetailScreen({super.key, required this.techId});
  final int techId;

  @override
  State<CustodyDetailScreen> createState() => _CustodyDetailScreenState();
}

class _CustodyDetailScreenState extends State<CustodyDetailScreen> {
  Map<String, dynamic>? _d;
  Object? _error;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    try {
      final r = await context.read<Session>().api.get(
        'manage/technician-custody/',
        {'technician': '${widget.techId}'},
      );
      setState(() => (_d = Map<String, dynamic>.from(r), _error = null));
    } catch (e) {
      setState(() => _error = e);
    }
  }

  Future<void> _settle() async {
    final balance = _d!['balance'] as int;
    final amount = await askPounds(context, 'المبلغ اللي اتسدد', balance);
    if (amount == null || amount <= 0 || !mounted) return;
    final reason = await askText(
      context,
      'اتسدد إزاي؟',
      hint: 'مثلاً: دفعها كاش، أو اتخصمت من المرتب',
      ok: 'سجّل',
    );
    if (reason == null || !mounted) return;
    try {
      await context.read<Session>().api.post(
        'manage/technician-custody/settle/',
        {'technician': widget.techId, 'amount': amount, 'reason': reason},
      );
      if (mounted) showInfo(context, 'اتسجل.');
      _load();
    } catch (e) {
      if (mounted) showError(context, e);
    }
  }

  @override
  Widget build(BuildContext context) {
    final d = _d;
    return Scaffold(
      appBar: AppBar(
        title: Text(d == null ? 'العهدة' : '${d['technician_name']}'),
      ),
      body: _error != null
          ? ErrorRetry(error: _error!, onRetry: _load)
          : d == null
          ? const Loading()
          : RefreshIndicator(
              onRefresh: _load,
              child: ListView(
                padding: const EdgeInsets.all(16),
                children: [
                  Card(
                    child: Padding(
                      padding: const EdgeInsets.all(14),
                      child: Column(
                        children: [
                          KeyValue(
                            'العهدة دلوقتي',
                            balanceText(d['balance'] as int),
                            bold: true,
                            color: balanceColor(d['balance'] as int),
                          ),
                          KeyValue('إجمالي العجز', money(d['shortages'])),
                          KeyValue('إجمالي الزيادة', money(d['overages'])),
                          KeyValue('اتسدد', money(d['settled'])),
                        ],
                      ),
                    ),
                  ),
                  const SizedBox(height: 10),
                  if ((d['balance'] as int) > 0)
                    BusyButton(
                      label: 'سجّل إن الفني سدد',
                      icon: Icons.payments_outlined,
                      onPressed: _settle,
                    ),
                  const SectionTitle('الحركات'),
                  if ((d['entries'] as List).isEmpty)
                    const Muted('مفيش حركات لسه.'),
                  for (final e in d['entries'] as List) _entry(e as Map),
                ],
              ),
            ),
    );
  }

  Widget _entry(Map e) {
    final kind = '${e['kind']}';
    final amount = e['amount'] as int;
    final when = parseServerTime('${e['created_at']}');
    return Card(
      margin: const EdgeInsets.only(bottom: 8),
      child: Padding(
        padding: const EdgeInsets.all(12),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            Row(
              children: [
                Pill(
                  '${e['kind_label']}',
                  color: kind == 'shortage'
                      ? const Color(0xFFFDE7E7)
                      : kind == 'overage'
                      ? const Color(0xFFE3F4E5)
                      : BrandColors.razaz,
                ),
                const SizedBox(width: 8),
                Expanded(
                  child: Text(
                    e['closing_date'] != null
                        ? 'تقفيل يوم ${e['closing_date']}'
                        : '${shortDate(when)} ${clock(when)}',
                  ),
                ),
                Text(
                  money(amount),
                  style: const TextStyle(fontWeight: FontWeight.w700),
                ),
              ],
            ),
            const SizedBox(height: 4),
            Muted('${e['note']} • ${e['created_by_name']}'),
          ],
        ),
      ),
    );
  }
}
