import 'package:flutter/foundation.dart';
import 'package:shared_preferences/shared_preferences.dart';

import 'api.dart';

/// Who is logged in. Keeps the token on the phone so the customer stays logged in.
class Session extends ChangeNotifier {
  Session(this.api);
  final Api api;
  Map<String, dynamic>? user;
  bool loading = true;

  /// Test version: the login code shows on screen and a banner says so.
  bool demoMode = false;

  bool get loggedIn => api.token != null && user != null;
  String get role => '${user?['role'] ?? ''}';
  bool get needsTerms => user?['needs_terms_acceptance'] == true;

  Future<void> loadConfig() async {
    try {
      final c = await api.get('app-config/');
      demoMode = c['demo_mode'] == true;
      notifyListeners();
    } catch (_) {}
  }

  Future<void> restore() async {
    await loadConfig();
    final prefs = await SharedPreferences.getInstance();
    api.token = prefs.getString('token');
    if (api.token != null) {
      try {
        user = Map<String, dynamic>.from(await api.get('me/'));
      } on ApiError catch (e) {
        if (e.status == 401) await _forget();
      }
    }
    loading = false;
    notifyListeners();
  }

  Future<void> loggedInWith(String token, Map<String, dynamic> me) async {
    api.token = token;
    user = me;
    final prefs = await SharedPreferences.getInstance();
    await prefs.setString('token', token);
    notifyListeners();
  }

  Future<void> refreshMe() async {
    user = Map<String, dynamic>.from(await api.get('me/'));
    notifyListeners();
  }

  Future<void> logout() async {
    try {
      await api.post('auth/logout/');
    } catch (_) {}
    await _forget();
    notifyListeners();
  }

  Future<void> _forget() async {
    api.token = null;
    user = null;
    final prefs = await SharedPreferences.getInstance();
    await prefs.remove('token');
  }
}
