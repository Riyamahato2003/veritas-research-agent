import json
import os
import unittest
from unittest.mock import patch
from api.research import request_report, capabilities

Q = 'Compare vector databases for RAG'

class WebTests(unittest.TestCase):
    def test_public_demo(self):
        with patch.dict(os.environ, {}, clear=True):
            status, r = request_report({'question': Q})
            self.assertEqual(status, 200)
            self.assertEqual(r['mode'], 'demo')
            self.assertTrue(r['metrics']['citation_integrity'])
            self.assertTrue(r['sources_used'])

    def test_outage(self):
        status, r = request_report({'question': Q, 'fault': 'outage'})
        self.assertEqual(status, 200)
        self.assertEqual(r['status'], 'insufficient')
        self.assertFalse(r['sources_used'])

    def test_validation(self):
        for data in (None, [], {'question': 42}, {'question': 'x'}, {'question': 'a'*601}, {'question': Q, 'fault': []}, {'question': Q, 'mode': 'fake'}, {'question': Q, 'use_model': 'true'}, {'question': Q, 'mode': 'live', 'fault': 'outage'}):
            self.assertEqual(request_report(data)[0], 400)

    def test_live_disabled_without_keys(self):
        with patch.dict(os.environ, {}, clear=True):
            self.assertFalse(capabilities()['live'])
            self.assertEqual(request_report({'question': Q, 'mode': 'live'})[0], 403)

    def test_public_live_with_groq(self):
        with patch.dict(os.environ, {'GROQ_API_KEY':'example-key'}, clear=True):
            self.assertTrue(capabilities()['live'])
            self.assertTrue(capabilities()['providers']['model'])
            self.assertFalse(capabilities()['access_code_required'])
            self.assertNotIn('example', json.dumps(capabilities()))
            with patch('api.research.run') as run:
                run.return_value.to_dict.return_value={'mode':'live'}
                self.assertEqual(request_report({'question': Q, 'mode': 'live'})[0],200)
                run.assert_called_once_with(Q,'live','none',True)

    def test_public_live_with_brave(self):
        with patch.dict(os.environ, {'BRAVE_API_KEY':'example-key','VERITAS_LIVE_ACCESS_CODE':'old-code'}, clear=True):
            self.assertTrue(capabilities()['live'])
            self.assertFalse(capabilities()['access_code_required'])
            self.assertTrue(capabilities()['providers']['web'])
            with patch('api.research.run') as run:
                run.return_value.to_dict.return_value={'mode':'live'}
                self.assertEqual(request_report({'question': Q,'mode':'live'})[0],200)

    def test_openai_key_not_used(self):
        with patch.dict(os.environ, {'OPENAI_API_KEY':'unused'}, clear=True):
            self.assertFalse(capabilities()['live'])
            self.assertFalse(capabilities()['providers']['model'])

if __name__ == '__main__': unittest.main()
