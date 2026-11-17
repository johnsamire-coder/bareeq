import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../../core/session.dart';
import '../../widgets/common.dart';
import '../../widgets/terms_text.dart';
import '../addresses/my_addresses_screen.dart';
import '../cars/my_cars_screen.dart';
import 'wallet_screen.dart';

class AccountScreen extends StatelessWidget {
  const AccountScreen({super.key});

  @override
  Widget build(BuildContext context) {
    final s = context.watch<Session>();
    Widget link(IconData icon, String label, Widget page) => Card(
          margin: const EdgeInsets.only(bottom: 8),
          child: ListTile(
            leading: Icon(icon),
            title: Text(label, style: const TextStyle(fontWeight: FontWeight.w600)),
            trailing: const Icon(Icons.chevron_left),
            onTap: () => Navigator.push(context, MaterialPageRoute(builder: (_) => page)),
          ),
        );
    return ListView(padding: const EdgeInsets.all(16), children: [
      Card(
        child: ListTile(
          leading: const CircleAvatar(child: Icon(Icons.person)),
          title: Text('${s.user?['full_name'] ?? ''}', style: const TextStyle(fontWeight: FontWeight.w700)),
          subtitle: Text('${s.user?['phone'] ?? ''}', textDirection: TextDirection.ltr, textAlign: TextAlign.right),
          trailing: IconButton(icon: const Icon(Icons.edit_outlined), onPressed: () => _editName(context, s)),
        ),
      ),
      const SizedBox(height: 12),
      link(Icons.directions_car_outlined, 'عربياتي', const MyCarsScreen()),
      link(Icons.location_on_outlined, 'عناويني', const MyAddressesScreen()),
      link(Icons.account_balance_wallet_outlined, 'المحفظة', const WalletScreen()),
      link(Icons.description_outlined, 'الشروط والأحكام', const _TermsPage()),
      const SizedBox(height: 12),
      OutlinedButton.icon(onPressed: s.logout, icon: const Icon(Icons.logout), label: const Text('تسجيل خروج')),
    ]);
  }

  Future<void> _editName(BuildContext context, Session s) async {
    final c = TextEditingController(text: '${s.user?['full_name'] ?? ''}');
    final ok = await showDialog<bool>(
      context: context,
      builder: (d) => AlertDialog(
        title: const Text('اسمك'),
        content: TextField(controller: c, autofocus: true),
        actions: [
          TextButton(onPressed: () => Navigator.pop(d, false), child: const Text('إلغاء')),
          FilledButton(onPressed: () => Navigator.pop(d, true), child: const Text('حفظ')),
        ],
      ),
    );
    if (ok == true && c.text.trim().isNotEmpty) {
      try {
        await s.api.patch('me/', {'full_name': c.text.trim()});
        await s.refreshMe();
      } catch (e) {
        if (context.mounted) showError(context, e);
      }
    }
  }
}

class _TermsPage extends StatelessWidget {
  const _TermsPage();

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('الشروط والأحكام')),
      body: FutureBuilder(
        future: context.read<Session>().api.get('terms/current/'),
        builder: (_, snap) => snap.hasData
            ? SingleChildScrollView(padding: const EdgeInsets.all(18), child: TermsText('${(snap.data as Map)['text']}'))
            : const Loading(),
      ),
    );
  }
}
