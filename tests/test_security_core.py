import unittest
from unittest.mock import patch
from backend.security_core import (SecurityError, DemoTokens, Principal, validate_profile,
                                   validate_messages, validate_course, validate_lesson,
                                   extract_bearer, safe_identifier, redact, require_json_object)

class TestSecurityCore(unittest.TestCase):
    def setUp(self): self.tokens=DemoTokens('a'*40)
    def fails(self,call,status=400):
        with self.assertRaises(SecurityError) as result: call()
        self.assertEqual(result.exception.status,status)

    def test_sign_and_verify(self):
        self.assertEqual(self.tokens.verify(self.tokens.issue('alice','instructor')).uid,'alice')
    def test_reject_unsigned(self): self.fails(lambda:self.tokens.verify('alice.instructor'),401)
    def test_reject_tampering(self):
        token=self.tokens.issue('alice','instructor')
        self.fails(lambda:self.tokens.verify(token+'x'),401)
    def test_wrong_key(self):
        token=self.tokens.issue('alice','instructor')
        self.fails(lambda:DemoTokens('b'*40).verify(token),401)
    def test_expired(self): self.fails(lambda:self.tokens.verify(self.tokens.issue('alice','instructor',-1)),401)
    def test_unknown_role(self):
        with self.assertRaises(ValueError): self.tokens.issue('alice','root')
    def test_short_signing_key_rejected(self):
        with self.assertRaises(ValueError): DemoTokens('short')
    def test_bad_base64(self): self.fails(lambda:self.tokens.verify('!!!.!!'),401)
    def test_wrong_header(self): self.fails(lambda:extract_bearer('Basic secret'),401)
    def test_header_extra_whitespace(self): self.fails(lambda:extract_bearer('Bearer a b'),401)
    def test_header_success(self): self.assertEqual(extract_bearer('Bearer abc'),'abc')
    def test_profile_bounded(self):
        value=validate_profile({'majors':['CS'],'about':'fine'})
        self.assertEqual(value['majors'],['CS'])
    def test_profile_mass_assignment_filtered(self):
        self.assertNotIn('role',validate_profile({'role':'admin'}))
    def test_profile_wrong_lists(self): self.fails(lambda:validate_profile({'majors':'CS'}))
    def test_profile_excess(self): self.fails(lambda:validate_profile({'about':'x'*1201}))
    def test_messages(self):
        value=validate_messages({'messages':[{'sender':'human','content':'Hello','messageID':'abc','timestamp':'2026'}]})
        self.assertEqual(value[0]['content'],'Hello')
    def test_messages_reject_numeric_identifier(self):
        self.fails(lambda:validate_messages({'messages':[{
            'sender':'user', 'content':'hi', 'messageID':123, 'timestamp':'2026',
        }]}))
    def test_messages_reject_object_timestamp(self):
        self.fails(lambda:validate_messages({'messages':[{
            'sender':'user', 'content':'hi', 'messageID':'abc', 'timestamp':{'bad':True},
        }]}))
    def test_messages_reject_list_timestamp(self):
        self.fails(lambda:validate_messages({'messages':[{
            'sender':'user', 'content':'hi', 'messageID':'abc', 'timestamp':[],
        }]}))
    def test_messages_untrusted_object(self): self.fails(lambda:validate_messages({'messages':[[1]]}))
    def test_messages_overflow(self): self.fails(lambda:validate_messages({'messages':[{}]*101}))
    def test_course_missing(self): self.fails(lambda:validate_course({}))
    def test_course_injection_remains_literal(self):
        self.assertEqual(validate_course({'title':'SQL -- never','description':'unsafe text'})['title'],'SQL -- never')
    def test_lesson_oversized(self): self.fails(lambda:validate_lesson({'title':'Fine','content':'A'*6000}))
    def test_identifier_forbids_paths(self): self.fails(lambda:safe_identifier('../../admin'))
    def test_data_object(self): self.fails(lambda:require_json_object([1,2]))
    def test_redact_bearer(self): self.assertNotIn('secrettoken',redact('Bearer secrettoken'))
    def test_redact_password(self): self.assertNotIn('hunter2',redact('password=hunter2'))
