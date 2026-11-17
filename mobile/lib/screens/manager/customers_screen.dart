import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../../core/api.dart';
import '../../core/format.dart';
import '../../core/links.dart';
import '../../core/session.dart';
import '../../core/theme.dart';
import '../../widgets/common.dart';
import '../orders/status.dart';
import 'manager_order_screen.dart';
import 'pricing_screens.dart';

/// Search customers by name or phone.
class CustomersScreen extends StatefulWidget {
  const CustomersScreen({super.key});

  @override
  State<CustomersScreen> createState() => _CustomersScreenState();
}

class _CustomersScreenState extends State<CustomersScreen> {
  List<dynamic>? _rows;
  String _q = '';

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    final r = await context.read<Session>().api.get('manage/customers/', {
      'search': _q,
    });
    if (mounted) setState(() => _rows = r as List);
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('العملاء')),
      body: Column(
        children: [
          Padding(
            padding: const EdgeInsets.all(16),
            child: TextField(
              decoration: const InputDecoration(
                prefixIcon: Icon(Icons.search),
                hintText: 'الاسم أو رقم الموبايل',
              ),
              onChanged: (v) {
                _q = v;
                _load();
              },
            ),
          ),
          Expanded(
            child: _rows == null
                ? const Loading()
                : _rows!.isEmpty
                ? const EmptyState(
                    icon: Icons.person_search_outlined,
                    text: 'مفيش عملاء بالاسم ده.',
                  )
                : ListView(
                    padding: const EdgeInsets.symmetric(horizontal: 16),
                    children: [
                      for (final c in _rows!)
                        Card(
                          margin: const EdgeInsets.only(bottom: 8),
                          child: ListTile(
                            title: Text(
                              '${c['name']}',
                              style: const TextStyle(
                                fontWeight: FontWeight.w700,
                              ),
                            ),
                            subtitle: Text(
                              '${c['phone']} • ${c['completed_orders']} غسلة • دفع ${money(c['total_paid'])}',
                            ),
                            trailing: const Icon(Icons.chevron_left),
                            onTap: () => Navigator.push(
                              context,
                              MaterialPageRoute(
                                builder: (_) => CustomerProfileScreen(
                                  customerId: c['id'] as int,
                                ),
                              ),
                            ),
                          ),
                        ),
                    ],
                  ),
          ),
        ],
      ),
    );
  }
}

class CustomerProfileScreen extends StatefulWidget {
  const CustomerProfileScreen({super.key, required this.customerId});
  final int customerId;

  @override
  State<CustomerProfileScreen> createState() => _CustomerProfileScreenState();
}

class _CustomerProfileScreenState extends State<CustomerProfileScreen> {
  Map<String, dynamic>? _p;
  Object? _error;

