import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../core/format.dart';
import '../core/session.dart';
import '../core/theme.dart';
import '../widgets/common.dart';
import 'account/account_screen.dart';
import 'account/notifications_screen.dart';
import 'booking/book_start_screen.dart';
import 'orders/order_detail_screen.dart';
import 'orders/orders_screen.dart';
import 'orders/status.dart';

/// Customer app: Home, My orders, Notifications, My account.
class HomeScreen extends StatefulWidget {
  const HomeScreen({super.key});

  @override
  State<HomeScreen> createState() => _HomeScreenState();
}

class _HomeScreenState extends State<HomeScreen> {
  int _tab = 0;
  int _unread = 0;

  @override
  void initState() {
    super.initState();
    _refreshUnread();
  }

  Future<void> _refreshUnread() async {
    try {
      final r = await context.read<Session>().api.get('notifications/');
      if (mounted) setState(() => _unread = r['unread'] as int);
    } catch (_) {}
  }

  @override
  Widget build(BuildContext context) {
    const titles = ['', 'طلباتي', 'الإشعارات', 'حسابي'];
    final pages = [
      _HomeTab(onBooked: () => setState(() {})),
      const OrdersScreen(),
      NotificationsScreen(onChanged: _refreshUnread),
      const AccountScreen(),
    ];
    return Scaffold(
      appBar: _tab == 0
          ? null
          : AppBar(title: Text(titles[_tab]), automaticallyImplyLeading: false),
      body: SafeArea(child: IndexedStack(index: _tab, children: pages)),
      bottomNavigationBar: NavigationBar(
        selectedIndex: _tab,
        onDestinationSelected: (i) {
          setState(() => _tab = i);
          _refreshUnread();
        },
        destinations: [
          const NavigationDestination(icon: Icon(Icons.home_outlined), selectedIcon: Icon(Icons.home_rounded), label: 'الرئيسية'),
          const NavigationDestination(icon: Icon(Icons.receipt_long_outlined), selectedIcon: Icon(Icons.receipt_long), label: 'طلباتي'),
          NavigationDestination(
            icon: Badge(isLabelVisible: _unread > 0, label: Text('$_unread'), child: const Icon(Icons.notifications_outlined)),
            selectedIcon: const Icon(Icons.notifications_rounded),
            label: 'الإشعارات',
          ),
          const NavigationDestination(icon: Icon(Icons.person_outline), selectedIcon: Icon(Icons.person), label: 'حسابي'),
        ],
      ),
    );
  }
}

class _HomeTab extends StatefulWidget {
  const _HomeTab({required this.onBooked});
  final VoidCallback onBooked;

  @override
  State<_HomeTab> createState() => _HomeTabState();
}

class _HomeTabState extends State<_HomeTab> {
  Map<String, dynamic>? _next;

  @override
  void initState() {
    super.initState();
    _loadNext();
  }

  Future<void> _loadNext() async {
    try {
      final orders = await context.read<Session>().api.get('orders/') as List;
      const live = {'pending_payment', 'confirmed', 'on_the_way', 'arrived', 'in_progress'};
      final upcoming = orders.where((o) => live.contains(o['status'])).toList()
        ..sort((a, b) => '${a['scheduled_start']}'.compareTo('${b['scheduled_start']}'));
      if (mounted) setState(() => _next = upcoming.isEmpty ? null : Map<String, dynamic>.from(upcoming.first));
    } catch (_) {}
  }

  @override
  Widget build(BuildContext context) {
    final name = '${context.watch<Session>().user?['full_name'] ?? ''}'.split(' ').first;
    return RefreshIndicator(
      onRefresh: _loadNext,
      child: ListView(padding: const EdgeInsets.all(16), children: [
        Row(children: [
          Image.asset('assets/images/Bareeq-Logo-Horizontal-color.png', height: 40),
          const Spacer(),
        ]),
        const SizedBox(height: 18),
        Container(
          padding: const EdgeInsets.all(20),
          decoration: BoxDecoration(color: BrandColors.layl, borderRadius: BorderRadius.circular(20)),
          child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            Text('أهلاً $name', style: const TextStyle(color: Colors.white70, fontSize: 15)),
            const SizedBox(height: 4),
            const Text('عربيتك تتغسل وإنت في البيت', style: TextStyle(color: Colors.white, fontSize: 21, fontWeight: FontWeight.w800)),
            const SizedBox(height: 16),
            FilledButton.icon(
              onPressed: () async {
                await Navigator.push(context, MaterialPageRoute(builder: (_) => const BookStartScreen()));
                _loadNext();
              },
              icon: const Icon(Icons.local_car_wash_rounded),
              label: const Text('احجز غسلة'),
            ),
          ]),
        ),
        if (_next != null) ...[
          const SectionTitle('طلبك الجاي'),
          Card(
            child: ListTile(
              contentPadding: const EdgeInsets.symmetric(horizontal: 14, vertical: 6),
              title: Text(fullWhen(parseServerTime('${_next!['scheduled_start']}')), style: const TextStyle(fontWeight: FontWeight.w700)),
              subtitle: Padding(
                padding: const EdgeInsets.only(top: 4),
                child: Align(alignment: AlignmentDirectional.centerStart, child: statusPill(_next!)),
              ),
              trailing: const Icon(Icons.chevron_left),
              onTap: () async {
                await Navigator.push(context, MaterialPageRoute(builder: (_) => OrderDetailScreen(orderId: _next!['id'] as int)));
                _loadNext();
              },
            ),
          ),
        ],
        const SectionTitle('خدماتنا'),
        GridView.count(
          crossAxisCount: 4,
          shrinkWrap: true,
          physics: const NeverScrollableScrollPhysics(),
          childAspectRatio: 0.8,
          children: const [
            _ServiceBadge('exterior-wash', 'غسيل خارجي'),
            _ServiceBadge('interior-wash', 'غسيل داخلي'),
            _ServiceBadge('engine-wash', 'غسيل موتور'),
            _ServiceBadge('polish-protection', 'تلميع وحماية'),
            _ServiceBadge('exterior-detailing', 'ديتيلنج خارجي'),
            _ServiceBadge('interior-detailing', 'ديتيلنج داخلي'),
            _ServiceBadge('headlight-restoration', 'تلميع الفوانيس'),
            _ServiceBadge('oil-change', 'تغيير زيت'),
          ],
        ),
      ]),
    );
  }
}

class _ServiceBadge extends StatelessWidget {
  const _ServiceBadge(this.code, this.label);
  final String code, label;

  @override
  Widget build(BuildContext context) => Column(children: [
        Container(
          width: 58, height: 58,
          decoration: BoxDecoration(color: Colors.white, borderRadius: BorderRadius.circular(16), border: Border.all(color: BrandColors.line)),
          child: Center(child: ServiceIcon(code, size: 34)),
        ),
        const SizedBox(height: 4),
        Text(label, textAlign: TextAlign.center, style: const TextStyle(fontSize: 11)),
      ]);
}
