"""Runs original handler *function bodies* in an isolated stubbed namespace.

No Flask dependency, Firebase calls, networking, production accounts or external
credentials are involved. This is NOT an end-to-end pentest of the live app.
"""
from __future__ import annotations
import ast
from pathlib import Path
from types import SimpleNamespace
from backend.shared_quota import QuotaExceeded, QuotaUnavailable
from backend.security_core import (SecurityError, extract_bearer, validate_profile,
                                   validate_messages, safe_identifier, bounded_text)

ROOT = Path(__file__).resolve().parents[1]
ORIGINAL = ROOT / "audit/baseline/endpoints_original.txt"
PATCHED = ROOT / "backend/endpoints.py"


class FakeFirebase:
    call_log = []
    token_error = None
    profile_error = None

    @classmethod
    def reset(cls):
        cls.call_log = []
        cls.token_error = None
        cls.profile_error = None

    @classmethod
    def create_user(cls, email, password):
        cls.call_log.append(("create_user", email))
        return {"user_id": "synthetic", "email": email}

    @classmethod
    def verify_id_token(cls, token):
        cls.call_log.append(("verify_id_token", bool(token)))
        if cls.token_error:
            raise RuntimeError(cls.token_error)
        if token != "SYNTHETIC_TOKEN":
            raise RuntimeError("SYNTHETIC_INTERNAL_TRACE_MARKER")
        return {"uid": "alice"}

    @classmethod
    def get_user_info(cls, uid):
        cls.call_log.append(("get_user_info", uid))
        if cls.profile_error:
            raise RuntimeError(cls.profile_error)
        return {"courses": ["SYNTHETIC_COURSE"]}

    @classmethod
    def set_user_info(cls, uid, profile):
        cls.call_log.append(("set_user_info", uid, profile))
        return None

    @classmethod
    def try_get_user_info(cls, token):
        cls.call_log.append(("try_get_user_info", bool(token)))
        return None

    @classmethod
    def enforce_quota(cls, uid, action):
        cls.call_log.append(("enforce_quota", uid, action))

    @classmethod
    def save_chat(cls, uid, chat_id, messages):
        cls.call_log.append(("save_chat", uid, chat_id, len(messages)))

    @classmethod
    def delete_chat(cls, uid, chat_id):
        cls.call_log.append(("delete_chat", uid, chat_id))


class FakeRequest:
    def __init__(self, payload=None, headers=None, query=None):
        self.payload = payload
        self.headers = headers or {}
        self.args = query or {}

    def get_json(self, **kwargs):
        return self.payload


def _compile_functions(filename, globals_):
    tree = ast.parse(Path(filename).read_text())
    names = {'create_user', 'get_user_info', 'get_user_query',
             'set_user_info', 'save_chat', 'delete_chat', 'verified_uid'}
    funcs = []
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name in names:
            node.decorator_list = []
            funcs.append(node)
    script = ast.Module(body=funcs, type_ignores=[])
    ast.fix_missing_locations(script)
    exec(compile(script, str(filename), 'exec'), globals_)


def execute_handler(source, function, *, payload=None, token=None, query_token=None,
                    firebase_token_error=None, firebase_profile_error=None, path_id='safeid'):
    FakeFirebase.reset()
    FakeFirebase.token_error = firebase_token_error
    FakeFirebase.profile_error = firebase_profile_error
    headers = {'Authorization': f'Bearer {token}'} if token else {}
    req = FakeRequest(payload, headers=headers,
                      query={'id_token': query_token} if query_token else {})
    ns = {
        '__builtins__': __builtins__,
        'request': req,
        # Isolated AST handler tests intentionally stub transport parsing. The
        # real strict parser is covered by R12 unit and Flask HTTP integration.
        'request_json_object': req.get_json,
        'Firebase': FakeFirebase,
        'QueryManager': lambda query, profile: SimpleNamespace(response={'botResponse':'SYNTHETIC_OK'}),
        'jsonify': lambda payload: payload,
        'success_response': lambda payload, code: (payload, code),
        'error_response': lambda message, code: ({'error': message}, code),
        'extract_bearer': extract_bearer,
        'validate_profile': validate_profile,
        'validate_messages': validate_messages,
        'safe_identifier': safe_identifier,
        'bounded_text': bounded_text,
        'SecurityError': SecurityError,
        # Auth events are validated separately using live Flask and metrics.
        'audit_auth': lambda result: None,
        # Offline handler harness: protocol behavior is verified separately over HTTP.
        'HTTPException': type('SyntheticHTTPException', (Exception,), {}),
        'QuotaExceeded': QuotaExceeded,
        'QuotaUnavailable': QuotaUnavailable,
    }
    _compile_functions(source, ns)
    if function in {'save_chat', 'delete_chat'}:
        result = ns[function](path_id)
    else:
        result = ns[function]()
    return result, list(FakeFirebase.call_log)
