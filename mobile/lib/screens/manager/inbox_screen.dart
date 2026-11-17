import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../../core/api.dart';
import '../../core/format.dart';
import '../../core/links.dart';
import '../../core/session.dart';
import '../../core/theme.dart';
import '../../widgets/common.dart';
import 'manager_order_screen.dart';

/// Everything waiting for the manager, with counts.
class InboxScreen extends StatefulWidget {
  const InboxScreen({super.key, this.onChanged});
  final VoidCallback? onChanged;

  @override
  State<InboxScreen> createState() => _InboxScreenState();
}

class _InboxScreenState extends State<InboxScreen> {
  Map<String, dynamic>? _c;
  Object? _error;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    try {
      final c = await context.read<Session>().api.get('manage/inbox/');
      setState(() => (_c = Map<String, dynamic>.from(c), _error = null));
      widget.onChanged?.call();
    } catch (e) {
      setState(() => _error = e);
    }
  }

  Future<void> _open(Widget page) async {
    await Navigator.push(context, MaterialPageRoute(builder: (_) => page));
    _load();
  }

  @override
  Widget build(BuildContext context) {
    if (_error != null) return ErrorRetry(error: _error!, onRetry: _load);
    if (_c == null) return const Loading();
    Widget row(IconData icon, String label, String key, Widget page) {
      final n = _c![key] as int;
      return Card(
        margin: const EdgeInsets.only(bottom: 8),
        child: ListTile(
          leading: Icon(
            icon,
            color: n > 0 ? BrandColors.mayya : BrandColors.muted,
          ),
          title: Text(
            label,
            style: const TextStyle(fontWeight: FontWeight.w600),
          ),
          trailing: n > 0
              ? Pill('$n', color: BrandColors.mayya, textColor: Colors.white)
              : const Muted('مفيش'),
          onTap: () => _open(page),
        ),
      );
    }

    return RefreshIndicator(
      onRefresh: _load,
      child: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          row(
            Icons.receipt_long_outlined,
            'تحويلات InstaPay محتاجة مراجعة',
            'instapay_to_review',
            const PaymentsReviewScreen(status: 'pending_review'),
          ),
          row(
            Icons.undo_rounded,
            'فلوس لازم ترجع لعملاء',
            'refunds_due',
            const PaymentsReviewScreen(status: 'refund_due'),
          ),
          row(
            Icons.payments_outlined,
            'تقفيلات الفنيين',
            'closings_to_confirm',
            const ClosingsReviewScreen(),
          ),
          row(
            Icons.star_half_rounded,
            'تقييمات وحشة',
            'bad_ratings',
            const BadRatingsScreen(),
          ),
          row(
            Icons.report_outlined,
            'بلاغات ضرر',
            'damage_reports',
            const DamageReportsScreen(),
          ),
        ],
      ),
    );
  }
}

/// Generic list screen for the inbox lists.
abstract class _ListScreen extends StatefulWidget {
  const _ListScreen({super.key});
  String get title;
  String get emptyText;
  Future<List<dynamic>> fetch(Api api);
  Widget item(BuildContext context, Api api, Map x, VoidCallback reload);

  @override
  State<_ListScreen> createState() => _ListScreenState();
}

class _ListScreenState extends State<_ListScreen> {
  List<dynamic>? _items;
  Object? _error;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    try {
      final items = await widget.fetch(context.read<Session>().api);
      setState(() => (_items = items, _error = null));
    } catch (e) {
      setState(() => _error = e);
    }
  }

  @override
  Widget build(BuildContext context) {
    final api = context.read<Session>().api;
    return Scaffold(
      appBar: AppBar(title: Text(widget.title)),
      body: _error != null
          ? ErrorRetry(error: _error!, onRetry: _load)
          : _items == null
          ? const Loading()
          : _items!.isEmpty
          ? EmptyState(icon: Icons.check_circle_outline, text: widget.emptyText)
          : RefreshIndicator(
              onRefresh: _load,
              child: ListView.separated(
                padding: const EdgeInsets.all(16),
                itemCount: _items!.length,
                separatorBuilder: (_, _) => const SizedBox(height: 10),
                itemBuilder: (c, i) => Card(
                  child: Padding(
                    padding: const EdgeInsets.all(14),
                    child: widget.item(c, api, _items![i], _load),
                  ),
                ),
              ),
            ),
    );
  }
}

