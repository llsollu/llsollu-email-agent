import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../state/providers.dart';
import '../theme.dart';
import 'schedule_util.dart';

/// 메일 스케줄러 전용 설정 폼.
/// - 생성(wizard=true): 2단계. 1단계 기본정보 → 2단계 데이터/본문/주기.
/// - 편집(wizard=false): 한 화면에 모두 표시.
/// 컬럼명을 드래그(또는 탭)해서 발송기준일·제목·본문에 넣는다. 발신자는 항상 본인 계정.
class MailSchedulerForm extends ConsumerStatefulWidget {
  final String initialName;
  final Map<String, dynamic> initialConfig;
  final bool wizard;
  final bool busy;
  final String submitLabel;
  final void Function(String name, Map<String, dynamic> config) onSubmit;
  final VoidCallback? onDelete;

  const MailSchedulerForm({
    super.key,
    required this.initialName,
    required this.initialConfig,
    required this.onSubmit,
    this.wizard = true,
    this.busy = false,
    this.submitLabel = '생성',
    this.onDelete,
  });

  @override
  ConsumerState<MailSchedulerForm> createState() => _MailSchedulerFormState();
}

class _MailSchedulerFormState extends ConsumerState<MailSchedulerForm> {
  final _name = TextEditingController();
  final _fileUrl = TextEditingController();
  final _recipient = TextEditingController();
  final _subject = TextEditingController();
  final _body = TextEditingController();
  final _subjectFocus = FocusNode();
  final _bodyFocus = FocusNode();
  String _lastFocused = 'body';

  String? _dateColumn;
  Map<String, dynamic> _schedule = {'kind': 'daily', 'hour': 9, 'minute': 0};

  List<String> _columns = [];
  bool _loadingCols = false;
  String? _colsError;

  int _step = 0; // wizard 단계
  String? _stepError;
  String? _dataError;

  String get _senderEmail => ref.read(currentUserProvider)?.email ?? '';

  @override
  void initState() {
    super.initState();
    final c = widget.initialConfig;
    _name.text = widget.initialName;
    _fileUrl.text = (c['sharepoint_file_url'] ?? '').toString();
    _recipient.text = (c['recipient_email'] ?? '').toString();
    _subject.text = (c['subject_template'] ?? '').toString();
    _body.text = (c['body_template'] ?? '').toString();
    final dc = (c['date_column'] ?? '').toString();
    if (dc.isNotEmpty) _dateColumn = dc;
    _schedule = (c['schedule_ui'] is Map)
        ? Map<String, dynamic>.from(c['schedule_ui'])
        : (scheduleUiFromCron(c['cron']?.toString()) ?? _schedule);

    _subjectFocus.addListener(() {
      if (_subjectFocus.hasFocus) _lastFocused = 'subject';
    });
    _bodyFocus.addListener(() {
      if (_bodyFocus.hasFocus) _lastFocused = 'body';
    });

    if (!widget.wizard && _fileUrl.text.trim().isNotEmpty) {
      _loadColumns();
    }
  }

  @override
  void dispose() {
    for (final c in [_name, _fileUrl, _recipient, _subject, _body]) {
      c.dispose();
    }
    _subjectFocus.dispose();
    _bodyFocus.dispose();
    super.dispose();
  }

  Future<void> _loadColumns() async {
    final url = _fileUrl.text.trim();
    if (url.isEmpty) return;
    setState(() {
      _loadingCols = true;
      _colsError = null;
    });
    try {
      final res = await ref.read(apiProvider).mailSchedulerColumns(url);
      setState(() => _columns = (res['columns'] as List).cast<String>());
    } catch (e) {
      setState(() => _colsError = '$e'.replaceFirst('Exception: ', ''));
    } finally {
      if (mounted) setState(() => _loadingCols = false);
    }
  }

