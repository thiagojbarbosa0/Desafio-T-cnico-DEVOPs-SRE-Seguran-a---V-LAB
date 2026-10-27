"""Safeguards for production/frontend contracts identified during V15 review.

These are offline source-contract checks and do NOT replace tsc/Vite or
browser tests. The release report labels them explicitly.
"""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
API = ROOT / 'frontend/src/api.ts'
CHAT = ROOT / 'frontend/src/components/ChatInterface/ChatInterface.tsx'
DASHBOARD = ROOT / 'frontend/src/pages/dashboard/Dashboard.tsx'
RUNNER = ROOT / 'scripts/verify_frontend_build_v14_2.sh'

class FrontendIntegrityV15(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.api = API.read_text(encoding='utf-8')
        cls.chat = CHAT.read_text(encoding='utf-8')
        cls.dashboard = DASHBOARD.read_text(encoding='utf-8')

    def test_no_synthetic_bot_reply_after_request_failure(self):
        self.assertIn('if (!response.ok || !sameUser(user.uid)) throw new Error', self.api)
        self.assertIn("throw new Error('Invalid API response')", self.api)
        self.assertNotIn('Não foi possível obter recomendações. Tente novamente.', self.api)

    def test_authentication_failure_not_returned_as_successful_reply(self):
        self.assertIn("if (!user || user.uid !== expectedUid) throw new Error('Session changed')", self.api)

    def test_api_response_checked_before_persisting_bot_message(self):
        self.assertIn("typeof result.botResponse !== 'string'", self.api)
        self.assertIn('!Array.isArray(result.newRecommendations)', self.api)
        self.assertIn('await fetchCourseSphereResponse(text, uid)', self.chat)
        self.assertIn('await saveCourseSphereChat(chatId.current', self.chat)

    def test_network_and_save_failures_are_distinct(self):
        self.assertIn('const [replyError, setReplyError]', self.chat)
        self.assertIn('const [saveError, setSaveError]', self.chat)
        self.assertIn('setReplyError(true)', self.chat)
        self.assertIn('setSaveError(true)', self.chat)

    def test_profile_auth_listener_has_cleanup(self):
        self.assertIn('const unsubscribe = onAuthStateChanged(auth, async (user)', self.api)
        self.assertIn('return () => { active = false; pending?.abort(); gate.begin(null); unsubscribe(); };', self.api)
        self.assertIn('return setProfileInfoIfLoggedIn(', self.dashboard)
        self.assertNotIn('async function setProfileInfoIfLoggedIn(', self.api)

    def test_new_user_without_profile_is_not_treated_as_error(self):
        self.assertIn('if (data === null) return;', self.api)
        self.assertIn("if (!response.ok) throw new Error('Profile request failed')",self.api)

    def test_build_evidence_requires_npm_compile(self):
        build = RUNNER.read_text(encoding='utf-8')
        self.assertIn('npm ci --no-audit --no-fund', build)
        self.assertIn('npm run build', build)
        self.assertIn('set -euo pipefail', build)
        self.assertLess(build.index('npm ci --no-audit'),build.index('npm run build'))
        self.assertIn("'validated': True", build)

if __name__ == '__main__':
    unittest.main()