  Api get _api => context.read<Session>().api;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    try {
      final p = await _api.get('manage/customers/${widget.customerId}/');
      setState(() => (_p = Map<String, dynamic>.from(p), _error = null));
    } catch (e) {
      setState(() => _error = e);
    }
  }

  Future<void> _credit() async {
    final amount = await askPounds(context, 'رصيد للمحفظة', 0);
    if (amount == null || amount <= 0 || !mounted) return;
    final note = await askText(context, 'السبب', hint: 'مثلاً: تعويض عن تأخير');
    if (note == null) return;
    await _api.post('manage/wallets/credit/', {
      'customer': widget.customerId,
      'amount': amount,
      'note': note,
    });
    _load();
  }

  Future<void> _waive(Map c) async {
    final reason = await askText(
      context,
      'إلغاء رسوم ${money(c['amount'])}',
      hint: 'السبب (بيتسجل باسمك)',
      ok: 'ألغي الرسوم',
    );
    if (reason == null) return;
    await _api.post('manage/customer-charges/${c['id']}/waive/', {
      'reason': reason,
    });
    _load();
  }

  Future<void> _note() async {
    final text = await askText(
      context,
      'ملاحظة على العميل',
      hint: 'العميل مش بيشوفها',
    );
    if (text == null) return;
    await _api.post('manage/customers/${widget.customerId}/notes/', {
      'text': text,
    });
    _load();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: Text('${_p?['name'] ?? 'العميل'}')),
      body: _error != null
          ? ErrorRetry(error: _error!, onRetry: _load)
          : _p == null
          ? const Loading()
          : RefreshIndicator(onRefresh: _load, child: _body()),
    );
  }

  Widget _body() {
    final p = _p!;
    final st = p['stats'] as Map;
    Future<void> safe(Future<void> Function() f) async {
      try {
        await f();
      } catch (e) {
        if (mounted) showError(context, e);
      }
    }

    return ListView(
      padding: const EdgeInsets.all(16),
      children: [
        Card(
          child: Padding(
            padding: const EdgeInsets.all(14),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  children: [
                    Expanded(
                      child: Text(
                        '${p['phone']}',
                        textDirection: TextDirection.ltr,
                        textAlign: TextAlign.right,
                        style: const TextStyle(
                          fontSize: 16,
                          fontWeight: FontWeight.w700,
                        ),
                      ),
                    ),
                    IconButton(
                      onPressed: () => callPhone('${p['phone']}'),
                      icon: const Icon(Icons.call_outlined),
                    ),
                  ],
                ),
                Muted(
                  'من ${shortDate(parseServerTime('${p['date_joined']}'))} • ${p['device']}'
                  '${p['heard_about'] != null ? ' • عرفنا من: ${p['heard_about']}' : ''}'
                  '${'${p['referral_code_entered']}'.isNotEmpty ? ' • كود دعوة: ${p['referral_code_entered']}' : ''}',
                ),
                const SizedBox(height: 8),
                Wrap(
                  spacing: 8,
                  runSpacing: 6,
                  children: [
                    Pill('${st['completed_orders']} غسلة'),
                    Pill('دفع ${money(st['total_paid'])}'),
                    if ((st['cancelled_orders'] as int) > 0)
                      Pill(
                        '${st['cancelled_orders']} إلغاء',
                        color: const Color(0xFFFDECEC),
                        textColor: BrandColors.danger,
                      ),
                  ],
                ),
              ],
            ),
          ),
        ),
        SectionTitle(
          'المحفظة: ${money(p['wallet_balance'])}',
          trailing: TextButton.icon(
            onPressed: () => safe(_credit),
            icon: const Icon(Icons.add),
            label: const Text('ضيف رصيد'),
          ),
        ),
        for (final e in (p['wallet_entries'] as List).take(5))
          KeyValue(
            '${e['kind_label']}${'${e['note']}'.isNotEmpty ? ' (${e['note']})' : ''}',
            money(e['amount']),
          ),
        if ((p['charges'] as List).isNotEmpty) ...[
          const SectionTitle('الرسوم'),
          for (final c in p['charges'] as List)
            Card(
              margin: const EdgeInsets.only(bottom: 8),
              child: ListTile(
                title: Text('${c['label']} • ${money(c['amount'])}'),
                subtitle: Text(
                  c['waived'] == true
                      ? 'اتلغت: ${c['waive_reason']}'
                      : (c['paid'] == true ? 'اتدفعت' : 'لسه متدفعتش'),
                ),
                trailing: c['waived'] == true || c['paid'] == true
                    ? null
                    : TextButton(
                        onPressed: () => safe(() => _waive(c)),
                        child: const Text('ألغيها'),
                      ),
              ),
            ),
        ],
        SectionTitle(
          'ملاحظات',
          trailing: TextButton.icon(
            onPressed: () => safe(_note),
            icon: const Icon(Icons.add),
            label: const Text('ملاحظة'),
          ),
        ),
        if ((p['notes'] as List).isEmpty) const Muted('مفيش.'),
        for (final n in p['notes'] as List)
          Muted(
            '• ${n['text']} (${n['by']}، ${shortDate(parseServerTime('${n['created_at']}'))})',
            size: 14,
          ),
        const SectionTitle('الطلبات'),
        for (final o in p['orders'] as List)
          Card(
            margin: const EdgeInsets.only(bottom: 8),
            child: ListTile(
              title: Text(fullWhen(parseServerTime('${o['scheduled_start']}'))),
              subtitle: Align(
                alignment: AlignmentDirectional.centerStart,
                child: statusPill(o),
              ),
              trailing: Text(
                money(o['amount_due']),
                style: const TextStyle(fontWeight: FontWeight.w700),
              ),
              onTap: () => Navigator.push(
                context,
                MaterialPageRoute(
                  builder: (_) => ManagerOrderScreen(orderId: o['id'] as int),
                ),
              ),
            ),
          ),
        if ((p['ratings'] as List).isNotEmpty) ...[
          const SectionTitle('تقييماته'),
          for (final r in p['ratings'] as List)
            Muted(
              '${'★' * (r['stars'] as int)}  طلب ${r['order']}${'${r['comment']}'.isNotEmpty ? ' • «${r['comment']}»' : ''}',
              size: 14,
            ),
        ],
      ],
    );
  }
}
