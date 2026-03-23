import 'package:flutter/material.dart';
import 'package:intl/intl.dart';
import 'package:provider/provider.dart';
import '../core/api_service.dart';
import '../core/theme.dart';
import '../providers/auth_provider.dart';

class AttendanceScreen extends StatefulWidget {
  const AttendanceScreen({super.key});
  @override
  State<AttendanceScreen> createState() => _AttendanceScreenState();
}

class _AttendanceScreenState extends State<AttendanceScreen> {
  List<dynamic> _summary = [];
  bool _loading = true;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    setState(() => _loading = true);
    try {
      final role = context.read<AuthProvider>().user?['role'];
      final data = await ApiService.getAttendanceSummary(
        start: DateFormat('yyyy-MM-dd').format(DateTime.now().subtract(const Duration(days: 30))),
        end: DateFormat('yyyy-MM-dd').format(DateTime.now()),
      );
      setState(() {
        _summary = data['data'] ?? [];
        _loading = false;
      });
    } catch (e) {
      setState(() => _loading = false);
    }
  }

  Color _attColor(double pct) {
    if (pct >= 85) return AppTheme.success;
    if (pct >= 75) return AppTheme.warning;
    return AppTheme.danger;
  }

  @override
  Widget build(BuildContext context) {
    if (_loading) return const Center(child: CircularProgressIndicator());

    return RefreshIndicator(
      onRefresh: _load,
      child: ListView.builder(
        padding: const EdgeInsets.all(16),
        itemCount: _summary.length,
        itemBuilder: (ctx, i) {
          final row = _summary[i];
          final pct = (row['percentage'] as num).toDouble();
          return Card(
            margin: const EdgeInsets.only(bottom: 8),
            child: Padding(
              padding: const EdgeInsets.all(12),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Row(
                    mainAxisAlignment: MainAxisAlignment.spaceBetween,
                    children: [
                      Text(row['name'] ?? 'Student',
                        style: const TextStyle(fontWeight: FontWeight.bold)),
                      Container(
                        padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
                        decoration: BoxDecoration(
                          color: _attColor(pct).withOpacity(0.1),
                          borderRadius: BorderRadius.circular(12),
                          border: Border.all(color: _attColor(pct)),
                        ),
                        child: Text('$pct%',
                          style: TextStyle(color: _attColor(pct),
                            fontWeight: FontWeight.bold)),
                      ),
                    ],
                  ),
                  const SizedBox(height: 8),
                  LinearProgressIndicator(
                    value: pct / 100,
                    color: _attColor(pct),
                    backgroundColor: Colors.grey[200],
                    minHeight: 6,
                  ),
                  const SizedBox(height: 6),
                  Row(
                    children: [
                      _chip('Present: ${row['present']}', AppTheme.success),
                      const SizedBox(width: 8),
                      _chip('Absent: ${row['absent']}', AppTheme.danger),
                      const SizedBox(width: 8),
                      _chip('Late: ${row['late']}', AppTheme.warning),
                    ],
                  ),
                ],
              ),
            ),
          );
        },
      ),
    );
  }

  Widget _chip(String text, Color color) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
      decoration: BoxDecoration(
        color: color.withOpacity(0.1),
        borderRadius: BorderRadius.circular(8),
      ),
      child: Text(text, style: TextStyle(color: color, fontSize: 11)),
    );
  }
}