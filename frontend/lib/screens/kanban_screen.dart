import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../models/models.dart';
import '../state/providers.dart';
import '../widgets/view_header.dart';

/// T1 뷰: 고객사 프로젝트 칸반.
class KanbanScreen extends ConsumerStatefulWidget {
  final AgentInfo agent;
  final VoidCallback onChanged;
  const KanbanScreen({super.key, required this.agent, required this.onChanged});
  @override
  ConsumerState<KanbanScreen> createState() => _KanbanScreenState();
}

const _columns = {
  'active': '진행 중',
  'on_hold': '보류',
  'completed': '완료',
  'cancelled': '취소',
};

class _KanbanScreenState extends ConsumerState<KanbanScreen> {
  late Future<List<ProjectInfo>> _future;

  @override
  void initState() {
    super.initState();
    _reload();
  }

  void _reload() {
    _future = ref.read(apiProvider).projects(widget.agent.id);
  }

  Future<void> _move(ProjectInfo p, String status) async {
    await ref.read(apiProvider).setProjectStatus(widget.agent.id, p.id, status);
    setState(_reload);
  }

  @override
  Widget build(BuildContext context) {
    return Column(
      children: [
        ViewHeader(
          agent: widget.agent,
          onChanged: widget.onChanged,
          actions: [
            TextButton.icon(
              icon: const Icon(Icons.play_arrow),
              label: const Text('지금 실행(드라이런)'),
              onPressed: () async {
                await ref.read(apiProvider).runNow(widget.agent.id, dryRun: true);
                if (context.mounted) {
                  ScaffoldMessenger.of(context).showSnackBar(
                      const SnackBar(content: Text('드라이런 실행을 큐에 넣었습니다 (최신 메일 1건 분류, 저장 안 함)')));
                }
              },
            ),
            IconButton(
              tooltip: '새로고침',
              icon: const Icon(Icons.refresh),
              onPressed: () => setState(_reload),
            ),
          ],
        ),
        Expanded(
          child: FutureBuilder<List<ProjectInfo>>(
            future: _future,
            builder: (context, snap) {
              if (!snap.hasData) {
                return const Center(child: CircularProgressIndicator());
              }
              final projects = snap.data!;
              return SingleChildScrollView(
                scrollDirection: Axis.horizontal,
                padding: const EdgeInsets.all(12),
                child: Row(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    for (final entry in _columns.entries)
                      _column(entry.key, entry.value,
                          projects.where((p) => p.status == entry.key).toList()),
                  ],
                ),
              );
            },
          ),
        ),
      ],
    );
  }

  Widget _column(String status, String label, List<ProjectInfo> items) {
    return Container(
      width: 300,
      margin: const EdgeInsets.symmetric(horizontal: 6),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Padding(
            padding: const EdgeInsets.all(8),
            child: Text('$label (${items.length})',
                style: const TextStyle(fontWeight: FontWeight.bold)),
          ),
          for (final p in items) _card(p, status),
        ],
      ),
    );
  }

  Widget _card(ProjectInfo p, String status) {
    final openIssues = p.issues.where((i) => i.status != 'resolved').toList();
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(10),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Expanded(
                  child: Text(p.clientName, style: const TextStyle(fontWeight: FontWeight.bold)),
                ),
                PopupMenuButton<String>(
                  icon: const Icon(Icons.more_vert, size: 18),
                  onSelected: (s) => _move(p, s),
                  itemBuilder: (_) => [
                    for (final e in _columns.entries)
                      if (e.key != status) PopupMenuItem(value: e.key, child: Text('→ ${e.value}')),
                  ],
                ),
              ],
            ),
            Text(p.title, style: const TextStyle(fontSize: 13)),
            if (p.latestUpdate != null) ...[
              const SizedBox(height: 4),
              Text(p.latestUpdate!,
                  style: const TextStyle(fontSize: 11, color: Colors.black54),
                  maxLines: 2, overflow: TextOverflow.ellipsis),
            ],
            for (final i in openIssues.take(3))
              Padding(
                padding: const EdgeInsets.only(top: 4),
                child: Chip(
                  label: Text('${i.type}: ${i.summary}',
                      style: const TextStyle(fontSize: 10)),
                  visualDensity: VisualDensity.compact,
                ),
              ),
          ],
        ),
      ),
    );
  }
}
