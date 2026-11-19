import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_map/flutter_map.dart';
import 'package:latlong2/latlong.dart';
import 'package:provider/provider.dart';

import '../../core/format.dart';
import '../../core/session.dart';
import '../../core/theme.dart';
import '../../widgets/common.dart';
import 'manager_order_screen.dart';

const _tiles =
    'https://tile.openstreetmap.org/{z}/{x}/{y}.png'; // TEMPORARY until the Google Maps key

/// Today's map: where each technician is now (while on the way) and the day's
/// jobs. A supervisor sees his zones only. Refreshes every 30 seconds.
class LiveMapScreen extends StatefulWidget {
  const LiveMapScreen({super.key});

  @override
  State<LiveMapScreen> createState() => _LiveMapScreenState();
}

class _LiveMapScreenState extends State<LiveMapScreen> {
  Map<String, dynamic>? _d;
  Object? _error;
  Timer? _timer;

  @override
  void initState() {
    super.initState();
    _load();
    _timer = Timer.periodic(const Duration(seconds: 30), (_) => _load());
  }

  @override
  void dispose() {
    _timer?.cancel();
    super.dispose();
  }

  Future<void> _load() async {
    try {
      final r = await context.read<Session>().api.get('manage/live-map/');
      if (mounted) {
        setState(() => (_d = Map<String, dynamic>.from(r), _error = null));
      }
    } catch (e) {
      if (mounted) setState(() => _error = e);
    }
  }

  Color _color(String status) => switch (status) {
    'completed' => BrandColors.good,
    'on_the_way' || 'arrived' || 'in_progress' => BrandColors.mayya,
    'cancelled_by_customer' ||
    'cancelled_by_company' ||
    'car_not_found' => BrandColors.muted,
    _ => BrandColors.layl,
  };

  @override
  Widget build(BuildContext context) {
    final d = _d;
    final orders = (d?['orders'] as List?) ?? [];
    final techs = ((d?['technicians'] as List?) ?? [])
        .where((t) => t['lat'] != null)
        .toList();
    final points = [
      for (final o in orders) LatLng(o['lat'] as double, o['lng'] as double),
      for (final t in techs) LatLng(t['lat'] as double, t['lng'] as double),
    ];
    return Scaffold(
      appBar: AppBar(title: const Text('خريطة اليوم')),
      body: _error != null
          ? ErrorRetry(error: _error!, onRetry: _load)
          : d == null
          ? const Loading()
          : Column(
              children: [
                SizedBox(
                  height: 360,
                  child: ExcludeSemantics(
                    child: FlutterMap(
                      options: MapOptions(
                        initialCenter: points.isEmpty
                            ? const LatLng(30.0729, 31.3456)
                            : points.first,
                        initialZoom: 11,
                        initialCameraFit: points.length > 1
                            ? CameraFit.coordinates(
                                coordinates: points,
                                padding: const EdgeInsets.all(40),
                              )
                            : null,
                      ),
                      children: [
                        TileLayer(
                          urlTemplate: _tiles,
                          userAgentPackageName: 'eg.bareeq.app',
                        ),
                        MarkerLayer(
                          markers: [
                            for (final o in orders)
                              Marker(
                                point: LatLng(
                                  o['lat'] as double,
                                  o['lng'] as double,
                                ),
                                child: Icon(
                                  Icons.location_on,
                                  size: 32,
                                  color: _color('${o['status']}'),
                                ),
                              ),
                            for (final t in techs)
                              Marker(
                                point: LatLng(
                                  t['lat'] as double,
                                  t['lng'] as double,
                                ),
                                width: 44,
                                height: 44,
                                child: const CircleAvatar(
                                  backgroundColor: BrandColors.lamaa,
                                  child: Icon(
                                    Icons.directions_car,
                                    color: BrandColors.layl,
                                  ),
                                ),
                              ),
                          ],
                        ),
                      ],
                    ),
                  ),
                ),
                Expanded(
                  child: ListView(
                    padding: const EdgeInsets.all(12),
                    children: [
                      for (final t in d['technicians'] as List)
                        ListTile(
                          dense: true,
                          leading: Icon(
                            Icons.engineering_outlined,
                            color: t['lat'] != null
                                ? BrandColors.mayya
                                : BrandColors.muted,
                          ),
                          title: Text('${t['full_name'] ?? t['name']}'),
                          subtitle: Text(
                            t['on_the_way_to'] != null
                                ? 'في الطريق لطلب ${t['on_the_way_to']}'
                                      '${t['updated_at'] != null ? ' • آخر مكان ${clock(parseServerTime('${t['updated_at']}'))}' : ''}'
                                : 'مش في الطريق دلوقتي',
                          ),
                        ),
                      const Divider(color: BrandColors.line),
                      for (final o in orders)
                        ListTile(
                          dense: true,
                          leading: Icon(
                            Icons.location_on,
                            color: _color('${o['status']}'),
                          ),
                          title: Text(
                            '${clock(parseServerTime('${o['start']}'))} • ${o['customer_name']}'
                            '${o['is_express'] == true ? ' • سريع' : ''}',
                          ),
                          subtitle: Text(
                            '${o['status_label']} • ${o['technician_name'] ?? '-'}',
                          ),
                          onTap: () => Navigator.push(
                            context,
                            MaterialPageRoute(
                              builder: (_) =>
                                  ManagerOrderScreen(orderId: o['id'] as int),
                            ),
                          ),
                        ),
                    ],
                  ),
                ),
              ],
            ),
    );
  }
}
