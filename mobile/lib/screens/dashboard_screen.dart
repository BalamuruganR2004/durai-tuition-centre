import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../core/api_service.dart';
import '../core/theme.dart';
import '../providers/auth_provider.dart';
import '../widgets/stat_card.dart';

class DashboardScreen extends StatefulWidget {
  const DashboardScreen({super.key});
  @override
  State<DashboardScreen> createState() => _DashboardScreenState();
}

class _DashboardScreenState extends State<DashboardScreen> {
  Map<String, dynamic>? _data;
  bool _loading = true;
  String? _error;

  @override
  void initState() {
    super.initState();
    _loadDashboard();
  }

  Future<void> _loadDashboard() async {
    setState(() { _loading = true; _error = null; });
    try {
      final role = context.read<AuthProvider>().user?['role'] ?? 'student';
      final data = await ApiService.getDashboard(role);
      setState(() { _data = data; _loading = false; });
    } catch (e) {
      setState(() { _error = e.toString(); _loading = false; });
    }
  }

  @override
  Widget build(BuildContext context) {
    if (_loading) return const Center(child: CircularProgressIndicator());
    if (_error != null) return Center(child: Column(
      mainAxisAlignment: MainAxisAlignment.center,
      children: [
        Text(_error!, style: const TextStyle(color: Colors.red)),
        ElevatedButton(onPressed: _loadDashboard, child: const Text('Retry')),
      ],
    ));

    final role = context.read<AuthProvider>().user?['role'] ?? 'student';
    return RefreshIndicator(
      onRefresh: _loadDashboard,
      child: SingleChildScrollView(
        physics: const AlwaysScrollableScrollPhysics(),
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            _buildGreeting(context, role),
            const SizedBox(height: 20),
            if (role == 'admin') _buildAdminCards(),
            if (role == 'teacher') _buildTeacherCards(),
            if (role == 'student') _buildStudentCards(),
            if (role == 'parent') _buildParentCards(),
          ],
        ),
      ),
    );
  }

  Widget _buildGreeting(BuildContext context, String role) {
    final user = context.read<AuthProvider>().user;
    final name = '${user?['first_name'] ?? ''} ${user?['last_name'] ?? ''}'.trim();
    return Container(
      padding: const EdgeInsets.all(20),
      decoration: BoxDecoration(
        gradient: const LinearGradient(colors: [AppTheme.primary, Color(0xFF283593)]),
        borderRadius: BorderRadius.circular(16),
      ),
      child: Row(
        children: [
          const CircleAvatar(
            backgroundColor: Colors.white24,
            child: Icon(Icons.person, color: Colors.white),
          ),
          const SizedBox(width: 12),
          Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text('Welcome back,', style: TextStyle(color: Colors.white70, fontSize: 13)),
              Text(name.isEmpty ? 'User' : name,
                style: const TextStyle(color: Colors.white, fontSize: 18,
                  fontWeight: FontWeight.bold)),
              Text(role.toUpperCase(),
                style: const TextStyle(color: AppTheme.accent, fontSize: 11,
                  fontWeight: FontWeight.w600, letterSpacing: 1.5)),
            ],
          ),
        ],
      ),
    );
  }

  Widget _buildAdminCards() {
    final d = _data!;
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        const Text('Overview', style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold)),
        const SizedBox(height: 12),
        GridView.count(
          crossAxisCount: 2, shrinkWrap: true, physics: const NeverScrollableScrollPhysics(),
          mainAxisSpacing: 12, crossAxisSpacing: 12, childAspectRatio: 1.4,
          children: [
            StatCard(title: 'Students', value: '${d['students']['total']}',
              icon: Icons.people, color: AppTheme.primary),
            StatCard(title: 'Teachers', value: '${d['teachers']['total']}',
              icon: Icons.person_pin, color: AppTheme.accent),
            StatCard(title: 'Present Today', value: '${d['attendance_today']['present']}',
              icon: Icons.check_circle, color: AppTheme.success),
            StatCard(title: 'Absent Today', value: '${d['attendance_today']['absent']}',
              icon: Icons.cancel, color: AppTheme.danger),
          ],
        ),
        const SizedBox(height: 20),
        _FeesSummaryCard(fees: d['fees']),
        const SizedBox(height: 20),
        _WeakStudentsList(students: d['weak_students'] ?? []),
      ],
    );
  }

  Widget _buildTeacherCards() {
    final d = _data!;
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        const Text('My Classes', style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold)),
        const SizedBox(height: 12),
        ...((d['my_classes'] as List).map((cls) => Card(
          margin: const EdgeInsets.only(bottom: 8),
          child: ListTile(
            leading: CircleAvatar(
              backgroundColor: AppTheme.primary,
              child: Text(cls['grade'].toString(),
                style: const TextStyle(color: Colors.white, fontWeight: FontWeight.bold)),
            ),
            title: Text(cls['name']),
            subtitle: Text('${cls['student_count']} students'),
            trailing: const Icon(Icons.arrow_forward_ios, size: 16),
          ),
        ))),
      ],
    );
  }

  Widget _buildStudentCards() {
    final d = _data!;
    final att = d['attendance'];
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Row(
          children: [
            Expanded(child: StatCard(
              title: 'Attendance', value: '${att['percentage']}%',
              icon: Icons.calendar_today, color: AppTheme.primary,
            )),
            const SizedBox(width: 12),
            Expanded(child: StatCard(
              title: 'Fee Pending', value: '₹${d['fee_pending']}',
              icon: Icons.payment, color: AppTheme.warning,
            )),
          ],
        ),
        const SizedBox(height: 20),
        const Text('Recent Marks', style: TextStyle(fontSize: 16, fontWeight: FontWeight.bold)),
        const SizedBox(height: 8),
        ...((d['latest_marks'] as List).take(5).map((m) => Card(
          margin: const EdgeInsets.only(bottom: 8),
          child: ListTile(
            title: Text(m['subject_name']),
            subtitle: Text('${m['exam_name']} • ${m['grade']}'),
            trailing: Text('${m['marks_obtained']}/${m['total_marks']}',
              style: const TextStyle(fontWeight: FontWeight.bold, color: AppTheme.primary)),
          ),
        ))),
      ],
    );
  }

  Widget _buildParentCards() {
    final d = _data!;
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        const Text("My Children", style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold)),
        const SizedBox(height: 12),
        ...((d['children'] as List).map((child) => Card(
          margin: const EdgeInsets.only(bottom: 12),
          child: Padding(
            padding: const EdgeInsets.all(16),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(child['student']['user']['first_name'] + ' ' +
                  child['student']['user']['last_name'],
                  style: const TextStyle(fontSize: 16, fontWeight: FontWeight.bold)),
                Text(child['student']['class_name'] ?? '',
                  style: TextStyle(color: Colors.grey[600])),
                const SizedBox(height: 12),
                Row(
                  mainAxisAlignment: MainAxisAlignment.spaceAround,
                  children: [
                    _infoChip('Attendance', '${child['attendance_pct']}%', AppTheme.success),
                    _infoChip('Pending Fee', '₹${child['fee_pending']}', AppTheme.warning),
                    if (child['latest_mark'] != null)
                      _infoChip('Last Mark', child['latest_mark']['grade'], AppTheme.primary),
                  ],
                ),
              ],
            ),
          ),
        ))),
      ],
    );
  }

  Widget _infoChip(String label, String value, Color color) {
    return Column(
      children: [
        Text(value, style: TextStyle(color: color, fontWeight: FontWeight.bold, fontSize: 16)),
        Text(label, style: TextStyle(color: Colors.grey[600], fontSize: 11)),
      ],
    );
  }
}

