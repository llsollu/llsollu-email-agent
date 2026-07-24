import 'package:flutter/material.dart';

import '../theme.dart';

/// 메일 분류·요약 에이전트 전용 설정 폼(생성/편집 공용, 단일 화면).
class ClassifierForm extends StatefulWidget {
  final String initialName;
  final Map<String, dynamic> initialConfig;
  final bool busy;
  final String submitLabel;
  final void Function(String name, Map<String, dynamic> config) onSubmit;
  final VoidCallback? onDelete;

  const ClassifierForm({
    super.key,
    required this.initialName,
    required this.initialConfig,
    required this.onSubmit,
    this.busy = false,
    this.submitLabel = '생성',
    this.onDelete,
  });

  @override
  State<ClassifierForm> createState() => _ClassifierFormState();
}

class _ClassifierFormState extends State<ClassifierForm> {
  final _name = TextEditingController();
  final _mailbox = TextEditingController();
  final _categories = TextEditingController();
  String _cardTitle = 'client';
  String? _error;

  static const _cardTitleOptions = {'client': '고객사', 'category': '분류', 'title': '요약 제목'};

  @override
  void initState() {
    super.initState();
    final c = widget.initialConfig;
    _name.text = widget.initialName;
    _mailbox.text = (c['mailbox'] ?? '').toString();
    _categories.text = (c['categories'] ?? '').toString();
    final ct = (c['card_title_field'] ?? 'client').toString();
    if (_cardTitleOptions.containsKey(ct)) _cardTitle = ct;
  }

  @override
  void dispose() {
    for (final c in [_name, _mailbox, _categories]) {
      c.dispose();
    }
    super.dispose();
  }

  void _submit() {
    if (_name.text.trim().isEmpty || _mailbox.text.trim().isEmpty) {
      setState(() => _error = '이름·대상 메일함을 입력하세요');
      return;
    }
    setState(() => _error = null);
    widget.onSubmit(_name.text.trim(), {
      'mailbox': _mailbox.text.trim(),
      'categories': _categories.text.trim(),
      'card_title_field': _cardTitle,
    });
  }

  @override
  Widget build(BuildContext context) {
    return SingleChildScrollView(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          _note(),
          _tf(_name, '이름'),
          _tf(_mailbox, '대상 메일함', hint: '분류할 메일을 수신하는 회사 메일 주소'),
          _tf(_categories, '메일 분류 카테고리',
              hint: '쉼표로 구분. 예: 제안,계약,개발,납품,유지보수,문의'),
          const SizedBox(height: 8),
          const Text('요약 카드 타이틀', style: TextStyle(fontWeight: FontWeight.w700, fontSize: 15)),
          const SizedBox(height: 2),
          const Text('칸반 카드에 크게 표시할 항목을 고르세요',
              style: TextStyle(fontSize: 13, color: AppColors.muted, fontWeight: FontWeight.w500)),
          const SizedBox(height: 8),
          SegmentedButton<String>(
            segments: [
              for (final e in _cardTitleOptions.entries)
                ButtonSegment(value: e.key, label: Text(e.value)),
            ],
            selected: {_cardTitle},
            onSelectionChanged: (s) => setState(() => _cardTitle = s.first),
          ),
          if (_error != null) ...[
            const SizedBox(height: 12),
            Text(_error!, style: const TextStyle(color: AppColors.danger, fontWeight: FontWeight.w600)),
          ],
          const SizedBox(height: 20),
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
        decoration: BoxDecoration(color: const Color(0xFFE8F4FD), borderRadius: BorderRadius.circular(kRadius)),
        child: const Row(children: [
          Icon(Icons.info_outline_rounded, size: 18, color: Color(0xFF0563A5)),
          SizedBox(width: 8),
          Expanded(
            child: Text('설정은 생성 후에도 언제든 변경할 수 있어요. (추후 변경 가능)',
                style: TextStyle(fontSize: 13, fontWeight: FontWeight.w600, color: Color(0xFF0563A5))),
          ),
        ]),
      );

  Widget _tf(TextEditingController c, String label, {String? hint}) => Padding(
        padding: const EdgeInsets.symmetric(vertical: 8),
        child: TextField(
          controller: c,
          decoration: InputDecoration(labelText: label, hintText: hint),
        ),
      );
}
