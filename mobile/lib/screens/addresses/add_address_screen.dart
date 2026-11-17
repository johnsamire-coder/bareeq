import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_map/flutter_map.dart';
import 'package:latlong2/latlong.dart';
import 'package:provider/provider.dart';

import '../../core/api.dart';
import '../../core/session.dart';
import '../../core/theme.dart';
import '../../widgets/common.dart';

/// TEMPORARY MAP: OpenStreetMap until the Google Maps key arrives (must be
/// replaced before launch, see docs/PROGRESS.md). The pin stays in the middle;
/// the customer moves the map under it.
class AddAddressScreen extends StatefulWidget {
  const AddAddressScreen({super.key});

  @override
  State<AddAddressScreen> createState() => _AddAddressScreenState();
}

class _AddAddressScreenState extends State<AddAddressScreen> {
  static const _start = LatLng(30.0729, 31.3456); // Nasr City
  final _map = MapController();
  LatLng _center = _start;
  Map<String, dynamic>? _zone; // null = outside or unknown
  bool _checking = false;
  Timer? _debounce;
  String _label = 'البيت';
  final _customLabel = TextEditingController();
  final _building = TextEditingController();
  final _floor = TextEditingController();
  final _apartment = TextEditingController();
  final _street = TextEditingController();
  final _landmark = TextEditingController();

  @override
  void initState() {
    super.initState();
    _locate();
  }

  @override
  void dispose() {
    _debounce?.cancel();
    super.dispose();
  }

  String _coord(double v) => v.toStringAsFixed(6);

  Future<void> _locate() async {
    setState(() => _checking = true);
    try {
      final r = await context.read<Session>().api.get('zones-locate/', {
        'lat': _coord(_center.latitude),
        'lng': _coord(_center.longitude),
      });
      setState(
        () => _zone = r['zone'] == null
            ? null
            : Map<String, dynamic>.from(r['zone']),
      );
    } catch (_) {
      setState(() => _zone = null);
    } finally {
      if (mounted) setState(() => _checking = false);
    }
  }

  void _moved(MapCamera camera) {
    _center = camera.center;
    _debounce?.cancel();
    _debounce = Timer(const Duration(milliseconds: 400), _locate);
  }

  Future<void> _notifyMe() async {
    await context.read<Session>().api.post('area-requests/', {
      'lat': _coord(_center.latitude),
      'lng': _coord(_center.longitude),
      'area_name': _street.text.trim(),
    });
    if (!mounted) return;
    showInfo(context, 'تمام، هنبلغك أول ما نوصل منطقتك.');
    Navigator.pop(context);
  }

  Future<void> _save() async {
    final label = _label == 'تاني' ? _customLabel.text.trim() : _label;
    try {
      final a = await context.read<Session>().api.post('my-addresses/', {
        'label': label.isEmpty ? 'عنوان' : label,
        'lat': _coord(_center.latitude),
        'lng': _coord(_center.longitude),
        'building': _building.text.trim(),
        'floor': _floor.text.trim(),
        'apartment': _apartment.text.trim(),
        'street': _street.text.trim(),
        'landmark': _landmark.text.trim(),
      });
      if (mounted) Navigator.pop(context, a);
    } on ApiError catch (e) {
      if (e.code == 'outside_service_area' && mounted) {
        setState(() => _zone = null);
        return;
      }
      rethrow;
    }
  }

