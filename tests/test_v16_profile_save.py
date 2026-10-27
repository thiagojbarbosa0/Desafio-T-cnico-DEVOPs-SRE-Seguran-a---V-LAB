"""Frontend contract guards. A full Vite build is still required on Fedora/CI."""
import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
class ProfileSaveSafety(unittest.TestCase):
    def test_success_only_after_awaited_response(self):
        source=(ROOT/'frontend/src/api.ts').read_text()
        block=source.split('async function saveProfileChanges',1)[1].split('This functions sends the query',1)[0]
        self.assertIn("await fetch(apiUrl('/users/info')",block)
        self.assertIn("if (!response.ok || !sameUser(user.uid)) throw",block)
        self.assertLess(block.index("if (!response.ok || !sameUser(user.uid))"), block.index("toast.success("))
        self.assertNotIn('toast.error(`',block)
    def test_save_button_disables_duplicate_requests(self):
        source=(ROOT/'frontend/src/pages/dashboard/Dashboard.tsx').read_text()
        block=source.split('const SaveButton',1)[1].split('const Dashboard',1)[0]
        self.assertIn('if (saving) return;',block)
        self.assertIn('disabled={saving}',block)
        self.assertIn('await saveProfileChanges',block)
        self.assertIn('finally {',block)
if __name__=='__main__': unittest.main()
