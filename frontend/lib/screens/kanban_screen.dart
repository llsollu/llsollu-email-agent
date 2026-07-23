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

  /// 드라이런: 최신 메일 1건을 분류(저장 안 함)하고 결과/오류를 다이얼로그로 표시.
  Future<void> _dryRun() async {
    final api = ref.read(apiProvider);
    final messenger = ScaffoldMessenger.of(context);
    Set<String> before;
    try {
      before = (await api.runs(widget.agent.id)).map((r) => r.id).toSet();
      await api.runNow(widget.agent.id, dryRun: true);
    } catch (e) {
      messenger.showSnackBar(SnackBar(content: Text('실행 요청 실패: $e')));
      return;
    }
    if (!mounted) return;

    // 진행 중 다이얼로그
    showDialog(
      context: context,
      barrierDismissible: false,
      builder: (_) => const AlertDialog(
        content: Row(children: [
          SizedBox(width: 20, height: 20, child: CircularProgressIndicator(strokeWidth: 2)),
          SizedBox(width: 16),
          Expanded(child: Text('최신 메일 1건을 분류하는 중…')),
        ]),
      ),
    );

    RunInfo? result;
    for (var i = 0; i < 20; i++) {
      await Future.delayed(const Duration(milliseconds: 1500));
      try {
        final runs = await api.runs(widget.agent.id);
        final done = runs.where((r) =>
            r.triggerSource == 'manual' && !before.contains(r.id) && r.status != 'running');
        if (done.isNotEmpty) {
          result = done.first;
          break;
        }
      } catch (_) {}
    }

    if (!mounted) return;
    Navigator.of(context).pop(); // 진행 다이얼로그 닫기
    _showDryRunResult(result);
  }

  void _showDryRunResult(RunInfo? r) {
    late final Widget body;
    if (r == null) {
      body = const Text('결과를 확인하지 못했습니다(시간 초과). 잠시 후 다시 시도해 주세요.');
    } else if (r.status == 'error') {
      final msg = r.error ?? '알 수 없는 오류';
      final hint = msg.contains('timed out') || msg.contains('timeout')
          ? '\n\nLLM 서버에 연결하지 못했습니다. 분류 서버 주소·네트워크 연결을 확인하세요.'
          : '';
      body = Text('분류에 실패했습니다.\n\n$msg$hint');
    } else {
      final s = r.stats;
      if ((s['processed'] ?? 0) == 0) {
        body = const Text('분류할 새 메일이 없습니다.');
      } else {
        body = Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          mainAxisSize: MainAxisSize.min,
          children: [
            _row('고객사', s['client']),
            _row('프로젝트', s['project']),
            _row('요약', s['summary']),
            const SizedBox(height: 8),
            const Text('※ 미리보기입니다. 실제 프로젝트/이슈에는 저장되지 않았습니다.',
                style: TextStyle(fontSize: 12, color: Colors.black54)),
          ],
        );
      }
    }
    showDialog(
      context: context,
      builder: (_) => AlertDialog(
        title: const Text('드라이런 결과'),
        content: SizedBox(width: 420, child: SingleChildScrollView(child: body)),
        actions: [
          TextButton(onPressed: () => Navigator.pop(context), child: const Text('닫기')),
        ],
      ),
    );
  }

  Widget _row(String k, Object? v) => Padding(
        padding: const EdgeInsets.symmetric(vertical: 3),
        child: Row(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            SizedBox(width: 64, child: Text(k, style: const TextStyle(color: Colors.black54))),
            Expanded(child: Text('${v ?? '-'}')),
          ],
        ),
      );

  @override
  Widget build(BuildContext context) {
    return Column(
      children: [
        ViewHeader(
          agent: widget.agent,
          onChanged: widget.onChanged,
          actions: [
            TextButton.icon(
              icon: const Icon(Icons.play_arrow_rounded),
              label: const Text('지금 실행(드라이런)'),
              onPressed: _dryRun,
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
