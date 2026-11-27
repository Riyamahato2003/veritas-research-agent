import unittest
from veritas.grounding import intent_from, coverage, review
from veritas.research_v2 import run_live
from veritas.tools import ToolError

Q='Compare the top 3 open-source vector databases for a startup building RAG products.'
ROWS=[{'title':n+' vector database','url':'https://'+n.lower()+'.example/docs',
       'text':n+' is an open-source vector database. '+n+' supports vector similarity search for RAG products.'}
      for n in ('Alpha','Beta','Gamma')]

class PrototypeReportingTests(unittest.TestCase):
    def test_nonoverlapping_numbered_rubric(self):
        i=intent_from(Q,{'facets':['open source license','scalability','startup usability']})
        self.assertEqual(len(i['facets']),3)
        self.assertEqual(i['target'],3)
    def test_named_unreviewed_candidate_is_coverage_gap_not_discovery_gap(self):
        q='Compare REST APIs, GraphQL and gRPC for microservices.'
        intent=intent_from(q,{'named':[],'facets':['performance','tooling']})
        claims=[{'label':'GraphQL','category':'candidate','requirement_id':'R1'},
                {'label':'gRPC','category':'candidate','requirement_id':'R1'}]
        result=coverage(intent,claims,['GraphQL','gRPC'])
        self.assertEqual(result['target'],3)
        self.assertEqual(result['need_more_candidates'],0)
        self.assertIn({'label':'REST APIs','requirements':['R1','R2']},result['missing'])
    def test_granular_not_all_or_nothing(self):
        i=intent_from(Q,None)
        claims=[{'label':n,'category':'candidate','requirement_id':rid} for n in ('Alpha','Beta','Gamma') for rid in ('R1','R2')]
        result=coverage(i,claims,['Alpha','Beta','Gamma'])
        self.assertEqual((result['covered'],result['candidates_reviewed'],result['facets_covered'],result['facets_target']),(0,3,6,9))
        self.assertFalse(result['complete'])
    def test_reviewer_corrects_valid_facet_only(self):
        i=intent_from(Q,None)
        c={'id':'C1','label':'Alpha','category':'candidate','statement':'Alpha supports vector similarity search.','requirement_id':'R1','passage_ids':['P1']}
        got,rej=review([c],{'verdicts':[{'id':'C1','supported':True,'reason':'supported','requirement_id':'R2'}]},i)
        self.assertEqual(got[0]['requirement_id'],'R2')
        self.assertEqual(got[0]['original_requirement_id'],'R1')
        self.assertEqual(got[0]['statement'],c['statement'])
        self.assertEqual(got[0]['passage_ids'],c['passage_ids'])
        self.assertFalse(rej)
        got,rej=review([c],{'verdicts':[{'id':'C1','supported':True,'reason':'supported','requirement_id':'R999'}]},i)
        self.assertFalse(got)
        self.assertEqual(rej,{'wrong_requirement':1})
    def test_partial_linked_claims_survive_provider_failure(self):
        calls=[]
        def model(stage,data,t):
            calls.append(stage)
            if stage=='intent': return {}
            if stage=='review':
                return {'verdicts':[{'id':c['id'],'supported':True,'reason':'supported','requirement_id':'R2' if 'similarity' in c['statement'] else 'R1'} for c in data['claims']]}
            if calls.count('synthesize')>1: raise ToolError('http_429:rate_limit_exceeded')
            return {'sections':[{'label':name,'category':'candidate','claims':[{'statement':p['text'],'requirement_id':'R1','passage_ids':[p['id']]} for p in data['passages'] if p['text'].startswith(name)]} for name in ('Alpha','Beta','Gamma')]}
        r=run_live(Q,adapters={'web':lambda q,t:ROWS},model=model)
        q=r.metrics['quality']
        self.assertEqual(r.status,'partial')
        self.assertEqual(r.confidence,'low')
        self.assertEqual(q['evidence_status'],'model_reviewed')
        self.assertEqual(q['claims_linked'],6)
        self.assertEqual(q['candidates_reviewed'],3)
        self.assertEqual(q['facets_covered'],6)
        self.assertEqual(q['provider_health'],'degraded')
        self.assertEqual(r.metrics['coverage'],0)
        self.assertTrue(all(name in r.short_answer for name in ('Alpha','Beta','Gamma')))
        self.assertTrue(any(e.get('classification_corrections')==3 for e in r.trace))
    def test_empty_evidence_not_green(self):
        r=run_live(Q,False,adapters={'web':lambda q,t:[]})
        self.assertEqual(r.metrics['quality']['evidence_status'],'no_evidence')
        self.assertEqual(r.metrics['quality']['claims_published'],0)
        self.assertEqual(r.metrics['quality']['claims_linked'],0)
        self.assertEqual(r.status,'insufficient')
    def test_review_rejects_extra_assertion(self):
        c={'id':'C1','category':'candidate','requirement_id':'R2','statement':'Alpha supports search and semantic schema features.'}
        a,r=review([c],{'verdicts':[{'id':'C1','supported':False,'reason':'not_entailed'}]},intent_from(Q,None))
        self.assertFalse(a)
        self.assertEqual(r,{'not_entailed':1})