Widget _orderLink(BuildContext context, int orderId) => TextButton.icon(
  onPressed: () => Navigator.push(
    context,
    MaterialPageRoute(builder: (_) => ManagerOrderScreen(orderId: orderId)),
  ),
  icon: const Icon(Icons.open_in_new, size: 18),
  label: Text('طلب $orderId'),
);

class PaymentsReviewScreen extends _ListScreen {
  const PaymentsReviewScreen({super.key, required this.status});
  final String status;

  @override
  String get title =>
      status == 'pending_review' ? 'مراجعة InstaPay' : 'فلوس ترجع لعملاء';
  @override
  String get emptyText => 'مفيش حاجة مستنية.';
  @override
  Future<List<dynamic>> fetch(Api api) async =>
      await api.get('manage/payments/', {'status': status}) as List;

  @override
  Widget item(BuildContext context, Api api, Map p, VoidCallback reload) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        KeyValue('${p['customer_name']}', money(p['amount']), bold: true),
        Muted(
          '${p['customer_phone']} • ${shortDate(parseServerTime('${p['created_at']}'))}',
        ),
        Align(
          alignment: AlignmentDirectional.centerStart,
          child: _orderLink(context, p['order'] as int),
        ),
        if (p['proof_url'] != null) ...[
          const SizedBox(height: 6),
          ServerImage(
            '${p['proof_url']}',
            loader: (path) => api.bytes(path),
            height: 220,
          ),
        ],
        const SizedBox(height: 10),
        if (status == 'pending_review')
          Row(
            children: [
              Expanded(
                child: BusyButton(
                  label: 'أكّد',
                  icon: Icons.check,
                  onPressed: () async {
                    await api.post('manage/payments/${p['id']}/approve/');
                    reload();
                  },
                ),
              ),
              const SizedBox(width: 8),
              Expanded(
                child: BusyButton(
                  label: 'ارفض',
                  outlined: true,
                  onPressed: () async {
                    final reason = await askText(
                      context,
                      'سبب الرفض',
                      hint: 'مثلاً: التحويل مش موجود',
                      ok: 'ارفض',
                    );
                    if (reason == null) return;
                    await api.post('manage/payments/${p['id']}/reject/', {
                      'reason': reason,
                    });
                    reload();
                  },
                ),
              ),
            ],
          )
        else
          BusyButton(
            label: 'رجّعت الفلوس للعميل',
            icon: Icons.check,
            onPressed: () async {
              await api.post('manage/payments/${p['id']}/refunded/');
              reload();
            },
          ),
        if (status == 'pending_review')
          const Padding(
            padding: EdgeInsets.only(top: 6),
            child: Muted('لو رفضت، الفني هيحصّل المبلغ كاش.'),
          ),
      ],
    );
  }
}

class ClosingsReviewScreen extends _ListScreen {
  const ClosingsReviewScreen({super.key});

  @override
  String get title => 'تقفيلات الفنيين';
  @override
  String get emptyText => 'مفيش تقفيلات مستنية.';
  @override
  Future<List<dynamic>> fetch(Api api) async =>
      await api.get('manage/daily-closings/', {'status': 'submitted'}) as List;

  @override
  Widget item(BuildContext context, Api api, Map c, VoidCallback reload) {
    final diff = c['difference'] as int;
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        KeyValue('${c['technician_name']}', '${c['date']}', bold: true),
        KeyValue('المفروض معاه', money(c['cash_expected'])),
        KeyValue('سلّم', money(c['cash_handed'])),
        KeyValue(
          'الفرق',
          money(diff),
          bold: true,
          color: diff < 0
              ? BrandColors.danger
              : (diff > 0 ? BrandColors.good : null),
        ),
        if ('${c['note']}'.isNotEmpty) Muted('ملاحظة الفني: ${c['note']}'),
        const SizedBox(height: 10),
        BusyButton(
          label: 'استلمت الفلوس',
          icon: Icons.check,
          onPressed: () async {
            await api.post('manage/daily-closings/${c['id']}/confirm/');
            reload();
          },
        ),
      ],
    );
  }
}

