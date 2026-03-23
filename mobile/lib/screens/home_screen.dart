import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../providers/auth_provider.dart';
import '../core/theme.dart';
import 'dashboard_screen.dart';
import 'attendance_screen.dart';
import 'marks_screen.dart';
import 'notes_screen.dart';
import 'fees_screen.dart';
import 'ai_chat_screen.dart';
import 'notifications_screen.dart';

class HomeScreen extends StatefulWidget {
  const HomeScreen({super.key});
  @override
  State<HomeScreen> createState() => _HomeScreenState();
}

class _HomeScreenState extends State<HomeScreen> {
  int _currentIndex = 0;

  List<BottomNavigationBarItem> get _navItems {
    final role = context.read<AuthProvider>().user?['role'] ?? 'student';
    final base = [
      const BottomNavigationBarItem(icon: Icon(Icons.dashboard), label: 'Dashboard'),
      const BottomNavigationBarItem(icon: Icon(Icons.how_to_reg), label: 'Attendance'),
      const BottomNavigationBarItem(icon: Icon(Icons.grade), label: 'Marks'),
      const BottomNavigationBarItem(icon: Icon(Icons.book), label: 'Notes'),
    ];
    if (role == 'student' || role == 'parent') {
      base.addAll([
        const BottomNavigationBarItem(icon: Icon(Icons.payment), label: 'Fees'),
        const BottomNavigationBarItem(icon: Icon(Icons.smart_toy), label: 'AI'),
      ]);
    }
    return base;
  }

  List<Widget> get _screens {
    final role = context.read<AuthProvider>().user?['role'] ?? 'student';
    final base = <Widget>[
      const DashboardScreen(),
      const AttendanceScreen(),
      const MarksScreen(),
      const NotesScreen(),
    ];
    if (role == 'student' || role == 'parent') {
      base.addAll([const FeesScreen(), const AIChatScreen()]);
    }
    return base;
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Durai Tuition Centre'),
        actions: [
          IconButton(
            icon: const Icon(Icons.notifications),
            onPressed: () => Navigator.push(context,
              MaterialPageRoute(builder: (_) => const NotificationsScreen())),
          ),
          IconButton(
            icon: const Icon(Icons.logout),
            onPressed: () async {
              await context.read<AuthProvider>().logout();
              if (mounted) Navigator.pushReplacementNamed(context, '/login');
            },
          ),
        ],
      ),
      body: IndexedStack(index: _currentIndex, children: _screens),
      bottomNavigationBar: BottomNavigationBar(
        currentIndex: _currentIndex,
        onTap: (i) => setState(() => _currentIndex = i),
        type: BottomNavigationBarType.fixed,
        selectedItemColor: AppTheme.primary,
        unselectedItemColor: Colors.grey,
        items: _navItems,
      ),
    );
  }
}