  Map<String, dynamic> _buildConfig() => {
        'sharepoint_file_url': _fileUrl.text.trim(),
        'mail_sender': _senderEmail, // 발신자는 항상 본인 계정
        'recipient_email': _recipient.text.trim(),
        'alert_email': _senderEmail,
        'date_column': _dateColumn ?? '',
        'subject_template': _subject.text,
        'body_template': _body.text,
        'schedule_ui': _schedule,
        'cron': cronFromScheduleUi(_schedule),
      };

  bool get _step1Valid =>
      _fileUrl.text.trim().isNotEmpty &&
      _recipient.text.trim().isNotEmpty &&
      _name.text.trim().isNotEmpty;

  /// {{ }} 토큰 형식 및 데이터명 유효성 검사.
  String? _tokenError(String label, String text) {
    if (!text.contains('{')) return null;
    final re = RegExp(r'\{\{\s*([^{}]*?)\s*\}\}');
    final matches = re.allMatches(text).toList();
    final stripped = text.replaceAll(re, '');
    if (stripped.contains('{') || stripped.contains('}')) {
      return '$label의 {{ }} 형식이 올바르지 않습니다';
    }
    const specials = {'오늘', 'today', '날짜'};
    for (final m in matches) {
      final name = m.group(1)!.trim();
      if (name.isEmpty) return '$label에 빈 데이터 태그({{}})가 있습니다';
      if (_columns.isNotEmpty && !specials.contains(name) && !_columns.contains(name)) {
        return '$label에 사용할 수 없는 데이터명이 있습니다: "$name"';
      }
    }
    return null;
  }

  String? _validate() {
    if (!_step1Valid) return '이름·참조 파일 URL·수신자 이메일을 모두 입력하세요';
    return _tokenError('메일 제목', _subject.text) ?? _tokenError('메일 작성 내용', _body.text);
  }

  Future<void> _goStep2() async {
    if (!_step1Valid) {
      setState(() => _stepError = '이름·참조 파일 URL·수신자 이메일을 모두 입력하세요');
      return;
    }
    setState(() => _stepError = null);
    await _loadColumns();
    setState(() => _step = 1);
  }

  void _submit() {
    final err = _validate();
    if (err != null) {
      setState(() => _dataError = err);
      return;
    }
    setState(() => _dataError = null);
    widget.onSubmit(_name.text.trim(), _buildConfig());
  }

  void _insertToken(TextEditingController c, String col) {
    final token = '{{$col}}';
    final text = c.text;
    var start = c.selection.start;
    var end = c.selection.end;
    if (start < 0 || end < 0) {
      start = end = text.length;
    }
    final newText = text.replaceRange(start, end, token);
    c.value = TextEditingValue(
      text: newText,
      selection: TextSelection.collapsed(offset: start + token.length),
    );
    setState(() {});
  }

  void _insertToLastFocused(String col) {
    _insertToken(_lastFocused == 'subject' ? _subject : _body, col);
  }

