import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../../core/session.dart';
import '../../core/theme.dart';
import '../../widgets/common.dart';
import '../addresses/add_address_screen.dart';
import '../addresses/my_addresses_screen.dart';
import '../cars/add_car_screen.dart';
import 'services_screen.dart';

/// Booking step 1: which address and which car(s). Several cars = one order,
/// same address, washed one after another by the same technician.
class BookStartScreen extends StatefulWidget {
  const BookStartScreen({super.key});

  @override
  State<BookStartScreen> createState() => _BookStartScreenState();
}

class _BookStartScreenState extends State<BookStartScreen> {
  List<dynamic>? _cars, _addresses;
  Object? _error;
  int? _addressId;
  final Set<int> _carIds = {};

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    final api = context.read<Session>().api;
    try {
      final cars = await api.get('my-cars/') as List;
      final addresses = await api.get('my-addresses/') as List;
      setState(() {
        _cars = cars;
        _addresses = addresses;
        _error = null;
        if (_addressId == null && addresses.isNotEmpty) _addressId = addresses.first['id'];
        if (_carIds.isEmpty && cars.length == 1) _carIds.add(cars.first['id']);
      });
    } catch (e) {
      setState(() => _error = e);
    }
  }

  Future<void> _addCar() async {
    final c = await Navigator.push(context, MaterialPageRoute(builder: (_) => const AddCarScreen()));
    if (c != null) {
      _carIds.add(c['id']);
      _load();
    }
  }

  Future<void> _addAddress() async {
    final a = await Navigator.push(context, MaterialPageRoute(builder: (_) => const AddAddressScreen()));
    if (a != null) {
      _addressId = a['id'];
      _load();
    }
  }

  @override
  Widget build(BuildContext context) {
    final ready = _addressId != null && _carIds.isNotEmpty;
    return Scaffold(
      appBar: AppBar(title: const Text('احجز غسلة')),
      body: _error != null
          ? ErrorRetry(error: _error!, onRetry: _load)
          : _cars == null
              ? const Loading()
              : ListView(padding: const EdgeInsets.fromLTRB(16, 0, 16, 100), children: [
                  SectionTitle('العنوان', trailing: TextButton.icon(onPressed: _addAddress, icon: const Icon(Icons.add), label: const Text('جديد'))),
                  if (_addresses!.isEmpty)
                    Card(child: ListTile(leading: const Icon(Icons.add_location_alt_outlined), title: const Text('ضيف عنوانك الأول'), onTap: _addAddress)),
                  RadioGroup<int>(
                    groupValue: _addressId,
                    onChanged: (v) => setState(() => _addressId = v),
                    child: Column(children: [
                      for (final a in _addresses!)
                        Padding(
                          padding: const EdgeInsets.only(bottom: 8),
                          child: Card(
                            child: RadioListTile<int>(
                              value: a['id'],
                              title: Text('${a['label']}', style: const TextStyle(fontWeight: FontWeight.w700)),
                              subtitle: Text(addressLine(a)),
                            ),
                          ),
                        ),
                    ]),
                  ),
                  SectionTitle('العربية', trailing: TextButton.icon(onPressed: _addCar, icon: const Icon(Icons.add), label: const Text('جديدة'))),
                  if (_cars!.isEmpty)
                    Card(child: ListTile(leading: const Icon(Icons.directions_car_outlined), title: const Text('ضيف عربيتك الأول'), onTap: _addCar)),
                  for (final c in _cars!)
                    Padding(
                      padding: const EdgeInsets.only(bottom: 8),
                      child: Card(
                        child: CheckboxListTile(
                          value: _carIds.contains(c['id']),
                          onChanged: (v) => setState(() => v == true ? _carIds.add(c['id']) : _carIds.remove(c['id'])),
                          title: Text('${c['display_name']}', style: const TextStyle(fontWeight: FontWeight.w700)),
                          subtitle: Text('${c['color_name']}'),
                        ),
                      ),
                    ),
                  if (_cars!.length > 1) const Muted('تقدر تختار أكتر من عربية في نفس الطلب.'),
                ]),
      bottomNavigationBar: _cars == null
          ? null
          : SafeArea(
              child: Padding(
                padding: const EdgeInsets.all(16),
                child: FilledButton(
                  onPressed: ready
                      ? () => Navigator.push(context, MaterialPageRoute(
                            builder: (_) => ServicesScreen(
                              addressId: _addressId!,
                              cars: [for (final c in _cars!) if (_carIds.contains(c['id'])) Map<String, dynamic>.from(c)],
                            ),
                          ))
                      : null,
                  child: const Text('اختار الخدمات'),
                ),
              ),
            ),
      backgroundColor: BrandColors.sahab,
    );
  }
}
