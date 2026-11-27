import unittest
from unittest.mock import patch
from veritas.agent import run
from veritas.contracts import Evidence
from veritas.synthesis import candidates
from veritas.tools import ToolError
from api.research import request_report

class DiagnosticTests(unittest.TestCase):
    def test_validation_reasons(self):
        e=Evidence('Alpha','https://example.org','Alpha offers local vector database deployment.','web',id='S1')
        p={'sections':[{'label':'Alpha','category':'candidate','claims':[
            {'source_id':'S1','statement':'Alpha offers local deployment.','quote':e.text},
            {'source_id':'S1','statement':'Alpha offers local deployment.','quote':'Alpha offers a fabricated feature.'},
            {'source_id':'S9','statement':'Alpha offers local deployment.','quote':e.text}]}]}
        audit={}
        self.assertEqual(len(candidates(p,[e],'list',audit)),1)
        self.assertEqual(audit['raw_claims'],3)
        self.assertEqual(audit['rejections'],{'quote_not_exact':1,'unknown_source_id':1})

    def test_error_type_and_snapshot(self):
        row={'title':'Vector database','url':'https://example.org/docs','text':'Vector database supports similarity retrieval for RAG.'}
        def down(*args): raise ToolError('http_429:rate_limit_exceeded')
        r=run('Compare vector databases for RAG','live',adapters={'web':lambda q,t:[row]},model_select=down,include_diagnostics=True)
        self.assertIn('http_429:rate_limit_exceeded',[x.get('error') for x in r.trace])
        self.assertTrue(any(x['stage']=='evidence_snapshot' for x in r.trace))
        r=run('Compare vector databases for RAG','live',adapters={'web':lambda q,t:[row]},model_select=down)
        self.assertFalse(any(x['stage']=='evidence_snapshot' for x in r.trace))

    def test_invalid_diagnostics(self):
        self.assertEqual(request_report({'question':'valid question','include_diagnostics':'yes'})[0],400)
