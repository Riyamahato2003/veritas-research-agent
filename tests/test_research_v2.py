import unittest
from veritas.research_v2 import run_live
from veritas.grounding import Index, intent_from, validate, review, coverage
from veritas.tools import ToolError

Q='Find 2 Indian HR SaaS companies and describe their positioning.'
ROWS=[{'title':'Alpha HR SaaS','url':'https://alpha.example/docs','text':'Alpha is an Indian HR SaaS company. Alpha offers payroll automation for HR teams.','provider_score':.9},
      {'title':'Beta HR SaaS','url':'https://beta.example/docs','text':'Beta is an Indian HR SaaS company. Beta offers HR performance management for businesses.','provider_score':.8}]

class V2Tests(unittest.TestCase):
    def test_ids_stable_and_exact(self):
        idx=Index(Q); idx.add(ROWS,'web',Q)
        before=set(idx.passages); idx.add(list(reversed(ROWS)),'web',Q)
        self.assertEqual(before,set(idx.passages))
        self.assertTrue(all(p.text in idx.sources[p.source_id].text for p in idx.passages.values()))
    def test_target_and_unknown_id(self):
        idx=Index(Q); idx.add(ROWS,'web',Q)
        intent=intent_from(Q,{'facets':[],'queries':['unrelated football']})
        self.assertEqual(intent['target'],2)
        claim={'sections':[{'label':'Alpha','category':'candidate','claims':[{'statement':'Alpha offers payroll automation.','requirement_id':'R2','passage_ids':['made-up']}]}]}
        valid,labels,audit=validate(claim,idx,intent,list(idx.passages))
        self.assertFalse(valid); self.assertEqual(audit['rejections']['unknown_passage_id'],1)
    def test_wrong_entity_and_numbers(self):
        idx=Index(Q); idx.add(ROWS,'web',Q); intent=intent_from(Q,None)
        p=next(p for p in idx.passages.values() if 'Alpha offers' in p.text)
        claim={'sections':[{'label':'Beta','category':'candidate','claims':[{'statement':'Beta offers payroll automation.','requirement_id':'R2','passage_ids':[p.id]}]},
                           {'label':'Alpha','category':'candidate','claims':[{'statement':'Alpha serves 500 companies.','requirement_id':'R2','passage_ids':[p.id]}]}]}
        valid,_,audit=validate(claim,idx,intent,list(idx.passages))
        self.assertFalse(valid); self.assertEqual(audit['rejections'],{'entity_not_in_evidence':1,'unsupported_number':1})
    def test_reviewer_fail_closed(self):
        c={'id':'C1'}
        self.assertEqual(review([c],{'verdicts':[{'id':'C1','supported':True},{'id':'C1','supported':True}]}),([],{'duplicate_verdict':1}))
        self.assertEqual(review([c],None),([],{'missing_verdict':1}))
    def test_end_to_end_coverage_recovery(self):
        calls=[]
        def web(q,t):
            calls.append(q)
            return ROWS[:1] if len(calls)<=2 else ROWS
        def model(stage,data,t):
            if stage=='intent': return {'queries':['Indian HR SaaS companies'], 'facets':[]}
            if stage=='review': return {'verdicts':[{'id':c['id'],'supported':True,'reason':'supported'} for c in data['claims']]}
            sections=[]
            for name in ('Alpha','Beta'):
                ps=[p for p in data['passages'] if p['text'].startswith(name)]
                if len(ps)>=2:
                    sections.append({'label':name,'category':'candidate','claims':[
                        {'statement':p['text'],'requirement_id':'R1' if 'Indian' in p['text'] else 'R2','passage_ids':[p['id']]} for p in ps]})
            return {'sections':sections}
        r=run_live(Q,adapters={'web':web},model=model,include_diagnostics=True)
        self.assertEqual(r.status,'complete')
        self.assertEqual(r.metrics['coverage'],2)
        self.assertTrue(r.metrics['recovery_triggered'])
        self.assertEqual(r.metrics['model_calls'],5)
        self.assertTrue(r.metrics['citation_integrity'])
        self.assertLessEqual(r.metrics['search_calls'],5)
        self.assertTrue(any(e['stage']=='evidence_snapshot' for e in r.trace))
    def test_partial_eligibility_not_full_coverage(self):
        intent=intent_from(Q,None)
        c={'label':'Alpha','category':'candidate','requirement_id':'R2'}
        out=coverage(intent,[c],['Alpha'])
        self.assertEqual(out['covered'],0); self.assertFalse(out['complete'])
    def test_model_failure_no_fabrication(self):
        def bad(stage,data,t): raise ToolError('http_429:rate_limit_exceeded')
        r=run_live(Q,adapters={'web':lambda q,t:ROWS},model=bad)
        self.assertFalse(r.sections); self.assertIn('http_429:rate_limit_exceeded',r.metrics['error_counts'])
        self.assertEqual(r.status,'partial')
        self.assertFalse(any(e['stage']=='evidence_snapshot' for e in r.trace))
    def test_total_outage(self):
        def down(*a): raise ToolError('network_error',True)
        r=run_live(Q,False,adapters={'web':down})
        self.assertEqual(r.status,'insufficient'); self.assertFalse(r.sources_used)
        self.assertLessEqual(r.metrics['search_calls'],5)
    def test_noisy_title_and_source_rejection(self):
        idx=Index(Q)
        rows=[{'title':'Top HR SaaS agencies','url':'https://agency.example','text':'Indian HR SaaS company agency for marketing.'},
              {'title':'Alpha HR SaaS','url':'https://127.0.0.1/private','text':'Alpha is an Indian HR SaaS company.'}]
        a,r=idx.add(rows,'web',Q)
        self.assertFalse(a); self.assertEqual(r,{'off_intent_title':1,'invalid_url':1})
