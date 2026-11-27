"""Isolated audit against deployed production, no credentials or provider secrets."""
import json, os, sys, unittest, urllib.request
@unittest.skipUnless(os.getenv('GITHUB_REF_NAME')=='audit/live-trace-cp16' and sys.version_info[:2]==(3,10),'isolated audit only')
class LiveTraceAudit(unittest.TestCase):
    def test_public_endpoint(self):
        for question in (
            'Find 5 Indian B2B SaaS startups in HR tech and summarize their positioning.',
            'Research the pros and cons of using a multi-agent architecture for customer support automation.'
        ):
            with self.subTest(question=question):
                req=urllib.request.Request('https://veritas-research-agent.vercel.app/api/research',data=json.dumps({'question':question,'mode':'live','use_model':True,'include_diagnostics':True}).encode(),headers={'Content-Type':'application/json'},method='POST')
                with urllib.request.urlopen(req,timeout=65) as response: report=json.load(response)
                safe={k:report.get(k) for k in ('question','status','confidence','plan','trace','metrics','sections','limitations')}
                for event in safe['trace']:
                    if event.get('stage')=='evidence_snapshot':
                        for record in event.get('records',[]): record['text']=record['text'][:450]
                print('AUDIT_JSON '+json.dumps(safe,ensure_ascii=True),flush=True)
                self.assertTrue(any(e.get('stage')=='evidence_snapshot' for e in report.get('trace',[])), 'diagnostics missing')