class BadRatingsScreen extends _ListScreen {
  const BadRatingsScreen({super.key});

  @override
  String get title => 'تقييمات وحشة';
  @override
  String get emptyText => 'مفيش تقييمات وحشة مستنية.';
  @override
  Future<List<dynamic>> fetch(Api api) async =>
      await api.get('manage/ratings/', {'bad': 1, 'unhandled': 1}) as List;

  @override
  Widget item(BuildContext context, Api api, Map r, VoidCallback reload) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        Row(
          children: [
            for (var i = 1; i <= 5; i++)
              Icon(
                i <= (r['stars'] as int)
                    ? Icons.star_rounded
                    : Icons.star_outline_rounded,
                color: BrandColors.lamaa,
                size: 22,
              ),
            const Spacer(),
            if (r['call_requested'] == true)
              const Pill(
                'طالب «كلمني»',
                color: Color(0xFFFDECEC),
                textColor: BrandColors.danger,
              ),
          ],
        ),
        const SizedBox(height: 6),
        Text(
          '${r['customer_name']} • الفني: ${r['technician_name']} • ${r['zone_name']}',
          style: const TextStyle(fontWeight: FontWeight.w600),
        ),
        if ((r['tag_names'] as List).isNotEmpty)
          Muted((r['tag_names'] as List).join('، ')),
        if ('${r['comment']}'.isNotEmpty)
          Padding(
            padding: const EdgeInsets.only(top: 4),
            child: Text('«${r['comment']}»'),
          ),
        for (final ph in r['photos'] as List)
          Padding(
            padding: const EdgeInsets.only(top: 6),
            child: ServerImage('$ph', loader: (p) => api.bytes(p)),
          ),
        Row(
          children: [
            _orderLink(context, r['order'] as int),
            const Spacer(),
            TextButton.icon(
              onPressed: () => callPhone('${r['customer_phone']}'),
              icon: const Icon(Icons.call_outlined),
              label: const Text('كلّمه'),
            ),
          ],
        ),
        BusyButton(
          label: 'اتحلت',
          icon: Icons.check,
          onPressed: () async {
            final note = await askText(
              context,
              'اتعمل إيه؟',
              hint: 'مثلاً: كلمناه واعتذرنا وعملنا غسلة ببلاش',
            );
            if (note == null) return;
            await api.post('manage/ratings/${r['id']}/handle/', {'note': note});
            reload();
          },
        ),
      ],
    );
  }
}

class DamageReportsScreen extends _ListScreen {
  const DamageReportsScreen({super.key});

  @override
  String get title => 'بلاغات الضرر';
  @override
  String get emptyText => 'مفيش بلاغات مفتوحة.';
  @override
  Future<List<dynamic>> fetch(Api api) async =>
      await api.get('manage/damage-reports/', {'status': 'open'}) as List;

  @override
  Widget item(BuildContext context, Api api, Map d, VoidCallback reload) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        Text(
          '${d['description']}',
          style: const TextStyle(fontWeight: FontWeight.w600),
        ),
        Muted(
          '${d['customer_phone']} • ${shortDate(parseServerTime('${d['created_at']}'))}',
        ),
        for (final ph in d['photos'] as List)
          Padding(
            padding: const EdgeInsets.only(top: 6),
            child: ServerImage('$ph', loader: (p) => api.bytes(p)),
          ),
        Align(
          alignment: AlignmentDirectional.centerStart,
          child: _orderLink(context, d['order'] as int),
        ),
        const Muted('افتح الطلب وقارن بصور قبل وبعد.'),
        const SizedBox(height: 8),
        BusyButton(
          label: 'اقفل البلاغ',
          icon: Icons.check,
          onPressed: () async {
            final note = await askText(
              context,
              'اتعمل إيه؟',
              hint: 'مثلاً: الخدش كان موجود في صور قبل',
            );
            if (note == null) return;
            await api.post('manage/damage-reports/${d['id']}/resolve/', {
              'note': note,
            });
            reload();
          },
        ),
      ],
    );
  }
}
