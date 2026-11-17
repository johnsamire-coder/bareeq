import 'package:flutter/foundation.dart';
import 'package:geolocator/geolocator.dart';

/// Current position, or null when location is off or not allowed.
Future<Position?> currentPosition() async {
  try {
    if (!await Geolocator.isLocationServiceEnabled()) return null;
    var p = await Geolocator.checkPermission();
    if (p == LocationPermission.denied) {
      p = await Geolocator.requestPermission();
    }
    if (p == LocationPermission.denied ||
        p == LocationPermission.deniedForever) {
      return null;
    }
    return await Geolocator.getCurrentPosition(
      locationSettings: const LocationSettings(
        accuracy: LocationAccuracy.high,
        timeLimit: Duration(seconds: 15),
      ),
    );
  } catch (e) {
    debugPrint('location error: $e');
    return null;
  }
}

String coord(double v) => v.toStringAsFixed(6);
