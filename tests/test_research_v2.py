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
    def test_candidate_claim_rejects_passage_without_entity_attribution(self):
        q='Compare open-source vector databases Qdrant and LanceDB.'
        rows=[{'title':'Qdrant vector database','url':'https://qdrant.example/docs','text':'Qdrant is an open-source vector database. Qdrant supports metadata filtering.'},
              {'title':'General vector database techniques','url':'https://guide.example/vector','text':'This vector database supports index compression and hybrid search.'}]
        idx=Index(q); idx.add(rows,'web',q); intent=intent_from(q,None)
        ps=list(idx.passages.values())
        proposal={'sections':[{'label':'Qdrant','category':'candidate','claims':[{'statement':'Qdrant supports metadata filtering and hybrid search.','requirement_id':'R2','passage_ids':[p.id for p in ps]}]}]}
        valid,_,audit=validate(proposal,idx,intent,list(idx.passages))
        self.assertFalse(valid)
        self.assertEqual(audit['rejections'],{'passage_entity_mismatch':1})
    def test_candidate_claim_rejects_feature_owned_by_another_entity(self):
        q='Compare open-source vector databases Qdrant, Milvus, and Weaviate.'
        text=('Qdrant, Milvus, and Weaviate ship replication and RBAC in their open-source builds, '
              "with the caveat that Milvus's high availability lives in the heavier distributed mode, not the standalone build.")
        idx=Index(q); idx.add([{'title':'Vector database comparison','url':'https://bench.example/vector-databases','text':text}],'web',q)
        p=next(iter(idx.passages.values())); intent=intent_from(q,None)
        proposal={'sections':[{'label':'Qdrant','category':'candidate','claims':[{'statement':'Qdrant high availability requires the heavier distributed mode, not the standalone build.','requirement_id':'R2','passage_ids':[p.id]}]},
                             {'label':'Milvus','category':'candidate','claims':[]},{'label':'Weaviate','category':'candidate','claims':[]}]}
        valid,_,audit=validate(proposal,idx,intent,list(idx.passages))
        self.assertFalse(valid)
        self.assertEqual(audit['rejections'],{'feature_owned_by_other_entity':1})
        proposal['sections'][0]['claims'][0]['statement']='High availability requires the heavier distributed mode.'
        valid,_,audit=validate(proposal,idx,intent,list(idx.passages))
        self.assertFalse(valid)
        self.assertEqual(audit['rejections'],{'claim_subject_missing':1})
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
        self.assertEqual(r.confidence,'medium')
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

    def test_recovery_queries_name_missing_criteria_and_batch_candidates(self):
        question='Find 5 Indian B2B SaaS startups in HR tech and summarize their positioning.'
        rows=[{'title':n+' HR platform','url':f'https://{n.lower()}.example/about',
               'text':f'{n} is an HR SaaS platform serving Indian employers. {n} offers HR workflow software.'}
              for n in ('Alpha','Beta','Gamma','Delta','Epsilon')]
        def web(q,t): return rows
        def model(stage,data,t):
            if stage=='intent': return {'facets':[],'queries':[question]}
            if stage=='review': return {'verdicts':[{'id':c['id'],'supported':True,'reason':'supported'} for c in data['claims']]}
            sections=[]
            for p in data['passages']:
                name=next((n for n in ('Alpha','Beta','Gamma','Delta','Epsilon') if p['text'].startswith(n)),None)
                if name and 'offers HR workflow' in p['text']:
                    sections.append({'label':name,'category':'candidate','claims':[{'statement':p['text'],'requirement_id':'R2','passage_ids':[p['id']]}]})
            return {'sections':sections}
        r=run_live(question,adapters={'web':web},model=model)
        self.assertEqual(r.metrics['search_calls'],4)
        recovery=[q for event in r.trace if event['stage']=='recovery' for q in event['queries']]
        self.assertEqual(len(recovery),2)
        self.assertTrue(all('India' in q and 'SaaS' in q for q in recovery))
        combined=' '.join(recovery)
        self.assertTrue(all(name in combined for name in ('Alpha','Beta','Gamma','Delta','Epsilon')))
        self.assertIn('Indian HR-tech B2B SaaS and startup eligibility',r.research_intent['facets'][0]['label'])

    def test_duplicate_candidate_requirement_claims_are_suppressed(self):
        def model(stage,data,t):
            if stage=='intent': return {}
            if stage=='review': return {'verdicts':[{'id':c['id'],'supported':True,'reason':'supported'} for c in data['claims']]}
            p=next(p for p in data['passages'] if p['text'].startswith('Alpha'))
            return {'sections':[{'label':'Alpha','category':'candidate','claims':[
                {'statement':'Alpha offers payroll automation for HR teams.','requirement_id':'R2','passage_ids':[p['id']]},
                {'statement':'Alpha provides payroll automation to HR departments.','requirement_id':'R2','passage_ids':[p['id']]}]}]}
        r=run_live(Q,adapters={'web':lambda q,t:ROWS},model=model)
        self.assertEqual(sum(len(s['claims']) for s in r.sections),1)
        self.assertTrue(any(e['stage']=='claim_selection' and e['removed_redundant_cells']==1 for e in r.trace))
    def test_model_failure_no_fabrication(self):
        def bad(stage,data,t): raise ToolError('http_429:rate_limit_exceeded')
        r=run_live(Q,adapters={'web':lambda q,t:ROWS},model=bad)
        self.assertFalse(r.sections); self.assertIn('http_429:rate_limit_exceeded',r.metrics['error_counts'])
        self.assertEqual(r.status,'partial')
        self.assertEqual(r.metrics['model_calls'],1)
        self.assertEqual(r.metrics['provider_attempts']['groq'],1)
        self.assertFalse(r.metrics['recovery_triggered'])
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

    def test_multi_source_claim_and_review(self):
        idx=Index(Q)
        idx.add(ROWS,'web',Q)
        ps=[p for p in idx.passages.values() if p.text.startswith('Alpha')]
        intent=intent_from(Q,None)
        proposal={'sections':[{'label':'Alpha','category':'candidate','claims':[{'statement':'Alpha is an Indian HR SaaS company offering payroll automation.','requirement_id':'R1','passage_ids':[p.id for p in ps]}]}]}
        claims,_,audit=validate(proposal,idx,intent,list(idx.passages))
        self.assertEqual(len(claims),1)
        self.assertEqual(len(claims[0]['passage_ids']),2)
        self.assertFalse(review(claims,{'verdicts':[{'id':claims[0]['id'],'supported':True,'reason':'not_entailed'}]})[0])

    def test_frozen_copy_mismatch_vs_passage_id(self):
        from veritas.synthesis import candidates
        idx=Index(Q); idx.add(ROWS,'web',Q)
        p=next(p for p in idx.passages.values() if 'Alpha offers' in p.text)
        evidence=list(idx.sources.values())
        old={'sections':[{'label':'Alpha','category':'candidate','claims':[{'statement':'Alpha offers payroll automation.','source_id':p.source_id,'quote':p.text.replace('automation','automation,')}]}]}
        new={'sections':[{'label':'Alpha','category':'candidate','claims':[{'statement':'Alpha offers payroll automation.','requirement_id':'R2','passage_ids':[p.id]}]}]}
        self.assertEqual(candidates(old,evidence,'list'),[])
        self.assertEqual(len(validate(new,idx,intent_from(Q,None),list(idx.passages))[0]),1)

    def test_log_redaction(self):
        import io, contextlib
        from veritas.telemetry import log_report
        r=run_live(Q,False,adapters={'web':lambda q,t:ROWS},include_diagnostics=True)
        buf=io.StringIO()
        with contextlib.redirect_stdout(buf): log_report(r)
        line=buf.getvalue()
        self.assertIn(r.metrics['run_id'],line)
        self.assertNotIn(Q,line)
        self.assertNotIn('https://',line)
        self.assertNotIn('Alpha offers',line)

    def test_shortlist_budget_and_alias_roundtrip(self):
        idx=Index(Q); idx.add(ROWS,'web',Q)
        ps=idx.shortlist(limit=2,char_budget=120)
        self.assertLessEqual(len(ps),2)
        self.assertLessEqual(sum(len(p.text) for p in ps),120)
        def model(stage,data,t):
            if stage=='intent': return {}
            if stage=='review':
                self.assertTrue(all(c['id'].startswith('C') for c in data['claims']))
                self.assertTrue(all(p['id'].startswith('P') for p in data['passages']))
                return {'verdicts':[{'id':c['id'],'supported':True,'reason':'supported'} for c in data['claims']]}
            p=next(p for p in data['passages'] if p['text'].startswith('Alpha'))
            self.assertRegex(p['id'],r'^P\d+$')
            return {'sections':[{'label':'Alpha','category':'candidate','claims':[{'statement':p['text'],'requirement_id':'R1','passage_ids':[p['id']]}]}]}
        r=run_live(Q,adapters={'web':lambda q,t:ROWS},model=model)
        self.assertTrue(r.sections)
        self.assertRegex(r.sections[0]['claims'][0]['passage_ids'][0],r'^S[0-9a-f]{12}-P[0-9a-f]{12}$')

    def test_quota_header_allowlist(self):
        from veritas.tools import rate_headers
        headers={'retry-after':'17','x-ratelimit-remaining-tokens':'123','x-ratelimit-reset-tokens':'12.3s','Authorization':'secret','x-ratelimit-limit-tokens':'invalid'}
        self.assertEqual(rate_headers(headers),{'retry-after':17,'x-ratelimit-remaining-tokens':123,'x-ratelimit-reset-tokens':'12.3s'})

    def test_open_list_ignores_category_names(self):
        q='Find 5 Indian B2B SaaS startups in HR tech and summarize their positioning.'
        intent=intent_from(q,{'named':['Indian B2B SaaS startups in HR tech','B2B SaaS startups']})
        self.assertEqual(intent['named'],[])
        claims=[{'label':'Alpha','category':'candidate','requirement_id':x['id']} for x in intent['facets']]
        self.assertEqual(coverage(intent,claims,['Alpha'])['covered'],1)

    def test_named_comparison_stays_named(self):
        intent=intent_from('Compare PostgreSQL versus MySQL',{'named':['PostgreSQL','MySQL']})
        self.assertEqual(intent['named'],['PostgreSQL','MySQL'])

    def test_qualification_cannot_be_inferred_from_title(self):
        idx=Index(Q); idx.add(ROWS,'web',Q)
        p=next(p for p in idx.passages.values() if 'Alpha offers' in p.text)
        proposal={'sections':[{'label':'Alpha','category':'candidate','claims':[{'statement':'Alpha is headquartered in India.','requirement_id':'R1','passage_ids':[p.id]}]}]}
        claims,_,audit=validate(proposal,idx,intent_from(Q,None),list(idx.passages))
        self.assertFalse(claims)
        self.assertEqual(audit['rejections'],{'unsupported_qualification':1})
