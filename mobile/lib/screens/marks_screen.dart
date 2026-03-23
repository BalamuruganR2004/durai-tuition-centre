import 'package:flutter/material.dart';
import 'package:fl_chart/fl_chart.dart';
import '../core/api_service.dart';
import '../core/theme.dart';

class MarksScreen extends StatefulWidget {
  const MarksScreen({super.key});
  @override
  State<MarksScreen> createState() => _MarksScreenState();
}

class _MarksScreenState extends State<MarksScreen> with SingleTickerProviderStateMixin {
  late TabController _tabController;
  List<dynamic> _marks = [];
  List<dynamic> _progress = [];
  bool _loading = true;

  @override
  void initState() {
    super.initState();
    _tabController = TabController(length: 2, vsync: this);
    _load();
  }

  Future<void> _load() async {
    setState(() => _loading = true);
    try {
      final marks = await ApiService.getMarks();
      setState(() { _marks = marks; _loading = false; });
    } catch (_) {
      setState(() => _loading = false);
    }
  }

  Color _gradeColor(String grade) {
    switch (grade) {
      case 'A+': case 'A': return AppTheme.success;
      case 'B+': case 'B': return Colors.blue;
      case 'C': return AppTheme.warning;
      default: return AppTheme.danger;
    }
  }

  @override
  Widget build(BuildContext context) {
    return Column(
      children: [
        TabBar(
          controller: _tabController,
          labelColor: AppTheme.primary,
          tabs: const [Tab(text: 'My Marks'), Tab(text: 'Progress')],
        ),
        Expanded(
          child: TabBarView(
            controller: _tabController,
            children: [
              _loading ? const Center(child: CircularProgressIndicator()) : _buildMarksList(),
              _buildProgressChart(),
            ],
          ),
        ),
      ],
    );
  }

  Widget _buildMarksList() {
    return ListView.builder(
      padding: const EdgeInsets.all(16),
      itemCount: _marks.length,
      itemBuilder: (ctx, i) {
        final m = _marks[i];
        final grade = m['grade'] ?? 'N/A';
        return Card(
          margin: const EdgeInsets.only(bottom: 8),
          child: ListTile(
            leading: CircleAvatar(
              backgroundColor: _gradeColor(grade).withOpacity(0.2),
              child: Text(grade,
                style: TextStyle(color: _gradeColor(grade), fontWeight: FontWeight.bold)),
            ),
            title: Text(m['subject_name'] ?? ''),
            subtitle: Text('${m['exam_name']} • ${m['percentage']}%'),
            trailing: Text('${m['marks_obtained']}/${m['total_marks']}',
              style: const TextStyle(fontWeight: FontWeight.bold)),
          ),
        );
      },
    );
  }

  Widget _buildProgressChart() {
    if (_marks.isEmpty) return const Center(child: Text('No marks data available'));

    // Group marks by subject for chart
    final Map<String, List<double>> bySubject = {};
    for (final m in _marks) {
      final subj = m['subject_name'] as String;
      bySubject.putIfAbsent(subj, () => []);
      bySubject[subj]!.add((m['percentage'] as num).toDouble());
    }

    return Padding(
      padding: const EdgeInsets.all(16),
      child: BarChart(
        BarChartData(
          maxY: 100,
          barGroups: bySubject.entries.toList().asMap().map((idx, entry) {
            final avgPct = entry.value.reduce((a, b) => a + b) / entry.value.length;
            return MapEntry(idx, BarChartGroupData(
              x: idx,
              barRods: [BarChartRodData(
                toY: avgPct,
                color: AppTheme.primary,
                width: 22,
                borderRadius: const BorderRadius.vertical(top: Radius.circular(4)),
              )],
            ));
          }).values.toList(),
          titlesData: FlTitlesData(
            bottomTitles: AxisTitles(
              sideTitles: SideTitles(
                showTitles: true,
                getTitlesWidget: (val, meta) {
                  final subjects = bySubject.keys.toList();
                  final i = val.toInt();
                  if (i < subjects.length) {
                    return Text(subjects[i].substring(0, subjects[i].length.clamp(0, 3)),
                      style: const TextStyle(fontSize: 10));
                  }
                  return const Text('');
                },
              ),
            ),
            leftTitles: AxisTitles(sideTitles: SideTitles(showTitles: true)),
            topTitles: AxisTitles(sideTitles: SideTitles(showTitles: false)),
            rightTitles: AxisTitles(sideTitles: SideTitles(showTitles: false)),
          ),
          gridData: FlGridData(show: true),
          borderData: FlBorderData(show: false),
        ),
      ),
    );
  }
}