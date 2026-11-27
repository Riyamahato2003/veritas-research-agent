import unittest
from veritas.agent import run
from veritas.contracts import Evidence
from veritas.planner import plan
from veritas.synthesis import candidates, approved_sections, coverage

Q='Compare the top 3 open-source vector databases for RAG.'
ROWS=[{'title':name+' vector database','url':'https://'+name.lower()+'.example/docs',
       'text':name+' is an open-source vector database supporting local deployment for RAG.'}
      for name in ('Alpha','Beta','Gamma')]

class ComparativeResearchTests(unittest.TestCase):
    def test_live_web_query_preserves_intent(self):
        self.assertEqual(next(s.query for s in plan(Q,{'web','wiki','github'},mode='live') if s.tool=='web'),Q)
        self.assertEqual(next(s.query for s in plan(Q,{'web'}) if s.tool=='web'),'vector database')

    def test_generic_entities_and_review(self):
        queries=[]
        def web(q,t): queries.append(q); return ROWS
        def model(q,e,t):
            return {'sections':[{'label':x.title.split()[0],'category':'candidate','claims':[{'statement':x.text,'source_id':x.id,'quote':x.text}]} for x in e]}
        def reviewer(q,cs,t): return {'verdicts':[{'id':c['id'],'supported':True} for c in cs]}
        r=run(Q,'live',adapters={'web':web},model_select=model,model_verify=reviewer)
        self.assertEqual(len(queries),3)
        self.assertEqual({s['label'] for s in r.sections},{'Alpha','Beta','Gamma'})
        self.assertEqual(r.metrics['coverage'],3)
        self.assertEqual(r.metrics['model_calls'],2)
        self.assertTrue(r.metrics['citation_integrity'])
        self.assertLessEqual(r.metrics['tool_attempts'],10)

    def test_cross_entity_fabricated_quotes_and_reviewer_fail_closed(self):
        e=Evidence('Alpha vector database',ROWS[0]['url'],ROWS[0]['text'],'web',id='S1')
        def proposal(label,quote):
            return {'sections':[{'label':label,'category':'candidate','claims':[{'statement':'This product supports local deployment.','source_id':'S1','quote':quote}]}]}
        self.assertEqual(candidates(proposal('Beta',e.text),[e],'list'),[])
        self.assertEqual(candidates(proposal('Alpha','Alpha has a fabricated GPU feature.'),[e],'list'),[])
        valid=candidates(proposal('Alpha',e.text),[e],'list')
        self.assertEqual(len(valid),1)
        for verdict in ({},{'verdicts':[{'id':'C1','supported':'true'}]},{'verdicts':[{'id':'C1','supported':True},{'id':'C1','supported':False}]}):
            self.assertEqual(approved_sections(valid,verdict),[])
        self.assertEqual(coverage(approved_sections(valid,{'verdicts':[{'id':'C1','supported':True}]}),'list',3),(1,3))

    def test_tradeoff_categories_and_model_rejection(self):
        q='Research the pros and cons of using a multi-agent architecture for customer support automation.'
        rows=[{'title':'Multi-agent customer support architecture','url':'https://example.org/support',
               'text':'Multi-agent customer support systems can specialize tasks but increase coordination complexity.'}]
        def model(q,e,t):
            return {'sections':[{'label':'Specialization','category':'benefit','claims':[{'statement':'Agents can specialize tasks.','source_id':e[0].id,'quote':e[0].text}]},
                {'label':'Coordination','category':'risk','claims':[{'statement':'Coordination complexity increases.','source_id':e[0].id,'quote':e[0].text}]}]}
        def reviewer(q,cs,t): return {'verdicts':[{'id':c['id'],'supported':c['category']=='benefit'} for c in cs]}
        r=run(q,'live',adapters={'web':lambda q,t:rows},model_select=model,model_verify=reviewer)
        self.assertEqual(r.metrics['claims_accepted'],1)
        self.assertEqual(r.metrics['claims_rejected'],1)
        self.assertEqual(r.status,'partial')
        self.assertNotIn('Coordination complexity increases.',r.short_answer)
        self.assertEqual(coverage(r.sections,'tradeoffs',2),(1,2))

    def test_review_outage_withholds_paraphrases(self):
        def model(q,e,t):
            return {'sections':[{'label':'Alpha','category':'candidate','claims':[{'statement':'Alpha offers local deployment.','source_id':e[0].id,'quote':e[0].text}]}]}
        def down(*args): raise RuntimeError('unavailable')
        r=run(Q,'live',adapters={'web':lambda q,t:ROWS},model_select=model,model_verify=down)
        self.assertFalse(r.sections)
        self.assertEqual(r.status,'partial')
        self.assertIn('Insufficient reviewed evidence',r.short_answer)
