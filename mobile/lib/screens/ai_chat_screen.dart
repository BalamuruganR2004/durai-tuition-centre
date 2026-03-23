import 'package:flutter/material.dart';
import '../core/api_service.dart';
import '../core/theme.dart';

class AIChatScreen extends StatefulWidget {
  const AIChatScreen({super.key});
  @override
  State<AIChatScreen> createState() => _AIChatScreenState();
}

class _AIChatScreenState extends State<AIChatScreen> {
  final _messages = <Map<String, String>>[];
  final _ctrl = TextEditingController();
  final _scrollCtrl = ScrollController();
  bool _isTyping = false;

  Future<void> _sendMessage(String text) async {
    if (text.trim().isEmpty) return;
    _ctrl.clear();
    setState(() {
      _messages.add({'role': 'user', 'content': text});
      _isTyping = true;
    });
    _scrollToBottom();

    try {
      final reply = await ApiService.aiChat(text, _messages.sublist(0, _messages.length - 1));
      setState(() {
        _messages.add({'role': 'assistant', 'content': reply});
        _isTyping = false;
      });
      _scrollToBottom();
    } catch (e) {
      setState(() {
        _messages.add({'role': 'assistant', 'content': 'Sorry, I am unavailable right now. Please try again.'});
        _isTyping = false;
      });
    }
  }

  void _scrollToBottom() {
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (_scrollCtrl.hasClients) {
        _scrollCtrl.animateTo(_scrollCtrl.position.maxScrollExtent,
          duration: const Duration(milliseconds: 300), curve: Curves.easeOut);
      }
    });
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Row(children: [
          CircleAvatar(radius: 16, backgroundColor: Colors.white,
            child: Icon(Icons.smart_toy, color: AppTheme.primary, size: 20)),
          SizedBox(width: 8),
          Text('AI Study Assistant'),
        ]),
        backgroundColor: AppTheme.primary,
      ),
      body: Column(
        children: [
          if (_messages.isEmpty) _buildQuickActions(),
          Expanded(
            child: ListView.builder(
              controller: _scrollCtrl,
              padding: const EdgeInsets.all(16),
              itemCount: _messages.length + (_isTyping ? 1 : 0),
              itemBuilder: (context, i) {
                if (i == _messages.length && _isTyping) {
                  return _TypingIndicator();
                }
                final msg = _messages[i];
                final isUser = msg['role'] == 'user';
                return _MessageBubble(message: msg['content']!, isUser: isUser);
              },
            ),
          ),
          _buildInputBar(),
        ],
      ),
    );
  }

  Widget _buildQuickActions() {
    final prompts = [
      'Create a study plan for me',
      'Explain photosynthesis',
      'Help me prepare for exams',
      'What topics should I focus on?',
    ];
    return Container(
      padding: const EdgeInsets.all(16),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Text('Quick Actions', style: TextStyle(fontWeight: FontWeight.bold)),
          const SizedBox(height: 8),
          Wrap(
            spacing: 8, runSpacing: 8,
            children: prompts.map((p) => ActionChip(
              label: Text(p, style: const TextStyle(fontSize: 12)),
              onPressed: () => _sendMessage(p),
            )).toList(),
          ),
        ],
      ),
    );
  }

  Widget _buildInputBar() {
    return Container(
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: Colors.white,
        boxShadow: [BoxShadow(color: Colors.black12, blurRadius: 8, offset: Offset(0, -2))],
      ),
      child: Row(
        children: [
          Expanded(
            child: TextField(
              controller: _ctrl,
              decoration: InputDecoration(
                hintText: 'Ask anything...',
                border: OutlineInputBorder(borderRadius: BorderRadius.circular(24)),
                contentPadding: const EdgeInsets.symmetric(horizontal: 16, vertical: 10),
                isDense: true,
              ),
              onSubmitted: _sendMessage,
              textInputAction: TextInputAction.send,
            ),
          ),
          const SizedBox(width: 8),
          FloatingActionButton.small(
            onPressed: () => _sendMessage(_ctrl.text),
            backgroundColor: AppTheme.primary,
            child: const Icon(Icons.send, color: Colors.white),
          ),
        ],
      ),
    );
  }
}

class _MessageBubble extends StatelessWidget {
  final String message;
  final bool isUser;
  const _MessageBubble({required this.message, required this.isUser});

  @override
  Widget build(BuildContext context) {
    return Align(
      alignment: isUser ? Alignment.centerRight : Alignment.centerLeft,
      child: Container(
        margin: const EdgeInsets.only(bottom: 12),
        padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 10),
        constraints: BoxConstraints(maxWidth: MediaQuery.of(context).size.width * 0.75),
        decoration: BoxDecoration(
          color: isUser ? AppTheme.primary : Colors.grey[100],
          borderRadius: BorderRadius.only(
            topLeft: const Radius.circular(16),
            topRight: const Radius.circular(16),
            bottomLeft: Radius.circular(isUser ? 16 : 4),
            bottomRight: Radius.circular(isUser ? 4 : 16),
          ),
        ),
        child: Text(message,
          style: TextStyle(color: isUser ? Colors.white : Colors.black87)),
      ),
    );
  }
}

class _TypingIndicator extends StatelessWidget {
  @override
  Widget build(BuildContext context) {
    return Align(
      alignment: Alignment.centerLeft,
      child: Container(
        margin: const EdgeInsets.only(bottom: 12),
        padding: const EdgeInsets.all(12),
        decoration: BoxDecoration(
          color: Colors.grey[100],
          borderRadius: BorderRadius.circular(16),
        ),
        child: const Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            Text('AI is thinking', style: TextStyle(color: Colors.grey)),
            SizedBox(width: 8),
            SizedBox(width: 20, height: 20,
              child: CircularProgressIndicator(strokeWidth: 2)),
          ],
        ),
      ),
    );
  }
}