  @override
  Widget build(BuildContext context) {
    if (widget.wizard) {
      return _step == 0 ? _stepOne() : _stepTwo();
    }
    return SingleChildScrollView(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          _note(),
          _basicFields(),
          const Divider(height: 28),
          _dataSection(),
          if (_dataError != null) ...[
            const SizedBox(height: 10),
            Text(_dataError!, style: const TextStyle(color: AppColors.danger, fontWeight: FontWeight.w600)),
          ],
          const SizedBox(height: 16),
          Row(children: [
            if (widget.onDelete != null)
              TextButton.icon(
                onPressed: widget.busy ? null : widget.onDelete,
                icon: const Icon(Icons.delete_outline),
                label: const Text('삭제'),
              ),
            const Spacer(),
            FilledButton(onPressed: widget.busy ? null : _submit, child: Text(widget.submitLabel)),
          ]),
        ],
      ),
    );
  }

  Widget _note() => Container(
        margin: const EdgeInsets.only(bottom: 12),
        padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
        decoration: BoxDecoration(
          color: const Color(0xFFE8F4FD),
          borderRadius: BorderRadius.circular(kRadius),
        ),
        child: const Row(children: [
          Icon(Icons.info_outline_rounded, size: 18, color: Color(0xFF0563A5)),
          SizedBox(width: 8),
          Expanded(
            child: Text('설정은 생성 후에도 언제든 변경할 수 있어요. (추후 변경 가능)',
                style: TextStyle(fontSize: 13, fontWeight: FontWeight.w600, color: Color(0xFF0563A5))),
          ),
        ]),
      );

  Widget _stepOne() {
    return SingleChildScrollView(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          const _StepBadge(step: 1, title: '기본 정보'),
          const SizedBox(height: 12),
          _note(),
          _basicFields(),
          if (_stepError != null) ...[
            const SizedBox(height: 8),
            Text(_stepError!, style: const TextStyle(color: AppColors.danger, fontWeight: FontWeight.w600)),
          ],
          const SizedBox(height: 20),
          FilledButton(
            onPressed: widget.busy || _loadingCols ? null : _goStep2,
            child: _loadingCols
                ? const SizedBox(height: 18, width: 18, child: CircularProgressIndicator(strokeWidth: 2))
                : const Text('다음'),
          ),
        ],
      ),
    );
  }

  Widget _basicFields() => Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          _tf(_name, '이름', hint: '예: 세금계산서 발행 알림'),
          _tf(_fileUrl, '참조 파일 URL (엑셀 표 형식)', hint: 'SharePoint 공유 xlsx 링크'),
          _tf(_recipient, '수신자 이메일'),
          Padding(
            padding: const EdgeInsets.symmetric(vertical: 8),
            child: Row(children: [
              const Icon(Icons.send_rounded, size: 16, color: AppColors.muted),
              const SizedBox(width: 6),
              Text('발신 계정: ${_senderEmail.isEmpty ? '본인 계정' : _senderEmail} (본인 계정으로 발송)',
                  style: const TextStyle(fontSize: 13, color: AppColors.muted, fontWeight: FontWeight.w500)),
            ]),
          ),
        ],
      );

  Widget _stepTwo() {
    return SingleChildScrollView(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          const _StepBadge(step: 2, title: '데이터 · 주기 · 본문'),
          const SizedBox(height: 12),
          _dataSection(),
          if (_dataError != null) ...[
            const SizedBox(height: 10),
            Text(_dataError!, style: const TextStyle(color: AppColors.danger, fontWeight: FontWeight.w600)),
          ],
          const SizedBox(height: 20),
          Row(children: [
            TextButton(onPressed: widget.busy ? null : () => setState(() => _step = 0), child: const Text('이전')),
            const Spacer(),
            FilledButton(
              onPressed: widget.busy ? null : _submit,
              child: widget.busy ? const Text('처리 중…') : Text(widget.submitLabel),
            ),
          ]),
        ],
      ),
    );
  }

  Widget _dataSection() {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        Row(
          children: [
            const Text('사용 가능한 데이터', style: TextStyle(fontWeight: FontWeight.w700, fontSize: 15)),
            const SizedBox(width: 8),
            IconButton(
              tooltip: '컬럼 다시 불러오기',
              icon: const Icon(Icons.refresh_rounded, size: 18),
              onPressed: _loadingCols ? null : _loadColumns,
            ),
          ],
        ),
        const Text('아래 항목을 드래그(또는 탭)해서 발송기준일·제목·본문에 넣으세요',
            style: TextStyle(fontSize: 13, color: AppColors.muted, fontWeight: FontWeight.w500)),
        const SizedBox(height: 8),
        if (_loadingCols)
          const Padding(padding: EdgeInsets.all(8), child: LinearProgressIndicator())
        else if (_colsError != null)
          Text(_colsError!, style: const TextStyle(color: AppColors.danger, fontWeight: FontWeight.w600))
        else if (_columns.isEmpty)
          const Text('컬럼이 없습니다. 참조 파일 URL을 확인하세요.',
              style: TextStyle(color: AppColors.muted, fontWeight: FontWeight.w500))
        else
          Wrap(spacing: 6, runSpacing: 6, children: [for (final c in _columns) _columnChip(c)]),
        const Divider(height: 28),

        const Text('발송기준일(발송 규칙 데이터)', style: TextStyle(fontWeight: FontWeight.w700, fontSize: 15)),
        const SizedBox(height: 6),
        _dateDropTarget(),
        const SizedBox(height: 4),
        const Text('입력하지 않으면 규칙 확인 주기마다 발송',
            style: TextStyle(fontSize: 13, color: AppColors.muted, fontWeight: FontWeight.w500)),
        const SizedBox(height: 20),

        const Text('규칙 확인 주기', style: TextStyle(fontWeight: FontWeight.w700, fontSize: 15)),
        const SizedBox(height: 6),
        _scheduleBuilder(),
        const SizedBox(height: 20),

        const Text('메일 제목(드래그로 데이터 삽입 가능)', style: TextStyle(fontWeight: FontWeight.w700, fontSize: 15)),
        const SizedBox(height: 6),
        _dropField(_subject, _subjectFocus, hint: '예: [{{거래처}}] 발행 요청', maxLines: 1),
        const SizedBox(height: 16),

        const Text('메일 작성 내용', style: TextStyle(fontWeight: FontWeight.w700, fontSize: 15)),
        const SizedBox(height: 6),
        _dropField(_body, _bodyFocus,
            hint: '본문을 작성하고, 원하는 위치에 데이터를 드래그해 넣으세요.\n예: 안녕하세요, {{거래처}} 담당자님',
            maxLines: 8),
      ],
    );
  }

  Widget _columnChip(String col) {
    final chip = Chip(
      label: Text(col),
      backgroundColor: const Color(0xFFE8F4FD),
      visualDensity: VisualDensity.compact,
    );
    return Draggable<String>(
      data: col,
      feedback: Material(color: Colors.transparent, child: Chip(label: Text(col))),
      childWhenDragging: Opacity(opacity: 0.4, child: chip),
      child: InkWell(onTap: () => _insertToLastFocused(col), child: chip),
    );
  }

  Widget _dateDropTarget() {
    return DragTarget<String>(
      onAcceptWithDetails: (d) => setState(() => _dateColumn = d.data),
      builder: (context, candidate, rejected) {
        final active = candidate.isNotEmpty;
        return Container(
          padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 12),
          decoration: BoxDecoration(
            border: Border.all(color: active ? AppColors.primary : AppColors.line),
            borderRadius: BorderRadius.circular(kRadius),
            color: active ? const Color(0xFFE8F4FD) : null,
          ),
          child: _dateColumn == null
              ? const Text('드래그해서 입력', style: TextStyle(color: AppColors.muted, fontWeight: FontWeight.w500))
              : Row(children: [
                  Chip(
                    label: Text(_dateColumn!),
                    backgroundColor: const Color(0xFFE8F4FD),
                    onDeleted: () => setState(() => _dateColumn = null),
                  ),
                ]),
        );
      },
    );
  }

  Widget _dropField(TextEditingController c, FocusNode focus, {required String hint, required int maxLines}) {
    return DragTarget<String>(
      onAcceptWithDetails: (d) => _insertToken(c, d.data),
      builder: (context, candidate, rejected) {
        return TextField(
          controller: c,
          focusNode: focus,
          maxLines: maxLines,
          decoration: InputDecoration(
            hintText: hint,
            filled: candidate.isNotEmpty,
            fillColor: const Color(0xFFE8F4FD),
          ),
        );
      },
    );
  }

  Widget _scheduleBuilder() {
    final kind = _schedule['kind'] ?? 'daily';
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Wrap(
          spacing: 8,
          runSpacing: 8,
          crossAxisAlignment: WrapCrossAlignment.center,
          children: [
            DropdownButton<String>(
              value: kind,
              items: const [
                DropdownMenuItem(value: 'daily', child: Text('매일')),
                DropdownMenuItem(value: 'weekly', child: Text('매주')),
                DropdownMenuItem(value: 'monthly', child: Text('매월')),
                DropdownMenuItem(value: 'hourly', child: Text('매시간')),
                DropdownMenuItem(value: 'minutely', child: Text('분마다')),
              ],
              onChanged: (v) => setState(() => _schedule = {..._schedule, 'kind': v}),
            ),
            if (kind == 'weekly')
              _dropdown<int>((_schedule['weekday'] ?? 1) as int, [for (int i = 1; i <= 7; i++) i],
                  (i) => '${kWeekdayNames[i - 1]}요일', (v) => setState(() => _schedule = {..._schedule, 'weekday': v})),
            if (kind == 'monthly')
              _dropdown<int>((_schedule['day'] ?? 1) as int, [for (int i = 1; i <= 31; i++) i],
                  (i) => '$i일', (v) => setState(() => _schedule = {..._schedule, 'day': v})),
            if (kind == 'daily' || kind == 'weekly' || kind == 'monthly') ...[
              _dropdown<int>((_schedule['hour'] ?? 9) as int, [for (int i = 0; i < 24; i++) i],
                  (i) => '${i.toString().padLeft(2, '0')}시', (v) => setState(() => _schedule = {..._schedule, 'hour': v})),
              _dropdown<int>((_schedule['minute'] ?? 0) as int, [for (int i = 0; i < 60; i++) i],
                  (i) => '${i.toString().padLeft(2, '0')}분', (v) => setState(() => _schedule = {..._schedule, 'minute': v})),
            ],
            if (kind == 'hourly')
              _dropdown<int>((_schedule['minute'] ?? 0) as int, [for (int i = 0; i < 60; i++) i],
                  (i) => '매시 ${i.toString().padLeft(2, '0')}분', (v) => setState(() => _schedule = {..._schedule, 'minute': v})),
            if (kind == 'minutely')
              _dropdown<int>((_schedule['interval'] ?? 30) as int, const [5, 10, 15, 20, 30, 60],
                  (i) => '$i분마다', (v) => setState(() => _schedule = {..._schedule, 'interval': v})),
          ],
        ),
        const SizedBox(height: 6),
        Text('→ ${humanFromScheduleUi(_schedule)}',
            style: const TextStyle(fontSize: 13, color: AppColors.primary, fontWeight: FontWeight.w600)),
      ],
    );
  }

  Widget _dropdown<T>(T value, List<T> items, String Function(T) label, void Function(T) onCh) {
    return DropdownButton<T>(
      value: value,
      items: [for (final i in items) DropdownMenuItem(value: i, child: Text(label(i)))],
      onChanged: (v) {
        if (v != null) onCh(v);
      },
    );
  }

  Widget _tf(TextEditingController c, String label, {String? hint}) => Padding(
        padding: const EdgeInsets.symmetric(vertical: 8),
        child: TextField(
          controller: c,
          onChanged: (_) => setState(() {}),
          decoration: InputDecoration(labelText: label, hintText: hint),
        ),
      );
}

class _StepBadge extends StatelessWidget {
  final int step;
  final String title;
  const _StepBadge({required this.step, required this.title});
  @override
  Widget build(BuildContext context) {
    return Row(
      children: [
        CircleAvatar(radius: 14, backgroundColor: AppColors.primary, child: Text('$step', style: const TextStyle(color: Colors.white, fontWeight: FontWeight.w700))),
        const SizedBox(width: 8),
        Text(title, style: const TextStyle(fontSize: 16, fontWeight: FontWeight.w700)),
        const SizedBox(width: 8),
        Text('($step/2)', style: const TextStyle(color: AppColors.muted, fontWeight: FontWeight.w600)),
      ],
    );
  }
}
