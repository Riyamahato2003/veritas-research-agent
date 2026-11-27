import unittest
from unittest.mock import patch
from veritas.agent import run, normalize, verified_findings
from veritas.contracts import Evidence
from veritas.tools import ToolError, request_json
from veritas.planner import plan
Q='Compare the top 3 open-source vector databases for a startup building RAG products.'
class AgentTests(unittest.TestCase):
    def test_vector_grounding(self):
        r=run(Q); self.assertEqual(r.mode,'demo'); self.assertGreaterEqual(len(r.sources_used),3)
        text=' '.join(x.title for x in r.sources_used).lower()
        for name in ('qdrant','milvus','weaviate'): self.assertIn(name,text)
        self.assertEqual(r.status,'partial'); self.assertEqual(r.confidence,'low'); self.assertTrue(r.metrics['citation_integrity'])
        for f in r.key_findings: self.assertTrue(any(f.statement in s.text and s.id in f.source_ids for s in r.sources_used))
    def test_business_routes(self):
        r=run('Find 5 Indian B2B SaaS startups in HR tech and summarize their positioning.')
        self.assertEqual(r.plan[0].tool,'web'); self.assertEqual(len(r.sources_used),5)
        self.assertNotIn('github',[s.tool for s in r.plan])
    def test_architecture(self):
        r=run('Research the pros and cons of using a multi-agent architecture for customer support automation.')
        self.assertGreaterEqual(len(r.sources_used),2); self.assertNotIn('LangGraph', [x.title for x in r.sources_used])
    def test_memory(self):
        r=run('Compare different approaches to adding memory in an AI support agent.')
        self.assertGreaterEqual(len(r.sources_used),2); self.assertNotIn('Microsoft AutoGen', [x.title for x in r.sources_used])
    def test_timeout(self):
        r=run(Q,fault='timeout'); self.assertEqual(r.status,'partial'); self.assertEqual(r.confidence,'low')
        self.assertEqual(len([t for t in r.trace if t.get('tool')=='github' and t['status']=='error']),2)
        self.assertTrue(r.key_findings)
    def test_outage(self):
        r=run(Q,fault='outage'); self.assertEqual(r.status,'insufficient'); self.assertFalse(r.key_findings); self.assertFalse(r.sources_used); self.assertEqual(r.metrics['tool_attempts'],8)
    def test_transient(self):
        r=run(Q,fault='transient'); self.assertTrue(r.key_findings); self.assertEqual(r.metrics['tool_attempts'],6)
    def test_malformed(self):
        r=run(Q,fault='malformed'); self.assertTrue(r.key_findings); self.assertTrue(any(t.get('error')=='malformed_schema' for t in r.trace))
    def test_injection(self):
        r=run(Q,fault='injection'); self.assertTrue(any('suspected_injection' in t.get('rejected',[]) for t in r.trace)); self.assertNotIn('example.org/injection',str(r.to_dict()))
    def test_noise(self):
        r=run(Q,fault='noise'); self.assertTrue(any('weak_relevance' in t.get('rejected',[]) for t in r.trace))
    def test_unknown(self):
        r=run('Explain xenoflux quorbanic tessellation.'); self.assertEqual(r.status,'insufficient'); self.assertEqual(len(r.plan),3)
    def test_bad_citation(self):
        e=[Evidence('Example','https://example.org','This is an exact passage from a source.','web',id='S1')]
        for bad in [{'findings':[{'source_id':'S9','quote':e[0].text}]},{'findings':[{'source_id':'S1','quote':'This is an invented passage from a source.'}]},{'findings':[{'source_id':[], 'quote':True}]}]: self.assertEqual(verified_findings(bad,e),[])
        self.assertEqual(len(verified_findings({'findings':[{'source_id':'S1','quote':e[0].text}]},e)),1)
    def test_invalid_url(self):
        rows=[{'title':'Vector database','url':'https://evil.example','text':'Vector database with similarity search.'}]
        self.assertEqual(normalize(rows,'github',Q,'vector database')[1],['invalid_url'])
    def test_bad_input(self):
        for q in (' ', 'x'*601):
            with self.assertRaises(ValueError): run(q)
        with self.assertRaises(ValueError): run(Q,'live','outage')
    def test_live_adapter_mock_model_reject(self):
        row={'title':'Vector database','url':'https://github.com/org/repo','text':'Vector database supports similarity retrieval.'}
        r=run(Q,'live',adapters={'github':lambda q,t:[row]},model_select=lambda *a:{'findings':[{'source_id':'S99','quote':'invented statement that should never appear'}]})
        self.assertTrue(r.key_findings); self.assertTrue(any('Model returned no verifiable' in x for x in r.limitations)); self.assertNotIn('invented statement',str(r.to_dict()))
    def test_live_adapter_mock_model_success(self):
        row={'title':'Vector database','url':'https://github.com/org/repo','text':'Vector database supports similarity retrieval.'}
        r=run(Q,'live',adapters={'github':lambda q,t:[row]},model_select=lambda q,e,t:{'findings':[{'source_id':e[0].id,'quote':row['text']}]})
        self.assertTrue(any(t.get('status')=='verified' for t in r.trace)); self.assertEqual(r.metrics['model_calls'],1)
    def test_bound(self):
        r=run(Q,fault='outage'); self.assertLessEqual(len(r.plan),4); self.assertLessEqual(r.metrics['tool_attempts'],8)
    def test_duplicate(self):
        row={'title':'Vector database','url':'https://github.com/org/repo','text':'Vector database supports similarity retrieval.'}
        r=run(Q,'live',use_model=False,adapters={'github':lambda q,t:[row,row]}); self.assertEqual(len(r.sources_used),1)
    def test_live_no_fixture_fallback(self):
        def down(q,t): raise ToolError('network_error',True)
        r=run(Q,'live',use_model=False,adapters={'github':down,'wiki':down}); self.assertEqual(r.status,'insufficient'); self.assertEqual(r.mode,'live'); self.assertFalse(r.sources_used)
if __name__=='__main__': unittest.main()
