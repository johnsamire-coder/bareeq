import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../../core/format.dart';
import '../../core/session.dart';
import '../../core/theme.dart';
import '../../widgets/common.dart';
import '../booking/book_start_screen.dart';
import '../orders/order_detail_screen.dart';
import '../orders/rating_screen.dart';

class NotificationsScreen extends StatefulWidget {
  const NotificationsScreen({super.key, this.onChanged});
  final VoidCallback? onChanged;

  @override
  State<NotificationsScreen> createState() => _NotificationsScreenState();
}

class _NotificationsScreenState extends State<NotificationsScreen> {
  List<dynamic>? _items;
  Object? _error;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    try {
      final r = await context.read<Session>().api.get('notifications/');
      setState(() => (_items = r['results'] as List, _error = null));
    } catch (e) {
      setState(() => _error = e);
    }
  }

  Future<void> _open(Map n) async {
    final api = context.read<Session>().api;
    if (n['read_at'] == null) {
      await api.post('notifications/${n['id']}/read/');
      widget.onChanged?.call();
    }
    final data = Map<String, dynamic>.from(n['data'] ?? {});
    if (!mounted) return;
    Widget? target;
    switch (data['action']) {
      case 'rate':
        target = RatingScreen(orderId: data['order'] as int);
      case 'rebook':
      case 'book':
        target = const BookStartScreen(); // "book a new time" button
      default:
        if (data['order'] != null) {
          target = OrderDetailScreen(orderId: data['order'] as int);
        }
    }
    if (target != null) {
      await Navigator.push(context, MaterialPageRoute(builder: (_) => target!));
    }
    _load();
  }

  String? _actionLabel(Map n) {
    final a = (n['data'] ?? {})['action'];
    if (a == 'rate') return 'قيّم';
    if (a == 'rebook') return 'احجز ميعاد جديد';
    if (a == 'book') return 'احجز';
    return null;
  }

  @override
  Widget build(BuildContext context) {
    if (_error != null) return ErrorRetry(error: _error!, onRetry: _load);
    if (_items == null) return const Loading();
    if (_items!.isEmpty) {
      return const EmptyState(
        icon: Icons.notifications_none_rounded,
        text: 'مفيش إشعارات لسه.',
      );
    }
    return RefreshIndicator(
      onRefresh: _load,
      child: ListView.separated(
        padding: const EdgeInsets.all(16),
        itemCount: _items!.length,
        separatorBuilder: (_, _) => const SizedBox(height: 8),
        itemBuilder: (_, i) {
          final n = _items![i];
          final unread = n['read_at'] == null;
          final action = _actionLabel(n);
          final when = parseServerTime('${n['created_at']}');
          return Card(
            color: unread
                ? BrandColors.razaz.withValues(alpha: 0.45)
                : Colors.white,
            child: InkWell(
              borderRadius: BorderRadius.circular(16),
              onTap: () => _open(n),
              child: Padding(
                padding: const EdgeInsets.all(14),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Row(
                      children: [
                        if (unread)
                          const Padding(
                            padding: EdgeInsets.only(left: 6),
                            child: CircleAvatar(
                              radius: 4,
                              backgroundColor: BrandColors.mayya,
                            ),
                          ),
                        Expanded(
                          child: Text(
                            '${n['title']}',
                            style: const TextStyle(fontWeight: FontWeight.w700),
                          ),
                        ),
                        Muted('${dayLabel(when)} ${clock(when)}', size: 11),
                      ],
                    ),
                    const SizedBox(height: 4),
                    Text('${n['body']}'),
                    if (action != null) ...[
                      const SizedBox(height: 10),
                      SizedBox(
                        height: 40,
                        child: FilledButton(
                          onPressed: () => _open(n),
                          child: Text(action),
                        ),
                      ),
                    ],
                  ],
                ),
              ),
            ),
          );
        },
      ),
    );
  }
}
