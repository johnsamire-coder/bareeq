import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../../core/format.dart';
import '../../core/session.dart';
import '../../widgets/common.dart';
import 'order_detail_screen.dart';
import 'status.dart';

class OrdersScreen extends StatefulWidget {
  const OrdersScreen({super.key});

  @override
  State<OrdersScreen> createState() => OrdersScreenState();
}

class OrdersScreenState extends State<OrdersScreen> {
  List<dynamic>? _orders;
  Object? _error;

  @override
  void initState() {
    super.initState();
    load();
  }

  Future<void> load() async {
    try {
      final r = await context.read<Session>().api.get('orders/');
      setState(() => (_orders = (r as List).where((o) => o['status'] != 'expired').toList(), _error = null));
    } catch (e) {
      setState(() => _error = e);
    }
  }

  @override
  Widget build(BuildContext context) {
    if (_error != null) return ErrorRetry(error: _error!, onRetry: load);
    if (_orders == null) return const Loading();
    if (_orders!.isEmpty) return const EmptyState(icon: Icons.receipt_long_outlined, text: 'لسه معملتش طلبات.');
    return RefreshIndicator(
      onRefresh: load,
      child: ListView.separated(
        padding: const EdgeInsets.all(16),
        itemCount: _orders!.length,
        separatorBuilder: (_, _) => const SizedBox(height: 10),
        itemBuilder: (_, i) {
          final o = _orders![i];
          final cars = (o['items'] as List).map((x) => x['car_name']).join('، ');
          return Card(
            child: ListTile(
              contentPadding: const EdgeInsets.symmetric(horizontal: 14, vertical: 6),
              title: Text(fullWhen(parseServerTime('${o['scheduled_start']}')), style: const TextStyle(fontWeight: FontWeight.w700)),
              subtitle: Padding(
                padding: const EdgeInsets.only(top: 4),
                child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                  Text(cars),
                  const SizedBox(height: 4),
                  statusPill(o),
                ]),
              ),
              trailing: Text(money(o['amount_due']), style: const TextStyle(fontWeight: FontWeight.w700)),
              onTap: () async {
                await Navigator.push(context, MaterialPageRoute(builder: (_) => OrderDetailScreen(orderId: o['id'] as int)));
                load();
              },
            ),
          );
        },
      ),
    );
  }
}
