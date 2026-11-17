import 'package:flutter/material.dart';

import '../../core/format.dart';
import '../../core/theme.dart';
import '../../widgets/common.dart';
import '../orders/order_detail_screen.dart';

class BookedScreen extends StatelessWidget {
  const BookedScreen({super.key, required this.order});
  final Map<String, dynamic> order;

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: SafeArea(
        child: ListView(padding: const EdgeInsets.all(24), children: [
          const SizedBox(height: 40),
          const CircleAvatar(radius: 40, backgroundColor: Color(0xFFE3F4E5), child: Icon(Icons.check_rounded, size: 46, color: BrandColors.good)),
          const SizedBox(height: 16),
          const Text('الحجز اتأكد', textAlign: TextAlign.center, style: TextStyle(fontSize: 24, fontWeight: FontWeight.w800)),
          const SizedBox(height: 6),
          Text(fullWhen(parseServerTime('${order['scheduled_start']}')), textAlign: TextAlign.center, style: const TextStyle(fontSize: 16)),
          Muted('الفني: ${order['technician_name'] ?? '-'}', align: TextAlign.center),
          if (order['payment_method'] == 'instapay')
            const Padding(padding: EdgeInsets.only(top: 12), child: Muted('هنراجع صورة التحويل ونأكدها.', align: TextAlign.center)),
          const SizedBox(height: 28),
          FilledButton(
            onPressed: () => Navigator.of(context).pushReplacement(
                MaterialPageRoute(builder: (_) => OrderDetailScreen(orderId: order['id'] as int))),
            child: const Text('تفاصيل الطلب'),
          ),
          const SizedBox(height: 10),
          OutlinedButton(onPressed: () => Navigator.of(context).popUntil((r) => r.isFirst), child: const Text('الرئيسية')),
        ]),
      ),
    );
  }
}
