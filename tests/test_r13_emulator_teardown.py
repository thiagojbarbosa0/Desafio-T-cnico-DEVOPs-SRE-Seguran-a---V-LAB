"""Regression: emulator integration teardown must not delete all demo users."""
import ast
from pathlib import Path
import unittest

ROOT=Path(__file__).resolve().parents[1]

class TeardownScope(unittest.TestCase):
    def test_emulator_test_cleanup_targets_only_fixture_users(self):
        path=ROOT/'integration/test_official_emulators.py'
        tree=ast.parse(path.read_text())
        module=next(node for node in tree.body if isinstance(node, ast.ClassDef)
                    and node.name=='OfficialFlaskFirebaseEmulatorIntegration')
        method=next(node for node in module.body if isinstance(node,(ast.FunctionDef,ast.AsyncFunctionDef))
                    and node.name=='tearDownClass')
        code=ast.get_source_segment(path.read_text(),method)
        self.assertIn('for uid in (cls.alice_uid, cls.bob_uid)',path.read_text())
        self.assertIn('cls.cleanup_fixture_users()',code)
        self.assertIn("db.reference(f'users/{uid}').delete()",path.read_text())
        self.assertNotIn("db.reference('users').delete()",code)

if __name__=='__main__':unittest.main()
