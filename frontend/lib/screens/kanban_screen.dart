import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../models/models.dart';
import '../state/providers.dart';
import '../theme.dart';
import '../widgets/view_header.dart';

/// T1 뷰: 고객사 프로젝트 칸반. 카드 드래그로 상태 변경 + 검색/필터/정렬.
class KanbanScreen extends ConsumerStatefulWidget {
  final AgentInfo agent;
  final VoidCallback onChanged;
  const KanbanScreen({super.key, required this.agent, required this.onChanged});
  @override
  ConsumerState<KanbanScreen> createState() => _KanbanScreenState();
}

// (status, label, accent)
const _columns = <(String, String, Color)>[
  ('storyboard', '스토리보드', AppColors.storyboard),
  ('active', '진행 중', AppColors.success),
  ('on_hold', '보류', AppColors.warning),
  ('completed', '완료', AppColors.muted),
  ('cancelled', '취소', AppColors.danger),
];
const _statusLabel = {
  'storyboard': '스토리보드', 'active': '진행 중', 'on_hold': '보류', 'completed': '완료', 'cancelled': '취소'
};
const _issueTypeLabel = {
  'bug': '버그', 'request': '요청', 'delay': '지연', 'question': '문의', 'complaint': '불만', 'general': '일반'
};
const _severityLabel = {'critical': '치명', 'high': '높음', 'medium': '보통', 'low': '낮음'};

class _KanbanScreenState extends ConsumerState<KanbanScreen> {
  List<ProjectInfo> _all = [];
  final Map<String, String> _override = {}; // 낙관적 상태 변경
  final ScrollController _hScroll = ScrollController();
  bool _loading = true;
  String _query = '';
  String _categoryFilter = '';
  String _sortBy = 'updated';

  String get _titleField => (widget.agent.config['card_title_field'] ?? 'client').toString();

  @override
  void initState() {
    super.initState();
    _load();
  }

  @override
  void dispose() {
    _hScroll.dispose();
    super.dispose();
  }

  Future<void> _load() async {
    setState(() => _loading = true);
    try {
      final data = await ref.read(apiProvider).projects(widget.agent.id);
      if (!mounted) return;
      setState(() {
        _all = data;
        _override.clear();
        _loading = false;
      });
    } catch (_) {
      if (mounted) setState(() => _loading = false);
    }
  }

  String _statusOf(ProjectInfo p) => _override[p.id] ?? p.status;

  List<String> _categories() {
    final set = <String>{};
    for (final p in _all) {
      if (p.category != null && p.category!.isNotEmpty) set.add(p.category!);
    }
    final list = set.toList()..sort();
    return list;
  }

  List<ProjectInfo> _visible() {
    final q = _query.toLowerCase();
    final list = _all.where((p) {
      if (q.isNotEmpty &&
          !p.clientName.toLowerCase().contains(q) &&
          !p.title.toLowerCase().contains(q)) {
        return false;
      }
      if (_categoryFilter.isNotEmpty && (p.category ?? '') != _categoryFilter) {
        return false;
      }
      return true;
    }).toList();
    list.sort((a, b) {
      switch (_sortBy) {
        case 'category':
          return (a.category ?? '').compareTo(b.category ?? '');
        case 'client':
          return a.clientName.compareTo(b.clientName);
        default:
          return (b.updatedAt ?? '').compareTo(a.updatedAt ?? '');
      }
    });
    return list;
  }

