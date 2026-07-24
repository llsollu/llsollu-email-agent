import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../models/models.dart';
import '../state/providers.dart';
import '../theme.dart';
import '../widgets/schedule_util.dart';
import '../widgets/view_header.dart';

/// T2 뷰: 트리거·규칙·참조파일·최근 로그 + 스케줄 on/off.
class SchedulerScreen extends ConsumerStatefulWidget {
  final AgentInfo agent;
  final VoidCallback onChanged;
  const SchedulerScreen({super.key, required this.agent, required this.onChanged});
  @override
  ConsumerState<SchedulerScreen> createState() => _SchedulerScreenState();
}

class _SchedulerScreenState extends ConsumerState<SchedulerScreen> {
  late Future<_PanelData> _future;

  @override
  void initState() {
    super.initState();
    _reload();
  }

  void _reload() {
    final api = ref.read(apiProvider);
    _future = () async {
      final runs = await api.runs(widget.agent.id);
      final schedule = await api.schedule(widget.agent.id);
      return _PanelData(runs, schedule);
    }();
  }

  @override
  Widget build(BuildContext context) {
    final cfg = widget.agent.config;
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
              onPressed: () async {
                final messenger = ScaffoldMessenger.of(context);
                await ref.read(apiProvider).runNow(widget.agent.id, dryRun: true);
                messenger.showSnackBar(const SnackBar(content: Text('드라이런 실행을 큐에 넣었습니다')));
                setState(_reload);
              },
            ),
          ],
        ),
        Expanded(
          child: FutureBuilder<_PanelData>(
            future: _future,
            builder: (context, snap) {
              if (!snap.hasData) return const Center(child: CircularProgressIndicator());
              final data = snap.data!;
              return ListView(
                padding: const EdgeInsets.all(20),
                children: [
                  _section('트리거 / 규칙', [
                    _kv('확인 주기', humanFromCron(cfg['cron']?.toString())),
                    _kv('참조 파일 URL', cfg['sharepoint_file_url'] ?? '-'),
                    _kv('발신자', cfg['mail_sender'] ?? '-'),
                    _kv('수신자', cfg['recipient_email'] ?? '-'),
                    if ((cfg['cc_email']?.toString().isNotEmpty ?? false))
                      _kv('참조', cfg['cc_email']),
                    _kv('발송기준일',
                        (cfg['date_column']?.toString().isNotEmpty ?? false)
                            ? cfg['date_column']
                            : '지정 안 함 (주기마다 전체 발송)'),
                  ]),
                  const SizedBox(height: 12),
                  if (data.schedule != null)
                    Card(
                      child: SwitchListTile(
                        title: const Text('스케줄 활성화'),
                        subtitle: Text(
                            '확인 주기: ${humanFromCron(cfg['cron']?.toString())}\n'
                            '다음 실행: ${_fmtKst(data.schedule!['next_run_at'])}'),
                        isThreeLine: true,
                        value: data.schedule!['enabled'] == true,
                        onChanged: (v) async {
                          await ref.read(apiProvider).toggleSchedule(widget.agent.id, v);
                          setState(_reload);
                        },
                      ),
                    ),
                  const SizedBox(height: 12),
                  const Text('최근 실행 로그', style: TextStyle(fontWeight: FontWeight.w700, fontSize: 15)),
                  for (final r in data.runs) _runTile(r),
                  if (data.runs.isEmpty) const Padding(
                    padding: EdgeInsets.all(8), child: Text('아직 실행 이력이 없습니다')),
                ],
              );
            },
          ),
        ),
      ],
    );
  }

  Widget _section(String title, List<Widget> children) => Card(
        child: Padding(
          padding: const EdgeInsets.all(12),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(title, style: const TextStyle(fontWeight: FontWeight.w700, fontSize: 15)),
              const SizedBox(height: 8),
              ...children,
            ],
          ),
        ),
      );

  Widget _kv(String k, Object v) => Padding(
        padding: const EdgeInsets.symmetric(vertical: 3),
        child: Row(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            SizedBox(
                width: 140,
                child: Text(k,
                    style: const TextStyle(
                        fontSize: 14, color: AppColors.muted, fontWeight: FontWeight.w600))),
            Expanded(
                child: Text('$v',
                    style: const TextStyle(fontSize: 14, fontWeight: FontWeight.w500))),
          ],
        ),
      );

  static const _triggerLabel = {'schedule': '예약 실행', 'manual': '수동 실행', 'email': '메일 수신'};
  static const _statusLabel = {'ok': '성공', 'error': '오류', 'running': '실행 중'};

  Widget _runTile(RunInfo r) {
    final color = r.status == 'ok'
        ? Colors.green
        : r.status == 'error'
            ? Colors.red
            : Colors.orange;
    final s = r.stats;
    final isDry = s['dry_run'] == true;
    final total = s['total'], targets = s['targets'], sent = s['sent'], failed = s['failed'];

    final parts = <String>[];
    if (total != null) parts.add('총 $total건');
    if (targets != null) parts.add('발송 대상 $targets건');
    if (isDry) {
      parts.add('드라이런(실제 발송 안 함)');
    } else {
      if (sent != null) parts.add('발송 $sent건');
      if (failed != null && failed != 0) parts.add('실패 $failed건');
    }
    final summary = parts.isEmpty ? '기록 없음' : parts.join(' · ');

    // 이벤트 중 실패/드라이런 상세를 사람이 읽는 문장으로.
    final details = <String>[];
    final events = (s['events'] as List?) ?? [];
    for (final e in events.whereType<Map>()) {
      switch (e['event']) {
        case 'send_failed':
          details.add('· 발송 실패 (${e['to']}): ${e['error']}');
          break;
        case 'dry_run':
          details.add('· [미리보기] 제목: ${e['subject']}');
          break;
      }
    }

    return Card(
      child: ListTile(
        leading: Icon(Icons.circle, color: color, size: 14),
        title: Text('${_triggerLabel[r.triggerSource] ?? r.triggerSource} · '
            '${_statusLabel[r.status] ?? r.status}', style: const TextStyle(fontWeight: FontWeight.w700)),
        subtitle: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(summary, style: const TextStyle(fontSize: 13, fontWeight: FontWeight.w500)),
            if (r.error != null)
              Text('오류: ${r.error}', style: const TextStyle(color: AppColors.danger, fontWeight: FontWeight.w600)),
            for (final d in details.take(5))
              Text(d, style: const TextStyle(fontSize: 13, color: AppColors.muted, fontWeight: FontWeight.w500)),
          ],
        ),
      ),
    );
  }
}

/// 서버가 내려주는 next_run_at(UTC ISO8601)을 KST(+9)로 변환해 표시.
/// 저장/계산은 UTC 기준이지만 사용자에게는 한국시간으로 보여야 오해가 없다.
String _fmtKst(Object? iso) {
  if (iso == null) return '-';
  final dt = DateTime.tryParse(iso.toString());
  if (dt == null) return iso.toString();
  final k = dt.toUtc().add(const Duration(hours: 9));
  String two(int n) => n.toString().padLeft(2, '0');
  return '${k.year}-${two(k.month)}-${two(k.day)} '
      '${two(k.hour)}:${two(k.minute)} (KST)';
}

class _PanelData {
  final List<RunInfo> runs;
  final Map<String, dynamic>? schedule;
  _PanelData(this.runs, this.schedule);
}
