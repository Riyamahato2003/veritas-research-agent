"""Production smoke on known public questions; no keys or private inputs."""
import json, os, sys, unittest, urllib.request
@unittest.skipUnless(os.getenv('GITHUB_REF_NAME')=='audit/live-v2-smoke' and sys.version_info[:2]==(3,10),'isolated audit only')
class LiveTraceAudit(unittest.TestCase):
    def test_public_endpoint(self):
        for question in (
            'Find 5 Indian B2B SaaS startups in HR tech and summarize their positioning.',
            'Research the pros and cons of using a multi-agent architecture for customer support automation.',
            'Compare open-source workflow orchestration tools for a small data engineering team.'
        ):
            with self.subTest(question=question):
                req=urllib.request.Request('https://veritas-research-agent.vercel.app/api/research',data=json.dumps({'question':question,'mode':'live','use_model':True,'include_diagnostics':True}).encode(),headers={'Content-Type':'application/json'},method='POST')
                with urllib.request.urlopen(req,timeout=65) as response: report=json.load(response)
                safe={k:report.get(k) for k in ('question','status','confidence','metrics','research_intent','coverage_details','limitations','sections')}
                for s in safe['sections']:
                    for c in s['claims']:
                        c['quote']=c['quote'][:220]
                        c.pop('passages',None)
                safe['trace']=[{k:v for k,v in e.items() if k not in ('records','selected_ids')} for e in report['trace'] if e['stage']!='evidence_snapshot']
                print('AUDIT_JSON '+json.dumps(safe,ensure_ascii=True),flush=True)
                self.assertEqual(report['metrics']['engine_version'],'cp17-23-v2')
                self.assertTrue(report['metrics']['citation_integrity'])
                self.assertLessEqual(report['metrics']['model_calls'],5)
                self.assertLessEqual(report['metrics']['search_calls'],5)
                self.assertTrue(any(e['stage']=='evidence_snapshot' for e in report['trace']))