  Future<void> _moveCard(ProjectInfo p, String newStatus) async {
    if (_statusOf(p) == newStatus) return;
    setState(() => _override[p.id] = newStatus);
    try {
      await ref.read(apiProvider).setProjectStatus(widget.agent.id, p.id, newStatus);
    } catch (e) {
      if (!mounted) return;
      setState(() => _override.remove(p.id));
      ScaffoldMessenger.of(context)
          .showSnackBar(const SnackBar(content: Text('상태 변경에 실패했습니다. 다시 시도해 주세요.')));
    }
  }

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
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
              icon: const Icon(Icons.refresh_rounded),
              onPressed: _load,
            ),
          ],
        ),
        _toolbar(),
        if (!_loading) _statRow(),
        Expanded(
          child: _loading
              ? const Center(child: CircularProgressIndicator())
              : _kanban(),
        ),
      ],
    );
  }

  Widget _toolbar() {
    return Padding(
      padding: const EdgeInsets.fromLTRB(20, 4, 20, 12),
      child: Wrap(
        spacing: 10,
        runSpacing: 10,
        crossAxisAlignment: WrapCrossAlignment.center,
        children: [
          SizedBox(
            width: 240,
            child: TextField(
              decoration: const InputDecoration(
                hintText: '고객사 / 프로젝트 검색…',
                prefixIcon: Icon(Icons.search_rounded, size: 20),
              ),
              onChanged: (v) => setState(() => _query = v),
            ),
          ),
          _dropdown(_categoryFilter, {
            '': '전체 분류',
            for (final c in _categories()) c: c,
          }, (v) => setState(() => _categoryFilter = v)),
          _dropdown(_sortBy, const {
            'updated': '최근 업데이트 순',
            'category': '분류 순',
            'client': '고객사명 순',
          }, (v) => setState(() => _sortBy = v)),
        ],
      ),
    );
  }

  Widget _dropdown(String value, Map<String, String> items, void Function(String) onCh) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10),
      decoration: BoxDecoration(
        color: AppColors.surface,
        border: Border.all(color: AppColors.line),
        borderRadius: BorderRadius.circular(kRadius),
      ),
      child: DropdownButtonHideUnderline(
        child: DropdownButton<String>(
          value: value,
          isDense: true,
          borderRadius: BorderRadius.circular(kRadius),
          style: const TextStyle(fontSize: 14, color: AppColors.ink),
          items: [
            for (final e in items.entries) DropdownMenuItem(value: e.key, child: Text(e.value)),
          ],
          onChanged: (v) => onCh(v ?? ''),
        ),
      ),
    );
  }

  Widget _statRow() {
    final vis = _visible();
    final active = vis.where((p) => _statusOf(p) == 'active').length;
    final onHold = vis.where((p) => _statusOf(p) == 'on_hold').length;
    final withIssues = vis.where((p) => p.issues.any((i) => i.status != 'resolved')).length;
    Widget box(String v, String l, {Color? color}) => Container(
          padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 12),
          decoration: BoxDecoration(
            color: AppColors.surface,
            border: Border.all(color: AppColors.line),
            borderRadius: BorderRadius.circular(kRadius),
          ),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(v, style: TextStyle(fontSize: 24, fontWeight: FontWeight.w800, color: color ?? AppColors.primary)),
              Text(l, style: const TextStyle(fontSize: 13, color: AppColors.muted, fontWeight: FontWeight.w600)),
            ],
          ),
        );
    return Padding(
      padding: const EdgeInsets.fromLTRB(20, 0, 20, 12),
      child: Wrap(spacing: 12, runSpacing: 12, children: [
        box('${vis.length}', '전체 이슈'),
        box('$active', '진행 중'),
        box('$onHold', '보류'),
        box('$withIssues', '미해결 이슈', color: AppColors.danger),
      ]),
    );
  }

  Widget _kanban() {
    final vis = _visible();
    return LayoutBuilder(
      builder: (context, constraints) {
        final colHeight = (constraints.maxHeight - 24).clamp(160.0, double.infinity);
        return Scrollbar(
          controller: _hScroll,
          thumbVisibility: true,
          child: SingleChildScrollView(
            controller: _hScroll,
            scrollDirection: Axis.horizontal,
            padding: const EdgeInsets.fromLTRB(20, 0, 20, 12),
            child: Row(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                for (final c in _columns)
                  _column(c.$1, c.$2, c.$3, vis.where((p) => _statusOf(p) == c.$1).toList(), colHeight),
              ],
            ),
          ),
        );
      },
    );
  }

  Widget _column(String status, String label, Color accent, List<ProjectInfo> cards, double height) {
    return Container(
      width: 300,
      height: height,
      margin: const EdgeInsets.only(right: 16),
      decoration: BoxDecoration(
        color: AppColors.gray100,
        border: Border.all(color: AppColors.line),
        borderRadius: BorderRadius.circular(kRadius),
      ),
      child: Column(
        children: [
          Container(
            height: 3,
            decoration: BoxDecoration(
              color: accent,
              borderRadius: const BorderRadius.vertical(top: Radius.circular(kRadius)),
            ),
          ),
          Padding(
            padding: const EdgeInsets.fromLTRB(14, 12, 14, 12),
            child: Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                Text(label, style: const TextStyle(fontWeight: FontWeight.w700, fontSize: 14)),
                Container(
                  padding: const EdgeInsets.symmetric(horizontal: 9, vertical: 1),
                  decoration: BoxDecoration(
                    color: AppColors.surface,
                    border: Border.all(color: AppColors.line),
                    borderRadius: BorderRadius.circular(999),
                  ),
                  child: Text('${cards.length}',
                      style: const TextStyle(fontSize: 12, fontWeight: FontWeight.w700, color: AppColors.muted)),
                ),
              ],
            ),
          ),
          Expanded(
            child: DragTarget<String>(
              onWillAcceptWithDetails: (_) => true,
              onAcceptWithDetails: (d) {
                final p = _all.firstWhere((x) => x.id == d.data);
                _moveCard(p, status);
              },
              builder: (context, candidate, rejected) {
                final over = candidate.isNotEmpty;
                return Container(
                  margin: const EdgeInsets.fromLTRB(8, 0, 8, 8),
                  padding: const EdgeInsets.all(4),
                  decoration: BoxDecoration(
                    color: over ? const Color(0xFFE8F4FD) : Colors.transparent,
                    borderRadius: BorderRadius.circular(6),
                    border: over ? Border.all(color: AppColors.primary, width: 1.5) : null,
                  ),
                  child: cards.isEmpty
                      ? const Center(
                          child: Text('카드를 여기로 드래그',
                              style: TextStyle(fontSize: 13, color: AppColors.muted, fontWeight: FontWeight.w500)),
                        )
                      : ListView(
                          padding: EdgeInsets.zero,
                          children: [for (final p in cards) _draggableCard(p)],
                        ),
                );
              },
            ),
          ),
        ],
      ),
    );
  }

  Widget _draggableCard(ProjectInfo p) {
    final card = _card(p);
    return Padding(
      padding: const EdgeInsets.only(bottom: 8),
      child: Draggable<String>(
        data: p.id,
        feedback: Material(
          color: Colors.transparent,
          child: SizedBox(width: 276, child: _card(p, elevated: true)),
        ),
        childWhenDragging: Opacity(opacity: 0.4, child: card),
        child: card,
      ),
    );
  }

  Widget _card(ProjectInfo p, {bool elevated = false}) {
    final openIssues = p.issues.where((i) => i.status != 'resolved').toList();
    return Material(
      color: AppColors.surface,
      borderRadius: BorderRadius.circular(kRadius),
      elevation: elevated ? 6 : 0,
      shadowColor: Colors.black26,
      child: InkWell(
        borderRadius: BorderRadius.circular(kRadius),
        onTap: () => _openDetail(p),
        child: Container(
          decoration: BoxDecoration(
            border: Border.all(color: AppColors.line),
            borderRadius: BorderRadius.circular(kRadius),
          ),
          padding: const EdgeInsets.all(14),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(_cardPrimary(p), style: const TextStyle(fontWeight: FontWeight.w700, fontSize: 15)),
                        Text(_cardSecondary(p),
                            style: const TextStyle(fontSize: 13, color: AppColors.muted, fontWeight: FontWeight.w500)),
                      ],
                    ),
                  ),
                  Container(
                    width: 8, height: 8, margin: const EdgeInsets.only(top: 4, left: 6),
                    decoration: BoxDecoration(color: _priorityColor(p.priority), shape: BoxShape.circle),
                  ),
                ],
              ),
              const SizedBox(height: 10),
              Wrap(spacing: 6, runSpacing: 6, children: [
                if (p.category != null && p.category!.isNotEmpty)
                  _badge(p.category!, const Color(0xFFE8F4FD), const Color(0xFF0563A5)),
                _statusBadge(_statusOf(p)),
              ]),
              if (p.latestUpdate != null && p.latestUpdate!.isNotEmpty) ...[
                const SizedBox(height: 10),
                Container(
                  padding: const EdgeInsets.only(left: 8),
                  decoration: const BoxDecoration(border: Border(left: BorderSide(color: AppColors.line, width: 3))),
                  child: Text(p.latestUpdate!,
                      maxLines: 3, overflow: TextOverflow.ellipsis,
                      style: const TextStyle(fontSize: 13, color: AppColors.muted)),
                ),
              ],
              if (openIssues.isNotEmpty) ...[
                const SizedBox(height: 10),
                Wrap(spacing: 6, runSpacing: 6, children: [
                  for (final i in openIssues.take(3))
                    _badge('${_issueTypeLabel[i.type] ?? i.type}: ${i.summary.length > 20 ? '${i.summary.substring(0, 20)}…' : i.summary}',
                        const Color(0xFFFDE8E8), AppColors.danger),
                ]),
              ],
              if (p.updatedAt != null) ...[
                const SizedBox(height: 10),
                Align(
                  alignment: Alignment.centerRight,
                  child: Text(_fmtDate(p.updatedAt),
                      style: const TextStyle(fontSize: 12, color: AppColors.muted, fontWeight: FontWeight.w500)),
                ),
              ],
            ],
          ),
        ),
      ),
    );
  }

  String _cardPrimary(ProjectInfo p) => switch (_titleField) {
        'category' => (p.category?.isNotEmpty ?? false) ? p.category! : '(분류 없음)',
        'title' => p.title,
        _ => p.clientName,
      };
  String _cardSecondary(ProjectInfo p) => switch (_titleField) {
        'title' => p.clientName,
        _ => p.title,
      };

  Widget _badge(String text, Color bg, Color fg) => Container(
        padding: const EdgeInsets.symmetric(horizontal: 9, vertical: 3),
        decoration: BoxDecoration(color: bg, borderRadius: BorderRadius.circular(999)),
        child: Text(text, style: TextStyle(fontSize: 12, color: fg, fontWeight: FontWeight.w600)),
      );

  Widget _statusBadge(String status) {
    const map = {
      'storyboard': (Color(0xFFF3E8FF), AppColors.storyboard),
      'active': (Color(0xFFE6F4EA), AppColors.success),
      'on_hold': (Color(0xFFFFF3CD), Color(0xFF856404)),
      'completed': (AppColors.gray100, AppColors.muted),
      'cancelled': (Color(0xFFFDE8E8), AppColors.danger),
    };
    final (bg, fg) = map[status] ?? (AppColors.gray100, AppColors.muted);
    return _badge(_statusLabel[status] ?? status, bg, fg);
  }

  Color _priorityColor(String? p) => switch (p) {
        'critical' => AppColors.danger,
        'high' => AppColors.warning,
        'low' => AppColors.muted,
        _ => AppColors.primary,
      };

  String _fmtDate(String? iso) {
    if (iso == null) return '';
    final dt = DateTime.tryParse(iso);
    if (dt == null) return '';
    final k = dt.toUtc().add(const Duration(hours: 9));
    String two(int n) => n.toString().padLeft(2, '0');
    return '${two(k.month)}/${two(k.day)} ${two(k.hour)}:${two(k.minute)}';
  }

  void _openDetail(ProjectInfo p) {
    showDialog(
      context: context,
      builder: (_) => AlertDialog(
        title: Text('${p.clientName} — ${p.title}', style: const TextStyle(fontSize: 17)),
        content: SizedBox(
          width: 460,
          child: SingleChildScrollView(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              mainAxisSize: MainAxisSize.min,
              children: [
                Wrap(spacing: 6, runSpacing: 6, children: [
                  if (p.category != null && p.category!.isNotEmpty)
                    _badge(p.category!, const Color(0xFFE8F4FD), const Color(0xFF0563A5)),
                  _statusBadge(_statusOf(p)),
                ]),
                if (p.latestUpdate != null && p.latestUpdate!.isNotEmpty) ...[
                  const SizedBox(height: 12),
                  Text(p.latestUpdate!,
                      style: const TextStyle(fontSize: 14, color: AppColors.ink, fontWeight: FontWeight.w500)),
                ],
                const SizedBox(height: 16),
                const Text('이슈 목록', style: TextStyle(fontWeight: FontWeight.w700, fontSize: 14)),
                const SizedBox(height: 8),
                if (p.issues.isEmpty)
                  const Text('이슈 없음', style: TextStyle(fontSize: 13, color: AppColors.muted))
                else
                  for (final i in p.issues)
                    Container(
                      margin: const EdgeInsets.only(bottom: 8),
                      padding: const EdgeInsets.all(10),
                      decoration: BoxDecoration(
                        border: Border.all(color: AppColors.line),
                        borderRadius: BorderRadius.circular(6),
                      ),
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text(i.summary, style: const TextStyle(fontSize: 14, fontWeight: FontWeight.w500)),
                          const SizedBox(height: 4),
                          Text(
                            '유형: ${_issueTypeLabel[i.type] ?? i.type} · 심각도: ${_severityLabel[i.severity] ?? i.severity} · '
                            '상태: ${i.status == 'resolved' ? '해결됨' : i.status == 'in_progress' ? '처리 중' : '미해결'}',
                            style: const TextStyle(fontSize: 13, color: AppColors.muted, fontWeight: FontWeight.w500),
                          ),
                        ],
                      ),
                    ),
              ],
            ),
          ),
        ),
        actions: [TextButton(onPressed: () => Navigator.pop(context), child: const Text('닫기'))],
      ),
    );
  }

  // ── 드라이런: 최신 메일 1건 분류(저장 안 함) 결과/오류 표시 ──
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
    Navigator.of(context).pop();
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
            _detailRow('고객사', s['client']),
            _detailRow('프로젝트', s['project']),
            _detailRow('요약', s['summary']),
            const SizedBox(height: 8),
            const Text('※ 미리보기입니다. 실제 프로젝트/이슈에는 저장되지 않았습니다.',
                style: TextStyle(fontSize: 12, color: AppColors.muted)),
          ],
        );
      }
    }
    showDialog(
      context: context,
      builder: (_) => AlertDialog(
        title: const Text('드라이런 결과'),
        content: SizedBox(width: 420, child: SingleChildScrollView(child: body)),
        actions: [TextButton(onPressed: () => Navigator.pop(context), child: const Text('닫기'))],
      ),
    );
  }

  Widget _detailRow(String k, Object? v) => Padding(
        padding: const EdgeInsets.symmetric(vertical: 3),
        child: Row(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            SizedBox(width: 64, child: Text(k, style: const TextStyle(color: AppColors.muted))),
            Expanded(child: Text('${v ?? '-'}')),
          ],
        ),
      );
}
