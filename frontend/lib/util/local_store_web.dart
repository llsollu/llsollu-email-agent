// 웹 전용 저장소 헬퍼. 조건부 import 로 웹 빌드에서만 사용됨.
// ignore_for_file: avoid_web_libraries_in_flutter, deprecated_member_use
import 'dart:html' as html;

const _key = 'saved_email';

String? loadSavedEmail() {
  final v = html.window.localStorage[_key];
  return (v != null && v.isNotEmpty) ? v : null;
}

void saveEmail(String? email) {
  if (email == null || email.isEmpty) {
    html.window.localStorage.remove(_key);
  } else {
    html.window.localStorage[_key] = email;
  }
}
