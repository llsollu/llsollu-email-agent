import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../models/models.dart';
import '../state/providers.dart';
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
              icon: const Icon(Icons.play_arrow),
              label: const Text('지금 실행(드라이런)'),
              onPressed: () async {
                await ref.read(apiProvider).runNow(widget.agent.id, dryRun: true);
                if (mounted) {
                  ScaffoldMessenger.of(context)
                      .showSnackBar(const SnackBar(content: Text('드라이런 실행을 큐에 넣었습니다')));
                }
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
                    _kv('실행 스케줄(cron)', cfg['cron'] ?? '(기본)'),
                    _kv('참조 파일 URL', cfg['sharepoint_file_url'] ?? '-'),
                    _kv('발신 계정', cfg['mail_sender'] ?? '-'),
                    _kv('수신자', cfg['recipient_email'] ?? '-'),
                    _kv('누락 알림', cfg['alert_email'] ?? '-'),
                  ]),
                  const SizedBox(height: 12),
                  if (data.schedule != null)
                    Card(
                      child: SwitchListTile(
                        title: const Text('스케줄 활성화'),
                        subtitle: Text('다음 실행: ${_fmtKst(data.schedule!['next_run_at'])}'),
                        value: data.schedule!['enabled'] == true,
                        onChanged: (v) async {
                          await ref.read(apiProvider).toggleSchedule(widget.agent.id, v);
                          setState(_reload);
                        },
                      ),
                    ),
                  const SizedBox(height: 12),
                  const Text('최근 실행 로그', style: TextStyle(fontWeight: FontWeight.bold)),
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
              Text(title, style: const TextStyle(fontWeight: FontWeight.bold)),
              const SizedBox(height: 8),
              ...children,
            ],
          ),
        ),
      );

  Widget _kv(String k, Object v) => Padding(
        padding: const EdgeInsets.symmetric(vertical: 2),
        child: Row(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            SizedBox(width: 140, child: Text(k, style: const TextStyle(color: Colors.black54))),
            Expanded(child: Text('$v')),
          ],
        ),
      );

  Widget _runTile(RunInfo r) {
    final color = r.status == 'ok'
        ? Colors.green
        : r.status == 'error'
            ? Colors.red
            : Colors.orange;
    return Card(
      child: ListTile(
        leading: Icon(Icons.circle, color: color, size: 14),
        title: Text('${r.triggerSource} · ${r.status}'),
        subtitle: Text(r.error ?? r.stats.toString(), maxLines: 2, overflow: TextOverflow.ellipsis),
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
