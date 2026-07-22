/// API 베이스 URL. Web은 동일 오리진(''), Desktop/macOS는 서버 IP 지정.
/// 빌드 시 --dart-define=API_BASE=http://<SERVER_IP>:8000 로 주입 가능.
const String kApiBase = String.fromEnvironment('API_BASE', defaultValue: '');

/// 예: '' 이면 상대경로 '/api', 값이 있으면 '<base>/api'
String get apiRoot => '$kApiBase/api';
