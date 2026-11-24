import 'dart:convert';
import 'dart:typed_data';

import 'package:http/http.dart' as http;
import 'package:shared_preferences/shared_preferences.dart';

/// Server address. Default is the server on the same computer. For a phone on
/// the network: flutter run --dart-define=API_BASE=http://192.168.1.10:8000/api
/// A path like /api means "the same address the app was opened from" (the
/// browser version served by the server itself, e.g. the client's test link).
const _apiBaseSetting = String.fromEnvironment(
  'API_BASE',
  defaultValue: 'http://localhost:8000/api',
);
String apiBase = _apiBaseSetting.startsWith('/')
    ? Uri.base.resolve(_apiBaseSetting).toString()
    : _apiBaseSetting;

/// API_BASE=remote (the test app file): the server's address is read when the
/// app opens from a small file on GitHub, so the same installed app keeps
/// working when the temporary test link changes. The last one is remembered.
const serverAddressFile =
    'https://raw.githubusercontent.com/johnsamire-coder/bareeq/main/deploy/server-url.txt';

Future<void> resolveApiBase() async {
  if (_apiBaseSetting != 'remote') return;
  final prefs = await SharedPreferences.getInstance();
  try {
    final r = await http
        .get(Uri.parse(serverAddressFile))
        .timeout(const Duration(seconds: 8));
    final url = r.body.trim();
    if (r.statusCode == 200 && url.startsWith('https://')) {
      apiBase = '$url/api';
      await prefs.setString('api_base', apiBase);
      return;
    }
  } catch (_) {}
  apiBase = prefs.getString('api_base') ?? apiBase;
}

/// An error the server explained: `code` (stable name) and `message` (Arabic).
class ApiError implements Exception {
  ApiError(
    this.code,
    this.message, {
    this.status = 400,
    this.fields = const {},
  });
  final String code;
  final String message;
  final int status;
  final Map<String, dynamic> fields;

  @override
  String toString() => message;
}

class Api {
  Api({http.Client? client}) : _client = client ?? http.Client();
  final http.Client _client;
  String? token;

  Map<String, String> get _headers => {
    'Content-Type': 'application/json',
    'Accept': 'application/json',
    if (token != null) 'Authorization': 'Token $token',
  };

  Uri _uri(String path, [Map<String, dynamic>? query]) {
    final q = query?.map((k, v) => MapEntry(k, '$v'));
    return Uri.parse(
      '$apiBase/$path',
    ).replace(queryParameters: (q == null || q.isEmpty) ? null : q);
  }

  Future<dynamic> get(String path, [Map<String, dynamic>? query]) =>
      _send(() => _client.get(_uri(path, query), headers: _headers));

  Future<dynamic> post(String path, [Object? body]) => _send(
    () => _client.post(
      _uri(path),
      headers: _headers,
      body: jsonEncode(body ?? {}),
    ),
  );

  Future<dynamic> patch(String path, Object body) => _send(
    () => _client.patch(_uri(path), headers: _headers, body: jsonEncode(body)),
  );

  Future<dynamic> delete(String path) =>
      _send(() => _client.delete(_uri(path), headers: _headers));

  /// Upload one image with form fields (InstaPay screenshot, rating photos...).
  Future<dynamic> upload(
    String path,
    Map<String, String> fields,
    String fileField,
    Uint8List bytes,
    String filename,
  ) {
    return _send(() async {
      final req = http.MultipartRequest('POST', _uri(path))
        ..fields.addAll(fields)
        ..files.add(
          http.MultipartFile.fromBytes(fileField, bytes, filename: filename),
        );
      if (token != null) req.headers['Authorization'] = 'Token $token';
      return http.Response.fromStream(await _client.send(req));
    });
  }

  /// A protected file (e.g. before/after photo) as bytes.
  Future<Uint8List> bytes(String serverPath) async {
    final base = Uri.parse(apiBase);
    final uri = base.replace(path: serverPath);
    final r = await _client.get(
      uri,
      headers: {if (token != null) 'Authorization': 'Token $token'},
    );
    if (r.statusCode != 200) {
      throw ApiError('file', 'مقدرناش نفتح الصورة.', status: r.statusCode);
    }
    return r.bodyBytes;
  }

  Future<dynamic> _send(Future<http.Response> Function() call) async {
    http.Response r;
    try {
      r = await call();
    } catch (_) {
      throw ApiError(
        'network',
        'مفيش اتصال بالإنترنت أو السيرفر مش شغال. جرب تاني.',
        status: 0,
      );
    }
    final text = utf8.decode(r.bodyBytes);
    final body = text.isEmpty ? null : jsonDecode(text);
    if (r.statusCode >= 200 && r.statusCode < 300) return body;
    if (body is Map && body['code'] != null) {
      throw ApiError(
        '${body['code']}',
        '${body['detail'] ?? 'حصلت مشكلة.'}',
        status: r.statusCode,
      );
    }
    if (r.statusCode == 401) {
      throw ApiError('unauthorized', 'سجل دخول تاني.', status: 401);
    }
    if (body is Map) {
      // Field errors: show the first message.
      final first = body.values.isNotEmpty ? body.values.first : null;
      final msg = first is List && first.isNotEmpty
          ? '${first.first}'
          : '$first';
      throw ApiError(
        'invalid',
        msg,
        status: r.statusCode,
        fields: Map<String, dynamic>.from(body),
      );
    }
    throw ApiError(
      'server',
      'حصلت مشكلة في السيرفر. جرب تاني.',
      status: r.statusCode,
    );
  }
}
