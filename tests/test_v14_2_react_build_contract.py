"""Regression checks for the concrete TS6133/TS7016/TS2322/TS2741 errors
observed on Fedora. These are source-contract tests, not a TypeScript build.
"""
from pathlib import Path
import unittest

ROOT=Path(__file__).resolve().parents[1]
SRC=ROOT/'frontend/src'


class ReactCompileRegressionV142(unittest.TestCase):
    def read(self, rel):
        return (SRC/rel).read_text(encoding='utf-8')

    def test_nav_unused_is_mobile_removed(self):
        code=self.read('components/nav/Nav.tsx')
        self.assertNotIn('const isMobile = ',code)
        self.assertNotIn('useMediaQuery',code)
        self.assertNotIn('useTheme',code)

    def test_dashboard_handlers_ignore_unused_mui_event(self):
        code=self.read('pages/dashboard/Dashboard.tsx')
        self.assertNotIn('onChange={(event, newValue',code)
        self.assertNotIn('onChange = {(event, newValue',code)
        self.assertNotIn('onChange={(event: any, newValue',code)
        self.assertGreaterEqual(code.count('onChange={(_event,'),3)

    def test_about_field_is_react_controlled(self):
        code=self.read('pages/dashboard/Dashboard.tsx')
        self.assertIn('setAbout: (value: string) => void',code)
        self.assertIn('value={props.about}',code)
        self.assertIn('onChange={(event) => props.setAbout(event.target.value)}',code)

    def test_saved_profile_values_use_state_not_dom_queries(self):
        api=self.read('api.ts')
        dashboard=self.read('pages/dashboard/Dashboard.tsx')
        self.assertRegex(api, r'year: string,\s*college: string,\s*about: string')
        self.assertIn('props.year, props.college, props.about)',dashboard)
        self.assertNotIn('$("#year-output")',api)
        self.assertNotIn('$("#info-output")',api)

    def test_login_and_signup_without_jquery_type_dependency(self):
        api=self.read('api.ts')
        self.assertNotIn("from 'jquery'",api)
        self.assertIn('HTMLInputElement | null',api)
        for name in ('signup-email-input','signup-password-input','login-email-input','login-password-input'):
            self.assertIn("inputValue('"+name+"')",api)

    def test_course_section_is_optional_and_rendered_conditionally(self):
        interfaces=self.read('interfaces.d.ts')
        course=self.read('components/CourseCard/CourseCard.tsx')
        self.assertIn('sectionNumber?: string',interfaces)
        self.assertIn('{sectionNumber && <Typography',course)

    def test_unused_box_import_removed(self):
        self.assertNotIn('import { Box, ThemeProvider }',self.read('App.tsx'))

    def test_frontend_build_is_fail_closed(self):
        runner=(ROOT/'scripts/verify_frontend_build_v14_2.sh').read_text()
        self.assertIn('set -euo pipefail',runner)
        self.assertIn('npm ci --no-audit --no-fund',runner)
        self.assertIn('npm run build',runner)
        self.assertIn('frontend_fingerprint()',runner)
        self.assertIn('rm -f evidence/generated/FRONTEND_BUILD_V13.json',runner)


if __name__=='__main__':
    unittest.main()
