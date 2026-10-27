"""Security regression checks for the OFFICIAL React/Flask chat data contract.

No Firebase SDK or remote service needed; storage adapter executes against fake
RTDB refs. Emulator HTTP integration runs separately when dependencies exist.
"""
import json
import re
import unittest
from pathlib import Path
from unittest.mock import patch

from backend.security_core import SecurityError, validate_messages
from backend import firebase as fb

ROOT = Path(__file__).resolve().parents[1]


class FakeReference:
    def __init__(self, store, path):
        self.store, self.path = store, path
    def update(self, updates):
        self.store.setdefault(self.path, {}).update(updates)


class FakeDB:
    def __init__(self):
        self.store = {}
    def reference(self, path):
        return FakeReference(self.store, path)


class ChatStorageRegression(unittest.TestCase):
    def setUp(self):
        self.db = FakeDB()
        self.patcher = patch.object(fb, 'db', self.db)
        self.patcher.start()
        self.addCleanup(self.patcher.stop)
        self.messages = [{
            'sender': 'user', 'content': 'Synthetic course inquiry',
            'messageID': 'abcd1234', 'timestamp': '2026-10-22T12:00:00Z',
        }]

    def test_firebase_updates_by_message_id(self):
        fb.Firebase.save_chat('alice', 'chat_123', validate_messages({'messages': self.messages}))
        data = self.db.store['users/alice/chats/chat_123/messages']
        self.assertEqual(list(data), ['abcd1234'])

    def test_repeat_post_is_idempotent(self):
        for _ in range(4):
            fb.Firebase.save_chat('alice', 'chat_123', self.messages)
        self.assertEqual(len(self.db.store['users/alice/chats/chat_123/messages']), 1)

    def test_user_namespaces_are_isolated(self):
        fb.Firebase.save_chat('alice', 'chat_123', self.messages)
        fb.Firebase.save_chat('bob', 'chat_123', self.messages)
        self.assertEqual(len(self.db.store), 2)
        self.assertIn('users/alice/chats/chat_123/messages', self.db.store)
        self.assertIn('users/bob/chats/chat_123/messages', self.db.store)

    def test_message_rejected_if_content_object(self):
        payload={'messages':[{**self.messages[0], 'content':{'botResponse':'text'}}]}
        with self.assertRaises(SecurityError):
            validate_messages(payload)

    def test_message_rejected_if_promise_serializes_to_empty_object(self):
        payload={'messages':[{**self.messages[0], 'messageID':{}}]}
        with self.assertRaises(SecurityError):
            validate_messages(payload)

    def test_new_frontend_contract_matches_server_validation(self):
        definition=(ROOT/'frontend/src/interfaces.d.ts').read_text()
        self.assertRegex(definition, r'messageID:\s*string;')
        self.assertRegex(definition, r'content:\s*string;')
        chat=(ROOT/'frontend/src/components/ChatInterface/ChatInterface.tsx').read_text()
        self.assertNotIn('someUniqueChatId', chat)
        self.assertNotIn('beforeunload', chat)
        self.assertIn('await saveCourseSphereChat', chat)
        self.assertNotIn('messageID: h(', chat)

    def test_client_does_not_call_unsupported_message_mutation_routes(self):
        client=(ROOT/'frontend/src/api.ts').read_text()
        self.assertNotIn('async function updateCourseSphereChat(',client)
        self.assertNotIn('async function deleteCourseSphereChat(',client)

    def test_save_batch_empty_is_noop(self):
        fb.Firebase.save_chat('alice', 'chat_123', [])
        self.assertFalse(self.db.store)


class OfficialBackendHardening(unittest.TestCase):
    def test_logs_json_without_query_string(self):
        code=(ROOT/'backend/endpoints.py').read_text()
        self.assertIn('app.logger.info(json.dumps(', code)
        self.assertIn('request.url_rule.rule', code)
        self.assertNotIn('request.full_path', code)
        self.assertNotIn('request.query_string', code)

    def test_frontend_login_error_does_not_echo_provider_details(self):
        code=(ROOT/'frontend/src/api.ts').read_text()
        self.assertNotIn('Login failed: ${e.message}', code)


if __name__ == '__main__':
    unittest.main()
