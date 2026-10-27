"""UI security and presentation regression checks without browser dependencies."""
import re
import unittest
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / 'dashboard'

class UIParser(HTMLParser):
    def __init__(self):
        super().__init__(); self.ids=set(); self.buttons=[]; self.sections=[]
    def handle_starttag(self, tag, attrs):
        data=dict(attrs)
        if data.get('id'): self.ids.add(data['id'])
        if tag=='button': self.buttons.append(data)
        if tag=='section': self.sections.append(data)

class DashboardConsistencyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.html=(ROOT/'index.html').read_text()
        cls.css=(ROOT/'style.css').read_text()
        cls.js=(ROOT/'app.js').read_text()
        cls.dom=UIParser();cls.dom.feed(cls.html)

    def test_javascript_dom_references_exist(self):
        refs=set(re.findall(r"el\(['\"]([a-z][a-z0-9-]*)['\"]\)", self.js))
        self.assertFalse(refs-self.dom.ids, f'Missing HTML IDs: {refs-self.dom.ids}')

    def test_navigation_sections_exist(self):
        for name in ('overview','security','courses','reliability'):
            self.assertIn('view-'+name,self.dom.ids)
            self.assertIn(name,[button.get('data-view') for button in self.dom.buttons])

    def test_visual_is_neutral_and_accessible(self):
        self.assertIn('color-scheme:light', self.css)
        self.assertIn('prefers-reduced-motion:reduce', self.css)
        self.assertNotIn('text-shadow:',self.css)
        self.assertNotIn('box-shadow:0 0 20px',self.css)
        self.assertIn('aria-live="polite"',self.html)

    def test_no_html_injection_rendering(self):
        self.assertNotIn('.innerHTML',self.js)
        self.assertIn('name.textContent = course.title',self.js)

    def test_evidence_excludes_tokens(self):
        marker=self.js.split('lastEvidence = {schema:')[1].split('};')[0]
        self.assertNotIn('access_token',marker)
        self.assertNotIn('Bearer ',marker)

    def test_demo_scope_clearly_labeled(self):
        self.assertIn('dados sintéticos',self.html.lower())
        self.assertIn('não prova, isoladamente',self.html.lower())

if __name__=='__main__':unittest.main()
