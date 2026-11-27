import os
import unittest
from unittest.mock import patch
from veritas.contracts import Evidence
from veritas.model import select
from veritas.tools import ToolError

E = [Evidence('Test','https://example.org','A relevant evidence passage for the question.','web',id='S1')]

class GroqContractTests(unittest.TestCase):
    def test_groq_endpoint_and_json_mode(self):
        with patch.dict(os.environ, {'GROQ_API_KEY':'test-key'}, clear=True), patch('veritas.model.request_json') as request:
            request.return_value={'choices':[{'message':{'content':'{"findings":[{"source_id":"S1","quote":"A relevant evidence passage for the question."}]}'}}]}
            self.assertEqual(select('Research question', E)['findings'][0]['source_id'],'S1')
            args, kwargs = request.call_args
            self.assertEqual(args[0],'https://api.groq.com/openai/v1/chat/completions')
            self.assertEqual(kwargs['headers']['Authorization'],'Bearer test-key')
            self.assertEqual(kwargs['payload']['model'],'openai/gpt-oss-120b')
            self.assertEqual(kwargs['payload']['response_format'],{'type':'json_object'})
            self.assertEqual(kwargs['payload']['reasoning_effort'],'low')
    def test_model_override_and_malformed(self):
        with patch.dict(os.environ, {'GROQ_API_KEY':'test-key','GROQ_MODEL':'custom-model'}, clear=True), patch('veritas.model.request_json') as request:
            request.return_value={'choices':[]}
            with self.assertRaises(ToolError):
                select('Research question', E)
            self.assertEqual(request.call_args.kwargs['payload']['model'],'custom-model')
            self.assertNotIn('reasoning_effort',request.call_args.kwargs['payload'])
    def test_no_groq_key_does_not_call_openai(self):
        with patch.dict(os.environ, {'OPENAI_API_KEY':'unused'}, clear=True), patch('veritas.model.request_json') as request:
            self.assertIsNone(select('Research question', E))
            request.assert_not_called()
