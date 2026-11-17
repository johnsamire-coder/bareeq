import 'package:url_launcher/url_launcher.dart';

/// Opens Google Maps directions on the phone (no API key needed).
Future<void> openDirections(String lat, String lng) =>
    launchUrl(Uri.parse('https://www.google.com/maps/dir/?api=1&destination=$lat,$lng'), mode: LaunchMode.externalApplication);

Future<void> callPhone(String phone) => launchUrl(Uri.parse('tel:$phone'));
