import json
import tempfile
import unittest
from pathlib import Path
from scripts.npm_audit_triage_vlab import triage, main
from scripts.evidence_integrity_vlab import EvidenceError

class NpmTriageTests(unittest.TestCase):
    def setUp(self):
        self.full={'vulnerabilities':{
            'vite':{'severity':'moderate','isDirect':True,'fixAvailable':True,'via':[1]},
            'legacy-pkg':{'severity':'critical','isDirect':False,'fixAvailable':{'name':'x','version':'10'},'via':[1,2]},
            'react':{'severity':'low','isDirect':True,'fixAvailable':False,'via':[]}}}
        self.prod={'vulnerabilities':{'legacy-pkg':self.full['vulnerabilities']['legacy-pkg'],
                                      'react':self.full['vulnerabilities']['react']}}
    def test_with_production(self):
        x=triage(self.full,self.prod)
        self.assertEqual(x['priority'],'P0')
        self.assertEqual(x['production_counts_by_severity']['critical'],1)
        self.assertEqual(next(i for i in x['items'] if i['package']=='vite')['exposure'],'dev_only_by_audit')
        self.assertEqual(next(i for i in x['items'] if i['package']=='legacy-pkg')['fix_type'],'major_or_explicit_change')
    def test_no_production_is_not_green(self):
        x=triage(self.full)
        self.assertEqual(x['priority'],'P1_review_required')
        self.assertIsNone(x['production_counts_by_severity'])
        self.assertTrue(all(i['exposure']=='not_measured' for i in x['items']))
    def test_empty_clean_audit(self):
        self.assertEqual(triage({'vulnerabilities':{}},{'vulnerabilities':{}})['priority'],'none_reported')
    def test_missing_required_field(self):
        with self.assertRaises(EvidenceError):triage({'metadata':{'vulnerabilities':{}}})
    def test_bad_severity(self):
        self.full['vulnerabilities']['vite']['severity']='severe'
        with self.assertRaises(EvidenceError):triage(self.full)
    def test_bad_package_name(self):
        self.full['vulnerabilities']['../../etc/passwd']=self.full['vulnerabilities'].pop('vite')
        with self.assertRaises(EvidenceError):triage(self.full)
    def test_impossible_prod_report(self):
        self.prod['vulnerabilities']['not-in-full']={'severity':'high'}
        with self.assertRaises(EvidenceError):triage(self.full,self.prod)
    def test_strict_metadata_requirement_rejects_incomplete_report(self):
        with self.assertRaises(EvidenceError):triage(self.full,self.prod,require_metadata=True)
    def test_strict_metadata_accepts_coherent_audit_v2(self):
        for report in (self.full,self.prod):
            report['auditReportVersion']=2
            values=report['vulnerabilities'].values()
            counts={name:sum(x['severity']==name for x in values)
                    for name in ('critical','high','moderate','low','info')}
            counts['total']=len(report['vulnerabilities'])
            report['metadata']={'vulnerabilities':counts}
        self.assertTrue(triage(self.full,self.prod,require_metadata=True)['validated'])
    def test_rejects_npm_tool_error(self):
        with self.assertRaises(EvidenceError):
            triage({'error':{'code':'EAUDITNOLOCK'},'vulnerabilities':{}})
    def test_rejects_wrong_metadata_total(self):
        self.full['metadata']={'vulnerabilities':{'critical':2,'moderate':1,'low':1,'total':4}}
        with self.assertRaises(EvidenceError):triage(self.full)
    def test_rejects_severity_disagreement_between_reports(self):
        import copy
        self.prod=copy.deepcopy(self.prod)
        self.prod['vulnerabilities']['react']['severity']='high'
        with self.assertRaises(EvidenceError):triage(self.full,self.prod)
    def test_rejects_unknown_production_scope_in_strict_mode(self):
        with tempfile.TemporaryDirectory() as td:
            folder=Path(td)
            full=folder/'full.json'; lock=folder/'package-lock.json'
            full.write_text(json.dumps(self.full));lock.write_text('{}')
            self.assertEqual(main(['--full',str(full),'--lock',str(lock),'--fail-on-prod-high']),2)
    def test_rejects_critical_production_in_strict_mode(self):
        with tempfile.TemporaryDirectory() as td:
            folder=Path(td)
            full=folder/'full.json';prod=folder/'prod.json';lock=folder/'package-lock.json'
            full.write_text(json.dumps(self.full));prod.write_text(json.dumps(self.prod));lock.write_text('{}')
            self.assertEqual(main(['--full',str(full),'--production',str(prod),'--lock',str(lock),'--fail-on-prod-high']),2)
    def test_cli_file(self):
        with tempfile.TemporaryDirectory() as td:
            full=Path(td)/'full.json';prod=Path(td)/'prod.json';out=Path(td)/'triage.json'
            full.write_text(json.dumps(self.full));prod.write_text(json.dumps(self.prod))
            self.assertEqual(main(['--full',str(full),'--production',str(prod),'--output',str(out)]),0)
            self.assertTrue(json.loads(out.read_text())['validated'])

if __name__=='__main__': unittest.main()
