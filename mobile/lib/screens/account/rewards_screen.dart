import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:provider/provider.dart';
import 'package:url_launcher/url_launcher.dart';

import '../../core/format.dart';
import '../../core/session.dart';
import '../../core/theme.dart';
import '../../widgets/common.dart';

/// «مكافآتي»: wash card progress, the invite code, and cashback.
class RewardsScreen extends StatefulWidget {
  const RewardsScreen({super.key});

  @override
  State<RewardsScreen> createState() => _RewardsScreenState();
}

class _RewardsScreenState extends State<RewardsScreen> {
  Map<String, dynamic>? _r;
  Object? _error;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    try {
      final r = await context.read<Session>().api.get('my-rewards/');
      setState(() => (_r = Map<String, dynamic>.from(r), _error = null));
    } catch (e) {
      setState(() => _error = e);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('مكافآتي')),
      body: _error != null
          ? ErrorRetry(error: _error!, onRetry: _load)
          : _r == null
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
                        'رصيد محفظتك',
                        money(_r!['wallet_balance']),
                        bold: true,
                      ),
                    ),
                  ),
                  if (_r!['wash_card']['enabled'] == true)
                    _washCard(_r!['wash_card'] as Map),
                  if (_r!['referral']['enabled'] == true)
                    _referral(_r!['referral'] as Map),
                  if (_r!['cashback']['enabled'] == true)
                    _cashback(_r!['cashback'] as Map),
                ],
              ),
            ),
    );
  }

  Widget _washCard(Map w) {
    final n = w['every_n'] as int;
    final done = w['done'] as int;
    final pct = w['reward_percent'] as int;
    final reward = pct >= 100 ? 'ببلاش' : 'بخصم $pct%';
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        const SectionTitle('كارت الغسيل'),
        Card(
          child: Padding(
            padding: const EdgeInsets.all(14),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                Wrap(
                  spacing: 8,
                  runSpacing: 8,
                  alignment: WrapAlignment.center,
                  children: [
                    for (var i = 0; i < n; i++)
                      CircleAvatar(
                        radius: 18,
                        backgroundColor: i < done
                            ? BrandColors.mayya
                            : BrandColors.line,
                        child: Icon(
                          Icons.local_car_wash,
                          size: 18,
                          color: i < done ? Colors.white : BrandColors.muted,
                        ),
                      ),
                    const CircleAvatar(
                      radius: 18,
                      backgroundColor: BrandColors.lamaa,
                      child: Icon(
                        Icons.star,
                        size: 18,
                        color: BrandColors.layl,
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: 10),
                Text(
                  w['next_is_reward'] == true
                      ? 'طلبك الجاي $reward على الخدمات 🎉'
                      : 'فاضلك ${n - done} من $n، والطلب اللي بعدهم $reward.',
                  textAlign: TextAlign.center,
                  style: const TextStyle(fontWeight: FontWeight.w700),
                ),
                const SizedBox(height: 4),
                const Muted(
                  'كل طلب بيتحسب مرة واحدة حتى لو فيه كذا عربية.',
                  align: TextAlign.center,
                ),
              ],
            ),
          ),
        ),
      ],
    );
  }

  Widget _referral(Map r) {
    final code = '${r['code']}';
    final gift = money(r['new_customer_discount']);
    final mine = money(r['referrer_credit']);
    final text =
        'جرّب بريق لغسيل العربية في البيت. سجّل بكودي $code '
        'وخد خصم $gift على أول غسلة.';
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        const SectionTitle('ادعي صاحبك'),
        Card(
          child: Padding(
            padding: const EdgeInsets.all(14),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                Text(
                  'صاحبك ياخد $gift خصم على أول غسلة، وإنت تاخد $mine في محفظتك بعد ما يخلصها.',
                ),
                const SizedBox(height: 12),
                Container(
                  padding: const EdgeInsets.symmetric(vertical: 10),
                  decoration: BoxDecoration(
                    color: BrandColors.sahab,
                    borderRadius: BorderRadius.circular(12),
                    border: Border.all(color: BrandColors.line),
                  ),
                  child: SelectableText(
                    code,
                    textAlign: TextAlign.center,
                    style: const TextStyle(
                      fontSize: 24,
                      letterSpacing: 4,
                      fontWeight: FontWeight.w800,
                    ),
                  ),
                ),
                const SizedBox(height: 10),
                Row(
                  children: [
                    Expanded(
                      child: BusyButton(
                        label: 'ابعت على واتساب',
                        icon: Icons.share,
                        onPressed: () => launchUrl(
                          Uri.parse(
                            'https://wa.me/?text=${Uri.encodeComponent(text)}',
                          ),
                          mode: LaunchMode.externalApplication,
                        ),
                      ),
                    ),
                    const SizedBox(width: 8),
                    SizedBox(
                      width: 110,
                      child: BusyButton(
                        label: 'انسخ',
                        outlined: true,
                        onPressed: () async {
                          await Clipboard.setData(ClipboardData(text: code));
                          if (mounted) showInfo(context, 'الكود اتنسخ.');
                        },
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: 10),
                KeyValue('صحابك اللي سجلوا بكودك', '${r['invited']}'),
                KeyValue('اللي خلصوا أول غسلة', '${r['credited']}'),
                KeyValue('كسبت', money(r['earned']), bold: true),
              ],
            ),
          ),
        ),
      ],
    );
  }

  Widget _cashback(Map c) => Column(
    crossAxisAlignment: CrossAxisAlignment.stretch,
    children: [
      const SectionTitle('الكاش باك'),
      Card(
        child: Padding(
          padding: const EdgeInsets.all(14),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              Text(
                'كل غسلة بيرجعلك ${c['percent']}% من اللي دفعته كاش أو InstaPay في محفظتك.',
              ),
              KeyValue('كسبت لحد دلوقتي', money(c['earned']), bold: true),
            ],
          ),
        ),
      ),
    ],
  );
}
