import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../../core/format.dart';
import '../../core/session.dart';
import '../../core/theme.dart';
import '../../widgets/common.dart';

class WalletScreen extends StatefulWidget {
  const WalletScreen({super.key});

  @override
  State<WalletScreen> createState() => _WalletScreenState();
}

class _WalletScreenState extends State<WalletScreen> {
  Map<String, dynamic>? _w;
  Object? _error;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    try {
      final w = await context.read<Session>().api.get('my-wallet/');
      setState(() => (_w = Map<String, dynamic>.from(w), _error = null));
    } catch (e) {
      setState(() => _error = e);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('المحفظة')),
      body: _error != null
          ? ErrorRetry(error: _error!, onRetry: _load)
          : _w == null
              ? const Loading()
              : ListView(padding: const EdgeInsets.all(16), children: [
                  Container(
                    padding: const EdgeInsets.all(20),
                    decoration: BoxDecoration(color: BrandColors.layl, borderRadius: BorderRadius.circular(20)),
                    child: Column(children: [
                      const Text('رصيدك', style: TextStyle(color: Colors.white70)),
                      Text(money(_w!['balance']), style: const TextStyle(color: Colors.white, fontSize: 32, fontWeight: FontWeight.w800)),
                      const SizedBox(height: 4),
                      const Text('رصيد هدايا بتستخدمه في الغسلات. مبيتسحبش كاش.', style: TextStyle(color: Colors.white70, fontSize: 12)),
                    ]),
                  ),
                  const SectionTitle('الحركات'),
                  if ((_w!['entries'] as List).isEmpty) const EmptyState(icon: Icons.account_balance_wallet_outlined, text: 'مفيش حركات لسه.'),
                  for (final e in _w!['entries'] as List)
                    Card(
                      margin: const EdgeInsets.only(bottom: 8),
                      child: ListTile(
                        title: Text('${e['kind_label']}', style: const TextStyle(fontWeight: FontWeight.w600)),
                        subtitle: Text([
                          shortDate(parseServerTime('${e['created_at']}')),
                          if ((e['amount'] as int) > 0 && e['expires_at'] != null) 'ينتهي ${shortDate(parseServerTime('${e['expires_at']}'))}',
                          if ('${e['note']}'.isNotEmpty) '${e['note']}',
                        ].join(' • ')),
                        trailing: Text(
                          '${(e['amount'] as int) > 0 ? '+' : ''}${money(e['amount'])}',
                          style: TextStyle(fontWeight: FontWeight.w700, color: (e['amount'] as int) > 0 ? BrandColors.good : BrandColors.layl),
                        ),
                      ),
                    ),
                ]),
    );
  }
}
