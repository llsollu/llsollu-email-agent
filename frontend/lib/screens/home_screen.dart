import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../models/models.dart';
import '../state/providers.dart';
import 'add_agent_screen.dart';
import 'kanban_screen.dart';
import 'scheduler_screen.dart';

/// 메인: 좌측 Agent 목록 + [+ 추가], 우측 선택 에이전트 뷰.
class HomeScreen extends ConsumerStatefulWidget {
  const HomeScreen({super.key});
  @override
  ConsumerState<HomeScreen> createState() => _HomeScreenState();
}

class _HomeScreenState extends ConsumerState<HomeScreen> {
  AgentInfo? _selected;

  @override
  Widget build(BuildContext context) {
    final agentsAsync = ref.watch(agentsProvider);
    final user = ref.watch(currentUserProvider);

    return Scaffold(
      body: Row(
        children: [
          // ── 좌측 사이드바 ──
          SizedBox(
            width: 280,
            child: Material(
              color: Theme.of(context).colorScheme.surfaceContainerHighest,
              child: Column(
                children: [
                  const SizedBox(height: 16),
                  ListTile(
                    leading: const Icon(Icons.hub),
                    title: const Text('내 에이전트',
                        style: TextStyle(fontWeight: FontWeight.bold)),
                    subtitle: Text(user?.email ?? ''),
                  ),
                  const Divider(),
                  Expanded(
                    child: agentsAsync.when(
                      data: (agents) => ListView(
                        children: [
                          for (final a in agents)
                            ListTile(
                              selected: _selected?.id == a.id,
                              leading: Icon(_iconFor(a.viewType)),
                              title: Text(a.name),
                              subtitle: Text(_statusLabel(a.status)),
                              onTap: () => setState(() => _selected = a),
                            ),
                        ],
                      ),
                      loading: () => const Center(child: CircularProgressIndicator()),
                      error: (e, _) => Center(child: Text('$e')),
                    ),
                  ),
                  const Divider(),
                  Padding(
                    padding: const EdgeInsets.all(12),
                    child: FilledButton.icon(
                      icon: const Icon(Icons.add),
                      label: const Text('추가'),
                      onPressed: _openAddAgent,
                    ),
                  ),
                  TextButton.icon(
                    icon: const Icon(Icons.logout),
                    label: const Text('로그아웃'),
                    onPressed: () async {
                      await ref.read(apiProvider).logout();
                      ref.read(currentUserProvider.notifier).state = null;
                    },
                  ),
                  const SizedBox(height: 8),
                ],
              ),
            ),
          ),
          // ── 우측 콘텐츠 ──
          Expanded(child: _content()),
        ],
      ),
    );
  }

  Widget _content() {
    final a = _selected;
    if (a == null) {
      return const Center(child: Text('좌측에서 에이전트를 선택하거나 추가하세요'));
    }
    switch (a.viewType) {
      case 'kanban':
        return KanbanScreen(agent: a, onChanged: _refresh);
      case 'scheduler_panel':
        return SchedulerScreen(agent: a, onChanged: _refresh);
      default:
        return Center(child: Text('알 수 없는 뷰: ${a.viewType}'));
    }
  }

  Future<void> _openAddAgent() async {
    final created = await Navigator.of(context).push<bool>(
      MaterialPageRoute(builder: (_) => const AddAgentScreen()),
    );
    if (created == true) _refresh();
  }

  void _refresh() => ref.invalidate(agentsProvider);

  IconData _iconFor(String? viewType) =>
      viewType == 'kanban' ? Icons.view_kanban : Icons.schedule_send;

  String _statusLabel(String s) => switch (s) {
        'configuring' => '구성 중…',
        'active' => '실행 중',
        'paused' => '일시정지',
        'error' => '오류',
        _ => s,
      };
}
