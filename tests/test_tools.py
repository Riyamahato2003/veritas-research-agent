import unittest
from unittest.mock import patch
from veritas.tools import wiki, github, tavily, ToolError
class AdapterTests(unittest.TestCase):
    @patch('veritas.tools.request_json',return_value={'query':{'pages':[{'title':'A','fullurl':'https://en.wikipedia.org/wiki/A','extract':'A description'}]}})
    def test_wiki_schema(self,m):
        self.assertEqual(wiki('research')[0]['title'],'A'); self.assertEqual(m.call_args.args[0],'https://en.wikipedia.org/w/api.php')
    @patch('veritas.tools.request_json',return_value={'items':[{'full_name':'o/r','html_url':'https://github.com/o/r','description':'A description'}]})
    def test_github_schema(self,m):
        self.assertEqual(github('research')[0]['title'],'o/r'); self.assertEqual(m.call_args.args[0],'https://api.github.com/search/repositories')
    @patch.dict('os.environ',{'TAVILY_API_KEY':'test-key'},clear=True)
    @patch('veritas.tools.request_json',return_value={'results':[{'title':'A','url':'https://example.org','content':'A description'}]})
    def test_tavily_schema_and_budget(self,m):
        self.assertEqual(tavily('research')[0]['text'],'A description')
        self.assertEqual(m.call_args.args[0],'https://api.tavily.com/search')
        self.assertEqual(m.call_args.kwargs['headers']['Authorization'],'Bearer test-key')
        payload=m.call_args.kwargs['payload']
        self.assertEqual(payload['search_depth'],'basic')
        self.assertEqual(payload['max_results'],5)
        self.assertFalse(payload['auto_parameters'])
        self.assertFalse(payload['include_answer'])
        self.assertFalse(payload['include_raw_content'])
    @patch.dict('os.environ',{'TAVILY_API_KEY':'test-key'},clear=True)
    @patch('veritas.tools.request_json',return_value={'unexpected':True})
    def test_tavily_bad_schema(self,m):
        with self.assertRaises(ToolError): tavily('research')
    @patch.dict('os.environ',{},clear=True)
    @patch('veritas.tools.request_json')
    def test_tavily_missing_key(self,m):
        with self.assertRaises(ToolError): tavily('research')
        m.assert_not_called()
    @patch('veritas.tools.request_json',return_value={'unexpected':True})
    def test_github_bad_schema(self,m):
        with self.assertRaises(ToolError): github('research')
