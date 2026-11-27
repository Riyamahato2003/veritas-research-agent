import json, os, sys, unittest, urllib.request
@unittest.skipUnless(os.getenv('GITHUB_REF_NAME')=='audit/final-v2-coverage' and sys.version_info[:2]==(3,10),'isolated audit only')
class LiveTraceAudit(unittest.TestCase):
    def test_public_endpoint(self):
        q='Find 5 Indian B2B SaaS startups in HR tech and summarize their positioning.'
        req=urllib.request.Request('https://veritas-research-agent.vercel.app/api/research',data=json.dumps({'question':q,'mode':'live','use_model':True,'include_diagnostics':True}).encode(),headers={'Content-Type':'application/json'},method='POST')
        with urllib.request.urlopen(req,timeout=65) as response: r=json.load(response)
        safe={k:r.get(k) for k in ('status','confidence','metrics','research_intent','coverage_details','limitations')}
        safe['sections']=[{'label':s['label'],'claims':len(s['claims'])} for s in r['sections']]
        safe['trace']=[{k:v for k,v in e.items() if k not in ('records','selected_ids')} for e in r['trace'] if e['stage'] in ('model','claim_validation','claim_review','recovery')]
        print('AUDIT_JSON '+json.dumps(safe,ensure_ascii=True),flush=True)
        self.assertTrue(r['metrics']['citation_integrity'])
        self.assertEqual(r['research_intent']['named'],[])
        self.assertLessEqual(r['metrics']['model_calls'],5)
        self.assertLessEqual(r['metrics']['search_calls'],5)
        snap=next(e for e in r['trace'] if e['stage']=='evidence_snapshot')
        ids={p['id'] for p in snap['records']}
        for section in r['sections']:
            for claim in section['claims']:
                self.assertTrue(set(claim['passage_ids'])<=ids)
