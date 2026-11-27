import unittest
from veritas.agent import run, linked_analysis
from veritas.contracts import Evidence, Finding
from veritas.planner import plan
from veritas.comparison import cards

Q = 'Compare the top 3 open-source vector databases for a startup building RAG products.'
ROWS = [
    {'title':'Qdrant vector database','url':'https://qdrant.tech/docs','text':'Qdrant vector database supports local deployment and metadata filtering.'},
    {'title':'Milvus vector database','url':'https://milvus.io/docs','text':'Milvus vector database supports distributed deployment and sharding.'},
    {'title':'Chroma vector database','url':'https://docs.trychroma.com/guide','text':'Chroma vector database offers local deployment and similarity search.'},
]
class ComparativeResearchTests(unittest.TestCase):
    def test_live_web_query_preserves_intent(self):
        live=plan(Q,{'web','wiki','github'},mode='live')
        self.assertEqual(next(s.query for s in live if s.tool=='web'),Q)
        self.assertEqual(next(s.query for s in plan(Q,{'web'}) if s.tool=='web'),'vector database')

    def test_candidate_queries_and_cards_with_exact_passages(self):
        queries=[]
        def web(q,t):
            queries.append(q)
            return ROWS
        def model(q,e,t):
            return {'findings':[{'source_id':x.id,'quote':x.text} for x in e[:1]],
                    'analysis':[{'statement':'Milvus scales to billions with GPU acceleration.','source_ids':[e[0].id]}]}
        r=run(Q,'live',adapters={'web':web},model_select=model)
        self.assertEqual(len(queries),4)
        self.assertEqual({x['entity'] for x in r.comparison},{'Qdrant','Milvus','Chroma'})
        self.assertFalse(r.analysis)
        self.assertEqual(r.metrics['distinct_candidates'],3)
        self.assertEqual(r.status,'partial')
        self.assertTrue(r.metrics['citation_integrity'])
        self.assertLessEqual(r.metrics['tool_attempts'],12)
        for row in r.comparison:
            for item in row['evidence']:
                source=next(x for x in r.sources_used if x.id==item['source_id'])
                self.assertIn(item['quote'],source.text)
                self.assertIn(row['entity'],item['quote'])

    def test_reject_cross_entity_and_unverified_paraphrase(self):
        e=Evidence('Qdrant vector database',ROWS[0]['url'],ROWS[0]['text'],'web',id='S1')
        f=Finding(e.text,['S1'])
        proposal={'analysis':[{'statement':e.text,'source_ids':['S1']},
                              {'statement':'Milvus vector database supports GPU acceleration.','source_ids':['S1']},
                              {'statement':'Qdrant vector database is ranked first globally.','source_ids':['S1']}]}
        self.assertEqual(linked_analysis(proposal,[f],[e]),[f])
        self.assertEqual([x['entity'] for x in cards(Q,[e])],['Qdrant'])