class _FeesSummaryCard extends StatelessWidget {
  final Map fees;
  const _FeesSummaryCard({required this.fees});

  @override
  Widget build(BuildContext context) {
    final rate = (fees['collection_rate'] as num).toDouble();
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Text('Fee Collection', style: TextStyle(fontWeight: FontWeight.bold, fontSize: 16)),
            const SizedBox(height: 12),
            LinearProgressIndicator(value: rate / 100,
              backgroundColor: Colors.grey[200], color: AppTheme.accent, minHeight: 8),
            const SizedBox(height: 8),
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                Text('Collected: ₹${fees['collected']}', style: const TextStyle(color: AppTheme.success)),
                Text('Pending: ₹${fees['pending']}', style: const TextStyle(color: AppTheme.danger)),
              ],
            ),
          ],
        ),
      ),
    );
  }
}

class _WeakStudentsList extends StatelessWidget {
  final List students;
  const _WeakStudentsList({required this.students});

  @override
  Widget build(BuildContext context) {
    if (students.isEmpty) return const SizedBox.shrink();
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        const Text('At-Risk Students', style: TextStyle(fontSize: 16, fontWeight: FontWeight.bold, color: AppTheme.danger)),
        const SizedBox(height: 8),
        ...students.take(5).map((s) => Card(
          margin: const EdgeInsets.only(bottom: 8),
          color: Colors.red[50],
          child: ListTile(
            leading: CircleAvatar(
              backgroundColor: AppTheme.danger,
              child: Text(s['name'][0], style: const TextStyle(color: Colors.white)),
            ),
            title: Text(s['name']),
            subtitle: Text('Att: ${s['attendance_pct']}% | Marks: ${s['avg_marks'] ?? 'N/A'}%'),
            trailing: Container(
              padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
              decoration: BoxDecoration(
                color: AppTheme.danger,
                borderRadius: BorderRadius.circular(12),
              ),
              child: Text('HIGH', style: const TextStyle(color: Colors.white, fontSize: 11)),
            ),
          ),
        )),
      ],
    );
  }
}