  @override
  Widget build(BuildContext context) {
    final outside = !_checking && _zone == null;
    return Scaffold(
      appBar: AppBar(title: const Text('عنوان جديد')),
      body: ListView(
        children: [
          SizedBox(
            height: 300,
            child: Stack(
              children: [
                FlutterMap(
                  mapController: _map,
                  options: MapOptions(
                    initialCenter: _start,
                    initialZoom: 15,
                    onPositionChanged: (camera, hasGesture) => _moved(camera),
                  ),
                  children: [
                    TileLayer(
                      urlTemplate:
                          'https://tile.openstreetmap.org/{z}/{x}/{y}.png',
                      userAgentPackageName: 'eg.bareeq.app',
                    ),
                    const SimpleAttributionWidget(
                      source: Text('OpenStreetMap'),
                    ),
                  ],
                ),
                const IgnorePointer(
                  child: Center(
                    child: Padding(
                      padding: EdgeInsets.only(bottom: 36),
                      child: Icon(
                        Icons.location_on_rounded,
                        size: 46,
                        color: BrandColors.layl,
                      ),
                    ),
                  ),
                ),
                Positioned(
                  left: 12,
                  right: 12,
                  bottom: 12,
                  child: Container(
                    padding: const EdgeInsets.symmetric(
                      horizontal: 12,
                      vertical: 8,
                    ),
                    decoration: BoxDecoration(
                      color: Colors.white,
                      borderRadius: BorderRadius.circular(12),
                      border: Border.all(color: BrandColors.line),
                    ),
                    child: Text(
                      _checking
                          ? 'بنشوف المكان...'
                          : outside
                          ? 'لسه مش بنخدم المكان ده'
                          : 'المنطقة: ${_zone!['name']}',
                      textAlign: TextAlign.center,
                      style: TextStyle(
                        fontWeight: FontWeight.w700,
                        color: outside ? BrandColors.danger : BrandColors.good,
                      ),
                    ),
                  ),
                ),
              ],
            ),
          ),
          Padding(
            padding: const EdgeInsets.all(16),
            child: outside
                ? Column(
                    children: [
                      const Text(
                        'حرّك الخريطة وحط الدبوس على مكان العربية بالظبط.',
                        textAlign: TextAlign.center,
                      ),
                      const SizedBox(height: 8),
                      const Muted(
                        'لو مكانك برا مدينة نصر والعبور ومدينتي، نقدر نبلغك أول ما نوصل.',
                        align: TextAlign.center,
                      ),
                      const SizedBox(height: 12),
                      TextField(
                        controller: _street,
                        decoration: const InputDecoration(
                          labelText: 'اسم منطقتك (اختياري)',
                        ),
                      ),
                      const SizedBox(height: 12),
                      BusyButton(
                        label: 'بلغوني لما توصلوا',
                        icon: Icons.notifications_active_outlined,
                        onPressed: _notifyMe,
                      ),
                    ],
                  )
                : Column(
                    crossAxisAlignment: CrossAxisAlignment.stretch,
                    children: [
                      const Muted(
                        'حرّك الخريطة لحد ما الدبوس يبقى على مكان العربية بالظبط.',
                      ),
                      const SectionTitle('اسم العنوان'),
                      Wrap(
                        spacing: 8,
                        children: [
                          for (final l in const ['البيت', 'الشغل', 'تاني'])
                            ChoiceChip(
                              label: Text(l),
                              selected: _label == l,
                              onSelected: (_) => setState(() => _label = l),
                            ),
                        ],
                      ),
                      if (_label == 'تاني') ...[
                        const SizedBox(height: 8),
                        TextField(
                          controller: _customLabel,
                          decoration: const InputDecoration(
                            labelText: 'اسم العنوان',
                          ),
                        ),
                      ],
                      const SizedBox(height: 12),
                      TextField(
                        controller: _building,
                        decoration: const InputDecoration(
                          labelText: 'رقم العمارة / الفيلا',
                        ),
                        onChanged: (_) => setState(() {}),
                      ),
                      const SizedBox(height: 10),
                      Row(
                        children: [
                          Expanded(
                            child: TextField(
                              controller: _floor,
                              decoration: const InputDecoration(
                                labelText: 'الدور',
                              ),
                            ),
                          ),
                          const SizedBox(width: 10),
                          Expanded(
                            child: TextField(
                              controller: _apartment,
                              decoration: const InputDecoration(
                                labelText: 'الشقة',
                              ),
                            ),
                          ),
                        ],
                      ),
                      const SizedBox(height: 10),
                      TextField(
                        controller: _street,
                        decoration: const InputDecoration(
                          labelText: 'الشارع (اختياري)',
                        ),
                      ),
                      const SizedBox(height: 10),
                      TextField(
                        controller: _landmark,
                        decoration: const InputDecoration(
                          labelText: 'علامة مميزة (اختياري)',
                        ),
                      ),
                      const SizedBox(height: 18),
                      BusyButton(
                        label: 'احفظ العنوان',
                        onPressed: (_building.text.trim().isEmpty || _checking)
                            ? null
                            : _save,
                      ),
                    ],
                  ),
          ),
        ],
      ),
    );
  }
}
