import 'package:flutter/foundation.dart';
import '../core/api_service.dart';

class AuthProvider extends ChangeNotifier {
  Map<String, dynamic>? _user;
  bool _loading = false;

  Map<String, dynamic>? get user => _user;
  bool get loading => _loading;
  bool get isLoggedIn => _user != null;

  Future<void> login(String username, String password) async {
    _loading = true;
    notifyListeners();
    try {
      final data = await ApiService.login(username, password);
      _user = data['user'];
    } finally {
      _loading = false;
      notifyListeners();
    }
  }

  Future<void> logout() async {
    await ApiService.logout();
    _user = null;
    notifyListeners();
  }

  Future<void> loadProfile() async {
    try {
      _user = await ApiService.getProfile();
      notifyListeners();
    } catch (_) {}
  }
}