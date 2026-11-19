import 'dart:async';
import 'dart:typed_data';

import 'package:flutter/material.dart';
import 'package:image_picker/image_picker.dart';
import 'package:provider/provider.dart';

import '../../core/format.dart';
import '../../core/session.dart';
import '../../core/theme.dart';
import '../../widgets/common.dart';
import 'booked_screen.dart';

/// Booking step 4: the time is held for a few minutes while the customer pays.
/// Cash to the technician, or InstaPay with the transfer screenshot; up to the
/// allowed % from the wallet (whole pounds).
class CheckoutScreen extends StatefulWidget {
  const CheckoutScreen({super.key, required this.order});
  final Map<String, dynamic> order;

  @override
  State<CheckoutScreen> createState() => _CheckoutScreenState();
}

class _CheckoutScreenState extends State<CheckoutScreen> {
  Map<String, dynamic>? _info;
  String _method = 'cash';
  bool _useWallet = false;
  Uint8List? _proof;
  Timer? _timer;
  Duration _left = Duration.zero;

  late Map<String, dynamic> o = widget.order;
  final _coupon = TextEditingController();

  @override
  void initState() {
    super.initState();
    _tick();
    _timer = Timer.periodic(const Duration(seconds: 1), (_) => _tick());
    context
        .read<Session>()
        .api
        .get('payment-info/')
        .then((i) => setState(() => _info = Map<String, dynamic>.from(i)));
  }

  @override
  void dispose() {
    _timer?.cancel();
    super.dispose();
  }

  void _tick() {
    final until = o['hold_expires_at'] == null
        ? null
        : parseServerTime('${o['hold_expires_at']}');
    setState(
      () => _left = until == null
          ? Duration.zero
          : until.difference(DateTime.now()),
    );
  }

  int get _walletMax {
    if (_info == null) return 0;
    final due = o['amount_due'] as int;
    final pct = _info!['wallet_max_order_share_percent'] as int;
    final balance = (_info!['wallet_balance'] ?? 0) as int;
    final cap = due * pct ~/ 100;
    return ((balance < cap ? balance : cap) ~/ 100) * 100; // whole pounds
  }

  int get _wallet => _useWallet ? _walletMax : 0;

  Future<void> _pickProof() async {
    final f = await ImagePicker().pickImage(
      source: ImageSource.gallery,
      maxWidth: 1600,
    );
    if (f != null) {
      final b = await f.readAsBytes();
      setState(() => _proof = b);
    }
  }

  Future<void> _applyCoupon() async {
    final r = await context.read<Session>().api.post(
      'orders/${o['id']}/coupon/',
      {'code': _coupon.text.trim()},
    );
    setState(() => o = Map<String, dynamic>.from(r));
    if (mounted) {
      showInfo(context, 'الكود اتطبق: خصم ${money(o['extra_discount'])}');
    }
  }

  Future<void> _removeCoupon() async {
    final r = await context.read<Session>().api.delete(
      'orders/${o['id']}/coupon/',
    );
    setState(() => o = Map<String, dynamic>.from(r));
  }

  Future<void> _confirm() async {
    final api = context.read<Session>().api;
    final path = 'orders/${o['id']}/confirm/';
    final order = _method == 'instapay'
        ? await api.upload(
            path,
            {'payment_method': 'instapay', 'wallet_amount': '$_wallet'},
            'proof',
            _proof!,
            'proof.jpg',
          )
        : await api.post(path, {
            'payment_method': 'cash',
            'wallet_amount': _wallet,
          });
    if (!mounted) return;
    Navigator.of(context).pushAndRemoveUntil(
      MaterialPageRoute(
        builder: (_) => BookedScreen(order: Map<String, dynamic>.from(order)),
      ),
      (r) => r.isFirst,
    );
  }

