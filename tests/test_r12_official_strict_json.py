"""R12: security-regression tests for the original Flask JSON boundary."""
from __future__ import annotations
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'backend'))
from strict_request_json import parse_object, MAX_JSON_BYTES, MAX_JSON_DEPTH, MAX_JSON_NODES
from security_core import SecurityError


class StrictJSONTests(unittest.TestCase):
    def parse(self, raw, mimetype='application/json'):
        return parse_object(raw, mimetype)

    def test_accepts_nested_profile(self):
        self.assertEqual(self.parse(b'{"about":"ok","courses":["CS"],"active":true}'),
                         {'about':'ok','courses':['CS'],'active':True})

    def test_accepts_escaped_international_text(self):
        self.assertEqual(self.parse('{"about":"Recife – Olá"}'.encode()), {'about':'Recife – Olá'})

    def test_rejects_top_level_nonobject(self):
        for raw in (b'null',b'[]',b'123',b'"hi"',b'true'):
            with self.subTest(raw=raw), self.assertRaises(SecurityError):
                self.parse(raw)

    def test_rejects_missing_mime_type(self):
        for mime in (None,'','text/plain','text/html','application/x-www-form-urlencoded',
                     'application/jsonp','application/json; charset=utf-8'):
            with self.subTest(mimetype=mime), self.assertRaises(SecurityError) as cm:
                self.parse(b'{}',mime)
            self.assertEqual(cm.exception.status,415)

    def test_rejects_duplicate_top_level_key(self):
        with self.assertRaisesRegex(SecurityError,'Duplicate JSON key'):
            self.parse(b'{"about":"safe","about":"evil"}')

    def test_rejects_nested_duplicate_key(self):
        with self.assertRaisesRegex(SecurityError,'Duplicate JSON key'):
            self.parse(b'{"meta":{"flag":false,"flag":true}}')

    def test_rejects_duplicate_after_unicode_decoding(self):
        with self.assertRaisesRegex(SecurityError,'Duplicate JSON key'):
            self.parse(b'{"uid":1,"u\\u0069d":2}')

    def test_rejects_nan_infinity_and_negative_infinity(self):
        for value in ('NaN','Infinity','-Infinity'):
            with self.subTest(value=value), self.assertRaisesRegex(SecurityError,'Non-finite'):
                self.parse(('{"about":'+value+'}').encode())

    def test_rejects_float_overflow(self):
        for value in ('1e9999','-1e9999'):
            with self.subTest(value=value), self.assertRaisesRegex(SecurityError,'Non-finite'):
                self.parse(('{"limit":'+value+'}').encode())

    def test_rejects_surrogate_in_nested_value(self):
        with self.assertRaisesRegex(SecurityError,'Invalid Unicode'):
            self.parse(b'{"profile":{"about":"\\ud800"}}')

    def test_rejects_surrogate_in_key(self):
        with self.assertRaisesRegex(SecurityError,'Invalid Unicode'):
            self.parse(b'{"\\udfff":"value"}')

    def test_allows_valid_surrogate_pair(self):
        self.assertEqual(self.parse(b'{"name":"\\ud83d\\ude03"}'),{'name':'😃'})

    def test_rejects_trailing_and_comments(self):
        for raw in (b'{}{}',b'{"a":1} trailing',b'{"a":1}//comment'):
            with self.subTest(raw=raw),self.assertRaises(SecurityError):self.parse(raw)

    def test_rejects_invalid_utf8_and_bom(self):
        for raw in (b'{"a":"\xff"}',b'\xef\xbb\xbf{}'):
            with self.subTest(raw=raw),self.assertRaises(SecurityError):self.parse(raw)

    def test_rejects_truncated_and_empty(self):
        for raw in (b'',b'{',b'{"a":',b'{"a":1'):
            with self.subTest(raw=raw),self.assertRaises(SecurityError):self.parse(raw)

    def test_rejects_too_large_json(self):
        with self.assertRaises(SecurityError) as cm:
            self.parse(b'{"body":"'+b'a'*MAX_JSON_BYTES+b'"}')
        self.assertEqual(cm.exception.status,413)

    def test_accepts_at_boundary(self):
        body=b'{"a":"'+b'a'*(MAX_JSON_BYTES-8)+b'"}'
        self.assertLessEqual(len(body),MAX_JSON_BYTES)
        self.assertEqual(len(self.parse(body)['a']),MAX_JSON_BYTES-8)

    def test_rejects_excessive_depth(self):
        raw=b'{"x":'+b'['*(MAX_JSON_DEPTH+1)+b'1'+b']'*(MAX_JSON_DEPTH+1)+b'}'
        with self.assertRaisesRegex(SecurityError,'structure exceeds'):
            self.parse(raw)

    def test_accepts_reasonably_nested(self):
        raw=b'{"x":'+b'['*12+b'1'+b']'*12+b'}'
        self.assertIsInstance(self.parse(raw),dict)

    def test_rejects_too_many_nodes(self):
        raw=b'{"x":['+b'0,'*4200+b'0]}'
        with self.assertRaisesRegex(SecurityError,'structure exceeds'):
            self.parse(raw)

    def test_no_raw_secret_in_error_message(self):
        secret='SYNTHETIC_SECRET_SHOULD_NOT_LEAK'
        raw=('{"a":"'+secret+'","a":2}').encode()
        try:self.parse(raw)
        except SecurityError as e:self.assertNotIn(secret,str(e))
        else:self.fail('Expected error')

    def test_original_routes_use_shared_parser(self):
        source=(ROOT/'backend/endpoints.py').read_text()
        self.assertEqual(source.count('request_json_object()'),5)
        self.assertNotIn('request.get_json(',source)
        self.assertIn('from strict_request_json import parse_object',source)


if __name__ == '__main__':unittest.main()
