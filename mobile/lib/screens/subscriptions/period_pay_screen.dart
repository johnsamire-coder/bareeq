import 'dart:typed_data';

import 'package:flutter/material.dart';
import 'package:image_picker/image_picker.dart';
import 'package:provider/provider.dart';

import '../../core/format.dart';
import '../../core/session.dart';
import '../../core/theme.dart';
import '../../widgets/common.dart';
import '../booking/pay_online_screen.dart';

/// Paying a month of a subscription: in advance, card or InstaPay (no cash),
/// with part from the wallet.
class PeriodPayScreen extends StatefulWidget {
  const PeriodPayScreen({super.key, required this.period});
  final Map<String, dynamic> period;

  @override
  State<PeriodPayScreen> createState() => _PeriodPayScreenState();
}

class _PeriodPayScreenState extends State<PeriodPayScreen> {
  Map<String, dynamic>? _info;
  String _method = 'card';
  bool _useWallet = false;
  Uint8List? _proof;

  Map<String, dynamic> get p => widget.period;

  @override
  void initState() {
    super.initState();
    context.read<Session>().api.get('payment-info/').then((i) {
      setState(() {
        _info = Map<String, dynamic>.from(i);
        if (_info!['card_payment_enabled'] != true) _method = 'instapay';
      });
    });
  }

  int get _walletMax {
    if (_info == null) return 0;
    final price = p['price'] as int;
    final pct = _info!['wallet_max_order_share_percent'] as int;
    final balance = (_info!['wallet_balance'] ?? 0) as int;
    final max = price * pct ~/ 100 ~/ 100 * 100;
    return (balance < max ? balance : max) ~/ 100 * 100;
  }

  int get _wallet => _useWallet ? _walletMax : 0;

  Future<void> _pay() async {
    final api = context.read<Session>().api;
    if (_method == 'card') {
      final r = await api.post('subscription-periods/${p['id']}/pay-online/', {
        'wallet_amount': _wallet,
      });
      if (!mounted) return;
      final paid = await Navigator.push<bool>(
        context,
        MaterialPageRoute(
          builder: (_) =>
              PayOnlineScreen(payment: Map<String, dynamic>.from(r)),
        ),
      );
      if (paid == true && mounted) {
        showInfo(context, 'اشتراكك اتأكد.');
        Navigator.pop(context);
      }
      return;
    }
    await api.upload(
      'subscription-periods/${p['id']}/pay-instapay/',
      {'wallet_amount': '$_wallet'},
      'proof',
      _proof!,
      'proof.jpg',
    );
    if (!mounted) return;
    showInfo(context, 'استلمنا التحويل، ومواعيدك اتأكدت.');
    Navigator.pop(context);
  }

  @override
  Widget build(BuildContext context) {
    final price = p['price'] as int;
    final due = price - _wallet;
    return Scaffold(
      appBar: AppBar(title: const Text('دفع الاشتراك')),
      body: _info == null
          ? const Loading()
          : ListView(
              padding: const EdgeInsets.all(16),
              children: [
                Card(
                  child: Padding(
                    padding: const EdgeInsets.all(14),
                    child: Column(
                      children: [
                        KeyValue('من', '${p['start_date']}'),
                        KeyValue('لحد', '${p['end_date']}'),
                        KeyValue(
                          'عدد الزيارات',
                          '${(p['visits'] as List).length}',
                        ),
                        KeyValue('السعر العادي', money(p['normal_price'])),
                        KeyValue('سعر الاشتراك', money(price), bold: true),
                      ],
                    ),
                  ),
                ),
                if (p['hold_expires_at'] != null)
                  Muted(
                    'المواعيد محجوزالك لحد ${clock(parseServerTime('${p['hold_expires_at']}'))}. كمّل الدفع قبلها.',
                  ),
                if (_walletMax > 0)
                  SwitchListTile(
                    value: _useWallet,
                    onChanged: (v) => setState(() => _useWallet = v),
                    title: Text('ادفع ${money(_walletMax)} من المحفظة'),
                  ),
                const SectionTitle('طريقة الدفع'),
                Card(
                  child: RadioGroup<String>(
                    groupValue: _method,
                    onChanged: (v) => setState(() => _method = v!),
                    child: Column(
                      children: [
                        if (_info!['card_payment_enabled'] == true) ...[
                          const RadioListTile<String>(
                            value: 'card',
                            title: Text('كارت أو محفظة موبايل'),
                          ),
                          const Divider(height: 1, color: BrandColors.line),
                        ],
                        const RadioListTile<String>(
                          value: 'instapay',
                          title: Text('InstaPay'),
                          subtitle: Text('حوّل وارفع صورة التحويل'),
                        ),
                      ],
                    ),
                  ),
                ),
                if (_method == 'instapay') ...[
                  const SizedBox(height: 8),
                  Muted(
                    'حوّل ${money(due)} على: ${_info!['instapay_details']}',
                  ),
                  const SizedBox(height: 8),
                  OutlinedButton.icon(
                    onPressed: () async {
                      final f = await ImagePicker().pickImage(
                        source: ImageSource.gallery,
                        maxWidth: 1600,
                      );
                      if (f != null) {
                        final b = await f.readAsBytes();
                        setState(() => _proof = b);
                      }
                    },
                    icon: Icon(
                      _proof == null ? Icons.upload_file : Icons.check_circle,
                    ),
                    label: Text(
                      _proof == null
                          ? 'ارفع صورة التحويل'
                          : 'اترفعت. غيّر الصورة',
                    ),
                  ),
                ],
                const SizedBox(height: 12),
                KeyValue('هتدفع', money(due), bold: true),
                const SizedBox(height: 12),
                BusyButton(
                  label: 'ادفع',
                  onPressed: _method == 'instapay' && _proof == null
                      ? null
                      : _pay,
                ),
                const SizedBox(height: 8),
                const Muted(
                  'الكاش مش متاح للاشتراك. زيارات الاشتراك مبتاخدش كاش باك ولا كوبونات.',
                ),
              ],
            ),
    );
  }
}