  @override
  Widget build(BuildContext context) {
    final expired = _left.inSeconds <= 0;
    final mm = _left.inMinutes.toString(),
        ss = (_left.inSeconds % 60).toString().padLeft(2, '0');
    final due = o['amount_due'] as int;
    final ready = !expired && (_method == 'cash' || _proof != null);
    return Scaffold(
      appBar: AppBar(title: const Text('الدفع')),
      body: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          Container(
            padding: const EdgeInsets.all(12),
            decoration: BoxDecoration(
              color: expired ? const Color(0xFFFDECEC) : BrandColors.razaz,
              borderRadius: BorderRadius.circular(12),
            ),
            child: Text(
              expired
                  ? 'خلص وقت الحجز المؤقت. ارجع واختار الميعاد تاني.'
                  : 'الميعاد محجوزلك لمدة $mm:$ss دقيقة. كمّل الدفع قبلها.',
              textAlign: TextAlign.center,
              style: TextStyle(
                fontWeight: FontWeight.w700,
                color: expired ? BrandColors.danger : BrandColors.layl,
              ),
            ),
          ),
          const SectionTitle('الطلب'),
          Card(
            child: Padding(
              padding: const EdgeInsets.all(14),
              child: Column(
                children: [
                  KeyValue(
                    'الميعاد',
                    fullWhen(parseServerTime('${o['scheduled_start']}')),
                  ),
                  KeyValue('الفني', '${o['technician_name'] ?? '-'}'),
                  const Divider(color: BrandColors.line),
                  for (final item in o['items'] as List) ...[
                    Align(
                      alignment: AlignmentDirectional.centerStart,
                      child: Text(
                        '${item['car_name']}',
                        style: const TextStyle(fontWeight: FontWeight.w700),
                      ),
                    ),
                    for (final line in item['quote']['lines'] as List)
                      KeyValue('${line['name']}', money(line['price'])),
                    if (item['quote']['oil'] != null)
                      KeyValue(
                        'زيت: ${item['quote']['oil']['name']}',
                        money(item['quote']['oil']['price']),
                      ),
                  ],
                  if ((o['discount'] as int) > 0)
                    KeyValue(
                      'الخصم',
                      '- ${money(o['discount'])}',
                      color: BrandColors.good,
                    ),
                  if ((o['extra_discount'] as int) > 0)
                    KeyValue(
                      extraDiscountTitle(o),
                      '- ${money(o['extra_discount'])}',
                      color: BrandColors.good,
                    ),
                  if ((o['charges_total'] as int) > 0)
                    KeyValue(
                      'رسوم من طلب سابق',
                      money(o['charges_total']),
                      color: BrandColors.danger,
                    ),
                  const Divider(color: BrandColors.line),
                  KeyValue('الإجمالي', money(due), bold: true),
                ],
              ),
            ),
          ),
          const SectionTitle('كود خصم'),
          const Muted('الطلب بياخد خصم واحد بس جنب خصم الباقة: الأكبر.'),
          if (o['coupon_code'] == null)
            Row(
              children: [
                Expanded(
                  child: TextField(
                    controller: _coupon,
                    textDirection: TextDirection.ltr,
                    decoration: const InputDecoration(
                      hintText: 'BAREEQ20',
                      isDense: true,
                    ),
                  ),
                ),
                const SizedBox(width: 8),
                SizedBox(
                  width: 110,
                  child: BusyButton(
                    label: 'طبّق',
                    outlined: true,
                    onPressed: _applyCoupon,
                  ),
                ),
              ],
            )
          else
            Card(
              child: ListTile(
                leading: const Icon(
                  Icons.confirmation_number_outlined,
                  color: BrandColors.good,
                ),
                title: Text(
                  '${o['coupon_code']}',
                  textDirection: TextDirection.ltr,
                  textAlign: TextAlign.right,
                ),
                subtitle: Text('خصم ${money(o['extra_discount'])}'),
                trailing: TextButton(
                  onPressed: _removeCoupon,
                  child: const Text('شيله'),
                ),
              ),
            ),
          if (_walletMax > 0) ...[
            const SectionTitle('المحفظة'),
            Card(
              child: SwitchListTile(
                value: _useWallet,
                onChanged: (v) => setState(() => _useWallet = v),
                title: Text('ادفع ${money(_walletMax)} من المحفظة'),
                subtitle: Text(
                  'رصيدك ${money(_info!['wallet_balance'])}. أقصى حاجة ${_info!['wallet_max_order_share_percent']}% من الطلب.',
                ),
              ),
            ),
          ],
          const SectionTitle('طريقة الدفع'),
          Card(
            child: RadioGroup<String>(
              groupValue: _method,
              onChanged: (v) => setState(() => _method = v!),
              child: const Column(
                children: [
                  RadioListTile<String>(
                    value: 'cash',
                    title: Text('كاش للفني'),
                    subtitle: Text('بتدفع لما الشغل يخلص'),
                  ),
                  Divider(height: 1, color: BrandColors.line),
                  RadioListTile<String>(
                    value: 'instapay',
                    title: Text('InstaPay'),
                    subtitle: Text('حوّل وارفع صورة التحويل'),
                  ),
                ],
              ),
            ),
          ),
          if (_method == 'instapay') ...[
            const SizedBox(height: 10),
            Card(
              color: BrandColors.razaz,
              child: Padding(
                padding: const EdgeInsets.all(14),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      'حوّل ${money(due - _wallet)} على:',
                      style: const TextStyle(fontWeight: FontWeight.w700),
                    ),
                    const SizedBox(height: 4),
                    Text('${_info?['instapay_details'] ?? ''}'),
                  ],
                ),
              ),
            ),
            const SizedBox(height: 10),
            OutlinedButton.icon(
              onPressed: _pickProof,
              icon: Icon(
                _proof == null ? Icons.upload_file : Icons.check_circle,
                color: _proof == null ? null : BrandColors.good,
              ),
              label: Text(
                _proof == null ? 'ارفع صورة التحويل' : 'اترفعت. غيّر الصورة',
              ),
            ),
          ],
          const SizedBox(height: 12),
          KeyValue(
            _method == 'cash' ? 'هتدفع للفني' : 'هتحوّل',
            money(due - _wallet),
            bold: true,
          ),
          const SizedBox(height: 12),
          BusyButton(label: 'أكّد الحجز', onPressed: ready ? _confirm : null),
        ],
      ),
    );
  }
}
