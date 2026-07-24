import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../models/models.dart';
import '../state/providers.dart';
import '../theme.dart';
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
          Container(
            width: 288,
            decoration: const BoxDecoration(
              color: Colors.white,
              border: Border(right: BorderSide(color: AppColors.line)),
            ),
            child: Column(
              children: [
                // 브랜드 헤더
                Container(
                  padding: const EdgeInsets.fromLTRB(20, 28, 20, 20),
                  child: Row(
                    children: [
                      Container(
                        width: 44,
                        height: 44,
                        decoration: BoxDecoration(
                            gradient: kBrandGradient, borderRadius: BorderRadius.circular(13)),
                        child: const Icon(Icons.hub_rounded, color: Colors.white, size: 24),
                      ),
                      const SizedBox(width: 12),
                      Expanded(
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            const Text('Email Agent',
                                style: TextStyle(fontWeight: FontWeight.w800, fontSize: 16)),
                            Text(user?.email ?? '',
                                style: const TextStyle(fontSize: 13, color: AppColors.muted, fontWeight: FontWeight.w500),
                                overflow: TextOverflow.ellipsis),
                          ],
                        ),
                      ),
                    ],
                  ),
                ),
                const Padding(
                  padding: EdgeInsets.fromLTRB(20, 4, 20, 8),
                  child: Align(
                    alignment: Alignment.centerLeft,
                    child: Text('내 에이전트',
                        style: TextStyle(
                            fontSize: 13,
                            fontWeight: FontWeight.w700,
                            color: AppColors.muted,
                            letterSpacing: 0.4)),
                  ),
                ),
                Expanded(
                  child: agentsAsync.when(
                    data: (agents) => agents.isEmpty
                        ? const Center(
                            child: Text('아직 에이전트가 없어요',
                                style: TextStyle(color: AppColors.muted)))
                        : ListView(
                            padding: const EdgeInsets.symmetric(horizontal: 12),
                            children: [for (final a in agents) _navTile(a)],
                          ),
                    loading: () => const Center(child: CircularProgressIndicator()),
                    error: (e, _) => Center(child: Text('$e')),
                  ),
                ),
                const Divider(),
                Padding(
                  padding: const EdgeInsets.fromLTRB(12, 12, 12, 4),
                  child: SizedBox(
                    width: double.infinity,
                    child: FilledButton.icon(
                      icon: const Icon(Icons.add_rounded),
                      label: const Text('에이전트 추가'),
                      onPressed: _openAddAgent,
                    ),
                  ),
                ),
                TextButton.icon(
                  icon: const Icon(Icons.logout_rounded, size: 18),
                  label: const Text('로그아웃'),
                  style: TextButton.styleFrom(foregroundColor: AppColors.muted),
                  onPressed: () async {
                    await ref.read(apiProvider).logout();
                    ref.read(currentUserProvider.notifier).state = null;
                  },
                ),
                const SizedBox(height: 8),
              ],
            ),
          ),
          // ── 우측 콘텐츠 ──
          Expanded(child: _content()),
        ],
      ),
    );
  }

  Widget _navTile(AgentInfo a) {
    final selected = _selected?.id == a.id;
    return Padding(
      padding: const EdgeInsets.only(bottom: 4),
      child: Material(
        color: selected ? AppColors.primary.withValues(alpha: 0.10) : Colors.transparent,
        borderRadius: BorderRadius.circular(12),
        child: InkWell(
          borderRadius: BorderRadius.circular(12),
          onTap: () => setState(() => _selected = a),
          child: Padding(
            padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 10),
            child: Row(
              children: [
                Container(
                  width: 36,
                  height: 36,
                  decoration: BoxDecoration(
                    color: selected ? AppColors.primary : const Color(0xFFE8F4FD),
                    borderRadius: BorderRadius.circular(10),
                  ),
                  child: Icon(_iconFor(a.viewType),
                      size: 20, color: selected ? Colors.white : AppColors.primary),
                ),
                const SizedBox(width: 12),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(a.name,
                          maxLines: 1,
                          overflow: TextOverflow.ellipsis,
                          style: TextStyle(
                              fontWeight: FontWeight.w700,
                              color: selected ? AppColors.primaryDark : AppColors.ink)),
                      Text(_statusLabel(a.status),
                          style: const TextStyle(fontSize: 13, color: AppColors.muted, fontWeight: FontWeight.w500)),
                    ],
                  ),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }

  Widget _content() {
    final a = _selected;
    if (a == null) {
      return Center(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Container(
              width: 72,
              height: 72,
              decoration: BoxDecoration(
                  color: const Color(0xFFE8F4FD), borderRadius: BorderRadius.circular(20)),
              child: const Icon(Icons.auto_awesome_rounded, size: 34, color: AppColors.primary),
            ),
            const SizedBox(height: 16),
            const Text('에이전트를 선택하거나 추가하세요',
                style: TextStyle(fontSize: 16, fontWeight: FontWeight.w700)),
            const SizedBox(height: 4),
            const Text('좌측 목록에서 시작할 수 있어요', style: TextStyle(color: AppColors.muted)),
          ],
        ),
      );
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
      viewType == 'kanban' ? Icons.view_kanban_rounded : Icons.schedule_send_rounded;

  String _statusLabel(String s) => switch (s) {
        'configuring' => '구성 중…',
        'active' => '실행 중',
        'paused' => '일시정지',
        'error' => '오류',
        _ => s,
      };
}
