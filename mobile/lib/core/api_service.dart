import 'package:dio/dio.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';

class ApiService {
  static const String baseUrl = 'https://api.duraitution.com/api/v1';
  // For local dev: 'http://10.0.2.2:8000/api/v1'

  static final Dio _dio = Dio(BaseOptions(
    baseUrl: baseUrl,
    connectTimeout: const Duration(seconds: 30),
    receiveTimeout: const Duration(seconds: 30),
    headers: {'Content-Type': 'application/json'},
  ));

  static const _storage = FlutterSecureStorage();

  static Future<void> init() async {
    _dio.interceptors.add(InterceptorsWrapper(
      onRequest: (options, handler) async {
        final token = await _storage.read(key: 'access_token');
        if (token != null) {
          options.headers['Authorization'] = 'Bearer $token';
        }
        return handler.next(options);
      },
      onError: (error, handler) async {
        if (error.response?.statusCode == 401) {
          // Try refresh token
          final refreshed = await _refreshToken();
          if (refreshed) {
            final token = await _storage.read(key: 'access_token');
            error.requestOptions.headers['Authorization'] = 'Bearer $token';
            final response = await _dio.fetch(error.requestOptions);
            return handler.resolve(response);
          }
        }
        return handler.next(error);
      },
    ));
  }

  static Future<bool> _refreshToken() async {
    try {
      final refresh = await _storage.read(key: 'refresh_token');
      if (refresh == null) return false;
      final response = await Dio().post(
        '$baseUrl/auth/refresh/',
        data: {'refresh': refresh},
      );
      await _storage.write(key: 'access_token', value: response.data['access']);
      return true;
    } catch (_) {
      return false;
    }
  }

  // ── Auth ──
  static Future<Map<String, dynamic>> login(String username, String password) async {
    final response = await _dio.post('/auth/login/', data: {
      'username': username, 'password': password
    });
    await _storage.write(key: 'access_token', value: response.data['access']);
    await _storage.write(key: 'refresh_token', value: response.data['refresh']);
    return response.data;
  }

  static Future<void> logout() async {
    final refresh = await _storage.read(key: 'refresh_token');
    try { await _dio.post('/auth/logout/', data: {'refresh': refresh}); } catch (_) {}
    await _storage.deleteAll();
  }

  static Future<Map<String, dynamic>> getProfile() async {
    final response = await _dio.get('/auth/profile/');
    return response.data;
  }

  // ── Dashboard ──
  static Future<Map<String, dynamic>> getDashboard(String role) async {
    final response = await _dio.get('/dashboard/$role/');
    return response.data;
  }

  // ── Students ──
  static Future<List<dynamic>> getStudents({int? classId}) async {
    final params = classId != null ? {'current_class': classId} : null;
    final response = await _dio.get('/students/', queryParameters: params);
    return response.data['results'] ?? response.data;
  }

  // ── Attendance ──
  static Future<Map<String, dynamic>> getAttendanceSummary({
    int? classId, String? start, String? end
  }) async {
    final response = await _dio.get('/attendance/summary/', queryParameters: {
      if (classId != null) 'class_id': classId,
      if (start != null) 'start': start,
      if (end != null) 'end': end,
    });
    return {'data': response.data};
  }

  static Future<void> bulkMarkAttendance(Map<String, dynamic> data) async {
    await _dio.post('/attendance/bulk_mark/', data: data);
  }

  // ── Marks ──
  static Future<List<dynamic>> getMarks({int? studentId, int? examId}) async {
    final response = await _dio.get('/marks/', queryParameters: {
      if (studentId != null) 'student': studentId,
      if (examId != null) 'exam': examId,
    });
    return response.data['results'] ?? response.data;
  }

  static Future<List<dynamic>> getProgress(int studentId) async {
    final response = await _dio.get('/marks/progress/', queryParameters: {
      'student_id': studentId
    });
    return response.data;
  }

  // ── Notes ──
  static Future<List<dynamic>> getNotes({int? classId, bool? isQP}) async {
    final response = await _dio.get('/notes/', queryParameters: {
      if (classId != null) 'class_ref': classId,
      if (isQP != null) 'is_question_paper': isQP,
    });
    return response.data['results'] ?? response.data;
  }

  // ── Homework ──
  static Future<List<dynamic>> getHomework({int? classId}) async {
    final response = await _dio.get('/homework/', queryParameters: {
      if (classId != null) 'class_ref': classId,
    });
    return response.data['results'] ?? response.data;
  }

  // ── Fees ──
  static Future<List<dynamic>> getFees({int? studentId}) async {
    final response = await _dio.get('/fees/', queryParameters: {
      if (studentId != null) 'student': studentId,
    });
    return response.data['results'] ?? response.data;
  }

  // ── Notifications ──
  static Future<List<dynamic>> getNotifications() async {
    final response = await _dio.get('/notifications/');
    return response.data['results'] ?? response.data;
  }

  static Future<void> markAllNotificationsRead() async {
    await _dio.post('/notifications/mark_all_read/');
  }

  // ── AI Chat ──
  static Future<String> aiChat(String message, List<Map<String, String>> history) async {
    final response = await _dio.post('/ai/chat/', data: {
      'message': message, 'history': history
    });
    return response.data['reply'];
  }

  // ── AI Study Plan ──
  static Future<String> getStudyPlan(int studentId) async {
    final response = await _dio.post('/ai/study-plan/', data: {'student_id': studentId});
    return response.data['plan'];
  }
}