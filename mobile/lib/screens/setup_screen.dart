import 'package:flutter/material.dart';

import '../core/theme.dart';
import '../widgets/common.dart';
import 'addresses/add_address_screen.dart';
import 'cars/add_car_screen.dart';

/// Right after sign-up: "your car" and "your address" (SPEC 2.4). Can be skipped;
/// booking asks for them later.
class SetupScreen extends StatefulWidget {
  const SetupScreen({super.key});

  @override
  State<SetupScreen> createState() => _SetupScreenState();
}

class _SetupScreenState extends State<SetupScreen> {
  bool _car = false, _address = false;

  @override
  Widget build(BuildContext context) {
    Widget step(String title, String sub, IconData icon, bool done, VoidCallback onTap) => Card(
          child: ListTile(
            contentPadding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
            leading: Icon(done ? Icons.check_circle_rounded : icon, size: 34, color: done ? BrandColors.good : BrandColors.mayya),
            title: Text(title, style: const TextStyle(fontWeight: FontWeight.w700)),
            subtitle: Text(sub),
            trailing: done ? null : const Icon(Icons.chevron_left),
            onTap: done ? null : onTap,
          ),
        );
    return Scaffold(
      appBar: AppBar(title: const Text('خطوتين وتبقى جاهز'), automaticallyImplyLeading: false),
      body: ListView(padding: const EdgeInsets.all(16), children: [
        const Muted('عشان نحسبلك السعر ونوصلك صح.'),
        const SizedBox(height: 16),
        step('عربيتك', 'الماركة والموديل واللون', Icons.directions_car_outlined, _car, () async {
          final r = await Navigator.push(context, MaterialPageRoute(builder: (_) => const AddCarScreen()));
          if (r != null) setState(() => _car = true);
        }),
        const SizedBox(height: 10),
        step('عنوانك', 'مكان العربية على الخريطة', Icons.location_on_outlined, _address, () async {
          final r = await Navigator.push(context, MaterialPageRoute(builder: (_) => const AddAddressScreen()));
          if (r != null) setState(() => _address = true);
        }),
        const SizedBox(height: 24),
        FilledButton(onPressed: () => Navigator.pop(context), child: Text(_car && _address ? 'يلا نبدأ' : 'تخطّي دلوقتي')),
      ]),
    );
  }
}
