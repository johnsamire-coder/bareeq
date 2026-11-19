import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../../core/api.dart';
import '../../core/format.dart';
import '../../core/links.dart';
import '../../core/session.dart';
import '../../core/theme.dart';
import '../../widgets/common.dart';
import '../../widgets/photo_grid.dart';
import '../orders/status.dart';

/// One order for the manager: who/where/what, money (revenue next to what was
/// really collected), photos, move to another technician, cancel by the company.
class ManagerOrderScreen extends StatefulWidget {
  const ManagerOrderScreen({super.key, required this.orderId});
  final int orderId;

  @override
  State<ManagerOrderScreen> createState() => _ManagerOrderScreenState();
}

class _ManagerOrderScreenState extends State<ManagerOrderScreen> {
  Map<String, dynamic>? _o;
  List<dynamic> _photos = [];
  Object? _error;

  Api get _api => context.read<Session>().api;

  @override
  void initState() {
    super.initState();
    _load();
  }

  bool get _supervisor => context.read<Session>().role == 'supervisor';

  Future<void> _load() async {
    try {
      // A supervisor has no money screens: the plain order instead.
      final o = Map<String, dynamic>.from(
        await _api.get(
          _supervisor
              ? 'manage/orders/${widget.orderId}/'
              : 'manage/orders/${widget.orderId}/money/',
        ),
      );
      final photos =
          await _api.get('manage/orders/${widget.orderId}/photos/') as List;
      setState(() => (_o = o, _photos = photos, _error = null));
    } catch (e) {
      setState(() => _error = e);
    }
  }

  Future<void> _move() async {
    final techs =
        (await _api.get(
                  _supervisor ? 'manage/zone-technicians/' : 'technicians/',
                )
                as List)
            .where(
              (t) => t['is_active'] != false && t['id'] != _o!['technician'],
            )
            .toList();
    if (!mounted) return;
    final t = await showModalBottomSheet<Map>(
      context: context,
      builder: (c) => SafeArea(
        child: ListView(
          shrinkWrap: true,
          children: [
            const Padding(
              padding: EdgeInsets.all(16),
              child: Text(
                'انقل لفني تاني',
                style: TextStyle(fontSize: 17, fontWeight: FontWeight.w700),
              ),
            ),
            for (final t in techs)
              ListTile(
                leading: const Icon(Icons.engineering_outlined),
                title: Text('${t['full_name']}'),
                onTap: () => Navigator.pop(c, t),
              ),
          ],
        ),
      ),
    );
    if (t == null) return;
    try {
      await _api.post('manage/orders/${widget.orderId}/reassign/', {
        'technician': t['id'],
      });
    } on ApiError catch (e) {
      if (e.code != 'technician_not_available' || !mounted || _supervisor) {
        rethrow;
      }
      final force = await confirmDialog(
        context,
        'الفني مش فاضي',
        '${e.message}\nتنقله برضه؟',
        yes: 'انقل برضه',
      );
      if (!force) return;
      await _api.post('manage/orders/${widget.orderId}/reassign/', {
        'technician': t['id'],
        'force': true,
      });
    }
    if (mounted) {
      showInfo(context, 'الطلب اتنقل لـ ${t['full_name']}، والعميل اتبلغ.');
    }
    _load();
  }

  Future<void> _cancel() async {
    final reason = await askText(
      context,
      'إلغاء من الشركة',
      hint: 'السبب (العميل هيشوفه)',
      ok: 'ألغي الطلب',
    );
    if (reason == null) return;
    await _api.post('manage/orders/${widget.orderId}/cancel/', {
      'reason': reason,
    });
    _load();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: Text('طلب ${widget.orderId}')),
      body: _error != null
          ? ErrorRetry(error: _error!, onRetry: _load)
          : _o == null
          ? const Loading()
          : RefreshIndicator(onRefresh: _load, child: _body()),
    );
  }

  Widget _body() {
    final o = _o!;
    final status = '${o['status']}';
    final a = o['address_details'] as Map;
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
                        fullWhen(parseServerTime('${o['scheduled_start']}')),
                        style: const TextStyle(
                          fontSize: 16,
                          fontWeight: FontWeight.w800,
                        ),
                      ),
                    ),
                    statusPill(o),
                  ],
                ),
                const SizedBox(height: 6),
                Text('${o['customer_name']} • ${o['customer_phone']}'),
                Muted(
                  [
                    o['zone_name'],
                    a['street'],
                    'عمارة ${a['building']}',
                  ].where((x) => '${x ?? ''}'.isNotEmpty).join(' • '),
                ),
                Muted('الفني: ${o['technician_name'] ?? '-'}'),
                if ('${o['cancel_reason'] ?? ''}'.isNotEmpty)
                  Muted('سبب الإلغاء: ${o['cancel_reason']}'),
                const SizedBox(height: 8),
                OutlinedButton.icon(
                  onPressed: () => callPhone('${o['customer_phone']}'),
                  icon: const Icon(Icons.call_outlined),
                  label: const Text('كلّم العميل'),
                ),
              ],
            ),
          ),
        ),
        const SectionTitle('الشغل'),
        Card(
          child: Padding(
            padding: const EdgeInsets.all(14),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                for (final item in o['items'] as List) ...[
                  Text(
                    '${item['car_name']} • ${item['car_color']}',
                    style: const TextStyle(fontWeight: FontWeight.w700),
                  ),
                  for (final line in item['quote']['lines'] as List)
                    KeyValue('${line['name']}', money(line['price'])),
                ],
              ],
            ),
          ),
        ),
        if (!_supervisor) const SectionTitle('الفلوس'),
        if (!_supervisor)
          Card(
            child: Padding(
              padding: const EdgeInsets.all(14),
              child: Column(
                children: [
                  KeyValue('الإيراد', money(o['revenue']), bold: true),
                  KeyValue(
                    'اتحصّل فعلاً (كاش + InstaPay)',
                    money(o['collected']),
                  ),
                  KeyValue('من المحفظة', money(o['wallet_used'])),
                  if ((o['uncollected'] as int) > 0)
                    KeyValue(
                      'لسه متحصّلش',
                      money(o['uncollected']),
                      color: BrandColors.danger,
                    ),
                  const Divider(color: BrandColors.line),
                  KeyValue('الزيت', money(o['oil_total'])),
                  KeyValue('الخامات', money(o['materials_cost'])),
                  KeyValue('هامش الغسلة', money(o['wash_margin']), bold: true),
                  const Muted('هامش الغسلة مش داخل فيه أجر الفني ولا البنزين.'),
                ],
              ),
            ),
          ),
        if (_photos.isNotEmpty) ...[
          const SectionTitle('صور قبل وبعد'),
          PhotoGrid(photos: _photos),
        ],
        const SizedBox(height: 16),
        if (status == 'pending_payment' || status == 'confirmed')
          BusyButton(
            label: 'انقل لفني تاني',
            outlined: true,
            icon: Icons.swap_horiz,
            onPressed: _move,
          ),
        const SizedBox(height: 8),
        if (!_supervisor &&
            {
              'pending_payment',
              'confirmed',
              'on_the_way',
              'arrived',
            }.contains(status))
          BusyButton(
            label: 'إلغاء من الشركة',
            outlined: true,
            icon: Icons.cancel_outlined,
            onPressed: _cancel,
          ),
      ],
    );
  }
}
