import unittest
from unittest.mock import patch
from veritas.tools import wiki, github, brave, ToolError
class AdapterTests(unittest.TestCase):
    @patch('veritas.tools.request_json',return_value={'query':{'pages':[{'title':'A','fullurl':'https://en.wikipedia.org/wiki/A','extract':'A description'}]}})
    def test_wiki_schema(self,m):
        self.assertEqual(wiki('research')[0]['title'],'A'); self.assertEqual(m.call_args.args[0],'https://en.wikipedia.org/w/api.php')
    @patch('veritas.tools.request_json',return_value={'items':[{'full_name':'o/r','html_url':'https://github.com/o/r','description':'A description'}]})
    def test_github_schema(self,m):
        self.assertEqual(github('research')[0]['title'],'o/r'); self.assertEqual(m.call_args.args[0],'https://api.github.com/search/repositories')
    @patch.dict('os.environ',{'BRAVE_API_KEY':'test-key'})
    @patch('veritas.tools.request_json',return_value={'web':{'results':[{'title':'A','url':'https://example.org','description':'A description'}]}})
    def test_brave_schema(self,m): self.assertEqual(brave('research')[0]['text'],'A description')
    @patch('veritas.tools.request_json',return_value={'unexpected':True})
    def test_github_bad_schema(self,m):
        with self.assertRaises(ToolError): github('research')
