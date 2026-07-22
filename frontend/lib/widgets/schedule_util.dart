/// '확인 주기' 친화적 UI ↔ cron 변환/표시 유틸.
///
/// scheduleUi 맵 구조:
///   { kind: daily|weekly|monthly|hourly|minutely,
///     hour, minute, weekday(1=월..7=일), day(1~31), interval(분) }
/// 백엔드에는 cron 문자열로 저장하고, UI/대시보드에는 한글로 표시한다.
library;

const kWeekdayNames = ['월', '화', '수', '목', '금', '토', '일']; // index 0=월 .. 6=일

String _two(int n) => n.toString().padLeft(2, '0');

/// scheduleUi -> cron (표준 5필드: 분 시 일 월 요일; 요일 0=일..6=토)
String cronFromScheduleUi(Map<String, dynamic> s) {
  final kind = s['kind'] ?? 'daily';
  final minute = (s['minute'] ?? 0) as int;
  final hour = (s['hour'] ?? 9) as int;
  switch (kind) {
    case 'weekly':
      final wd = (s['weekday'] ?? 1) as int; // 1=월..7=일
      final cron = wd == 7 ? 0 : wd; // cron: 0=일
      return '$minute $hour * * $cron';
    case 'monthly':
      final day = (s['day'] ?? 1) as int;
      return '$minute $hour $day * *';
    case 'hourly':
      return '$minute * * * *';
    case 'minutely':
      final iv = (s['interval'] ?? 30) as int;
      return '*/$iv * * * *';
    case 'daily':
    default:
      return '$minute $hour * * *';
  }
}

/// scheduleUi -> 한글 표시
String humanFromScheduleUi(Map<String, dynamic> s) {
  final kind = s['kind'] ?? 'daily';
  final minute = (s['minute'] ?? 0) as int;
  final hour = (s['hour'] ?? 9) as int;
  final hm = '${_two(hour)}:${_two(minute)}';
  switch (kind) {
    case 'weekly':
      final wd = (s['weekday'] ?? 1) as int;
      return '매주 ${kWeekdayNames[(wd - 1).clamp(0, 6)]}요일 $hm';
    case 'monthly':
      return '매월 ${s['day'] ?? 1}일 $hm';
    case 'hourly':
      return '매시 ${minute}분';
    case 'minutely':
      return '${s['interval'] ?? 30}분마다';
    case 'daily':
    default:
      return '매일 $hm';
  }
}

/// cron -> scheduleUi (편집 시 복원용). 인식 못 하면 null.
Map<String, dynamic>? scheduleUiFromCron(String? cron) {
  if (cron == null) return null;
  final p = cron.trim().split(RegExp(r'\s+'));
  if (p.length != 5) return null;
  final mn = p[0], hr = p[1], dom = p[2], dow = p[4];
  int? pi(String v) => int.tryParse(v);

  if (mn.startsWith('*/') && hr == '*' && dom == '*' && dow == '*') {
    return {'kind': 'minutely', 'interval': pi(mn.substring(2)) ?? 30};
  }
  if (pi(mn) != null && hr == '*' && dom == '*' && dow == '*') {
    return {'kind': 'hourly', 'minute': pi(mn)};
  }
  if (pi(mn) != null && pi(hr) != null && dom == '*' && dow != '*') {
    final c = pi(dow)!;
    return {'kind': 'weekly', 'minute': pi(mn), 'hour': pi(hr), 'weekday': c == 0 ? 7 : c};
  }
  if (pi(mn) != null && pi(hr) != null && dom != '*') {
    return {'kind': 'monthly', 'minute': pi(mn), 'hour': pi(hr), 'day': pi(dom)};
  }
  if (pi(mn) != null && pi(hr) != null) {
    return {'kind': 'daily', 'minute': pi(mn), 'hour': pi(hr)};
  }
  return null;
}

/// cron -> 한글 표시 (대시보드). 인식 못 하면 cron 원문.
String humanFromCron(String? cron) {
  final ui = scheduleUiFromCron(cron);
  if (ui != null) return humanFromScheduleUi(ui);
  return cron ?? '-';
}
