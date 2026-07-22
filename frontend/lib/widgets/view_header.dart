import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../models/models.dart';
import 'settings_dialog.dart';

/// 모든 뷰 상단 공통 헤더: 제목 + ⚙️ 설정 버튼.
class ViewHeader extends ConsumerWidget {
  final AgentInfo agent;
  final VoidCallback onChanged;
  final List<Widget> actions;

  const ViewHeader({
    super.key,
    required this.agent,
    required this.onChanged,
    this.actions = const [],
  });

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    return Padding(
      padding: const EdgeInsets.fromLTRB(20, 16, 12, 8),
      child: Row(
        children: [
          Expanded(
            child: Text(agent.name,
                style: const TextStyle(fontSize: 20, fontWeight: FontWeight.bold)),
          ),
          ...actions,
          IconButton(
            tooltip: '설정',
            icon: const Icon(Icons.settings),
            onPressed: () async {
              final changed = await showAgentSettings(context, ref, agent);
              if (changed == true) onChanged();
            },
          ),
        ],
      ),
    );
  }
}
