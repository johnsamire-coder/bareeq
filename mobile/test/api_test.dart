import 'dart:convert';

import 'package:bareeq/core/api.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';

http.Response json(Object body, int status) =>
    http.Response.bytes(utf8.encode(jsonEncode(body)), status, headers: {'content-type': 'application/json'});

void main() {
  test('sends the login token and reads JSON', () async {
    late http.Request seen;
    final api = Api(client: MockClient((r) async {
      seen = r;
      return json({'ok': true}, 200);
    }))
      ..token = 'abc';
    final r = await api.get('me/');
    expect(r['ok'], true);
    expect(seen.headers['Authorization'], 'Token abc');
    expect(seen.url.toString(), '$apiBase/me/');
  });

  test('business errors keep the code and the Arabic message', () async {
    final api = Api(client: MockClient((_) async => json({'code': 'slot_taken', 'detail': 'الميعاد ده اتحجز.'}, 409)));
    try {
      await api.post('orders/', {});
      fail('should throw');
    } on ApiError catch (e) {
      expect(e.code, 'slot_taken');
      expect(e.message, 'الميعاد ده اتحجز.');
      expect(e.status, 409);
    }
  });

  test('field errors show the first message', () async {
    final api = Api(client: MockClient((_) async => json({'phone': ['رقم الموبايل مش صحيح.']}, 400)));
    expect(() => api.post('auth/otp/request/', {}), throwsA(isA<ApiError>().having((e) => e.message, 'message', 'رقم الموبايل مش صحيح.')));
  });

  test('no connection gives a clear message', () async {
    final api = Api(client: MockClient((_) async => throw Exception('down')));
    expect(() => api.get('me/'), throwsA(isA<ApiError>().having((e) => e.code, 'code', 'network')));
  });
}
