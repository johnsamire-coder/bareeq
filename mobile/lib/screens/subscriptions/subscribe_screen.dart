import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../../core/format.dart';
import '../../core/session.dart';
import '../../core/theme.dart';
import '../../widgets/common.dart';
import '../booking/slots_screen.dart';
import 'period_pay_screen.dart';

/// Subscribe: car + address -> plan (price for this car and place) -> the
/// first visit's day and time (the same weekday and time every visit) -> pay.
class SubscribeScreen extends StatefulWidget {
  const SubscribeScreen({super.key});

  @override
  State<SubscribeScreen> createState() => _SubscribeScreenState();
}

class _SubscribeScreenState extends State<SubscribeScreen> {
  List<dynamic>? _cars, _addresses, _plans;
  int? _car, _address, _plan;
  Object? _error;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    try {
      final api = context.read<Session>().api;
      final cars = await api.get('my-cars/') as List;
      final addresses = await api.get('my-addresses/') as List;
      setState(() {
        _cars = cars;
        _addresses = addresses;
        _car ??= cars.isEmpty ? null : cars.first['id'] as int;
        _address ??= addresses.isEmpty ? null : addresses.first['id'] as int;
        _error = null;
      });
      _loadPlans();
    } catch (e) {
      setState(() => _error = e);
    }
  }

  Future<void> _loadPlans() async {
    if (_car == null || _address == null) return;
    final r = await context.read<Session>().api.get('subscription-plans/', {
      'car': _car,
      'address': _address,
    });
    setState(() {
      _plans = r as List;
      _plan = _plans!.isEmpty ? null : _plans!.first['id'] as int;
    });
  }

  Future<void> _next() async {
    final plan = _plans!.firstWhere((p) => p['id'] == _plan) as Map;
    final start = await Navigator.push<String>(
      context,
      MaterialPageRoute(
        builder: (_) => SlotsScreen(
          addressId: _address!,
          items: [
            {'car': _car, 'services': plan['service_ids']},
          ],
          pickLabel: 'ده ميعادي كل أسبوع',
        ),
      ),
    );
    if (start == null || !mounted) return;
    final sub = await context.read<Session>().api.post('my-subscriptions/', {
      'plan': _plan,
      'car': _car,
      'address': _address,
      'start': start,
    });
    if (!mounted) return;
    // Wait for the payment, then go back to the list (which reloads then).
    await Navigator.push(
      context,
      MaterialPageRoute(
        builder: (_) =>
            PeriodPayScreen(period: Map<String, dynamic>.from(sub['current'])),
      ),
    );
    if (mounted) Navigator.pop(context);
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('اشترك')),
      body: _error != null
          ? ErrorRetry(error: _error!, onRetry: _load)
          : _cars == null
          ? const Loading()
          : (_cars!.isEmpty || _addresses!.isEmpty)
          ? const EmptyState(
              icon: Icons.info_outline,
              text: 'ضيف عربية وعنوان الأول من «حسابي».',
            )
          : ListView(
              padding: const EdgeInsets.all(16),
              children: [
                DropdownButtonFormField<int>(
                  initialValue: _car,
                  decoration: const InputDecoration(labelText: 'العربية'),
                  items: [
                    for (final c in _cars!)
                      DropdownMenuItem(
                        value: c['id'] as int,
                        child: Text('${c['display_name'] ?? c['id']}'),
                      ),
                  ],
                  onChanged: (v) => setState(() {
                    _car = v;
                    _loadPlans();
                  }),
                ),
                const SizedBox(height: 10),
                DropdownButtonFormField<int>(
                  initialValue: _address,
                  decoration: const InputDecoration(labelText: 'العنوان'),
                  items: [
                    for (final a in _addresses!)
                      DropdownMenuItem(
                        value: a['id'] as int,
                        child: Text('${a['label']}'),
                      ),
                  ],
                  onChanged: (v) => setState(() {
                    _address = v;
                    _loadPlans();
                  }),
                ),
                const SectionTitle('الباقة'),
                if (_plans == null)
                  const Loading()
                else if (_plans!.isEmpty)
                  const Muted('مفيش باقات متاحة دلوقتي.')
                else
                  for (final p in _plans!) _planCard(p as Map),
                const SizedBox(height: 8),
                const Muted(
                  'هتختار يوم وساعة أول زيارة، والزيارات اللي بعدها في نفس اليوم والساعة كل أسبوع. '
                  'الاشتراك بيتدفع مقدّم بالكارت أو InstaPay.',
                ),
                const SizedBox(height: 12),
                BusyButton(
                  label: 'اختار الميعاد',
                  onPressed: _plan == null ? null : _next,
                ),
              ],
            ),
    );
  }

  Widget _planCard(Map p) {
    final on = p['id'] == _plan;
    return Card(
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(16),
        side: BorderSide(
          color: on ? BrandColors.mayya : BrandColors.line,
          width: on ? 2 : 1,
        ),
      ),
      child: InkWell(
        borderRadius: BorderRadius.circular(16),
        onTap: () => setState(() => _plan = p['id'] as int),
        child: Padding(
          padding: const EdgeInsets.all(14),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              Text(
                '${p['name']}',
                style: const TextStyle(fontWeight: FontWeight.w800),
              ),
              Muted(
                '${p['washes_per_month']} غسلات في الشهر • ${(p['services'] as List).join('، ')}',
              ),
              const SizedBox(height: 6),
              KeyValue(
                'بدل ${money(p['normal_price'])}',
                money(p['price']),
                bold: true,
                color: BrandColors.good,
              ),
              Muted('خصم ${p['discount_percent']}% • في الشهر'),
            ],
          ),
        ),
      ),
    );
  }
}
