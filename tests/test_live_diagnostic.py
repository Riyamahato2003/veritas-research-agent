"""Temporary isolated audit: public endpoint only, no API keys, no secrets."""
import json, os, sys, unittest, urllib.request
@unittest.skipUnless(os.getenv('GITHUB_REF_NAME')=='audit/live-trace-cp15' and sys.version_info[:2]==(3,10), 'isolated audit only')
class LiveTraceAudit(unittest.TestCase):
    def test_public_endpoint(self):
        for question in (
            'Find 5 Indian B2B SaaS startups in HR tech and summarize their positioning.',
            'Research the pros and cons of using a multi-agent architecture for customer support automation.'
        ):
            with self.subTest(question=question):
                req=urllib.request.Request('https://veritas-research-agent.vercel.app/api/research',data=json.dumps({'question':question,'mode':'live','use_model':True}).encode(),headers={'Content-Type':'application/json'},method='POST')
                with urllib.request.urlopen(req,timeout=65) as response:
                    report=json.load(response)
                safe={k:report.get(k) for k in ('question','status','confidence','plan','trace','metrics','sections','limitations')}
                safe['sources']=[{'id':x['id'],'title':x['title'],'tool':x['tool'],'url':x['url'],'text':x['text'][:650]} for x in report.get('sources_used',[])]
                print('AUDIT_JSON '+json.dumps(safe,ensure_ascii=True),flush=True)
                self.assertIsInstance(report.get('trace'),list)
