"""Bounded single-agent execution and evidence gate."""
from dataclasses import replace
from concurrent.futures import ThreadPoolExecutor
from urllib.parse import urlsplit
from html import unescape
import re, time, os
from .contracts import Evidence, Finding, Report, Step, terms
from .planner import plan
from .tools import LIVE, FixtureTools, ToolError
from .model import select, verify
from .synthesis import request_shape, candidates as proposed_claims, approved_sections, coverage, evidence_findings

INJECTION=re.compile(r'ignore.{0,45}(instructions|prompt)|reveal.{0,30}(prompt|secret|key)|system prompt|developer message|execute.{0,20}(command|shell)',re.I)
TAG=re.compile(r'<[^>]+>')

def clean(x): return ' '.join(unescape(TAG.sub(' ',x)).split())

def normalize(rows, tool, question, search, mode='demo'):
    if not isinstance(rows,list): raise ToolError('malformed_schema')
    accepted=[]; rejected=[]
    qt=terms(question); st=terms(search)
    anchors = ({'memory'} if 'memory' in st else {'multi','multiagent'} if 'multi' in st else {'vector'} if 'vector' in st else {'hr','hrtech','hrms'} if 'hr' in st else set())
    for row in rows[:8]:
        if not isinstance(row,dict) or any(not isinstance(row.get(k),str) for k in ('title','url','text')):
            rejected.append('malformed_row'); continue
        title,text,url=clean(row['title'])[:180],clean(row['text'])[:1200],row['url'][:500]
        try:
            parsed=urlsplit(url); host=parsed.hostname
            if parsed.scheme!='https' or not host or parsed.username or parsed.password or parsed.port not in (None,443): raise ValueError()
            if tool=='github' and host!='github.com': raise ValueError()
            if tool=='wiki' and host!='en.wikipedia.org': raise ValueError()
        except ValueError:
            rejected.append('invalid_url'); continue
        if INJECTION.search(title+' '+text): rejected.append('suspected_injection'); continue
        overlap=terms(title+' '+text) & qt; search_overlap=terms(title+' '+text) & st
        if len(text)<25 or not overlap or not search_overlap or (anchors and not anchors & terms(title+' '+text)):
            rejected.append('weak_relevance'); continue
        if mode=='live' and len(qt)>=4:
            # Simple singular/plural normalization for the extra relevance gate.
            singular=lambda words:{w[:-1] if len(w)>3 and w.endswith('s') else w for w in words}
            if len(singular(qt)&singular(terms(title+' '+text)))<2:
                rejected.append('weak_relevance'); continue
        score=round(.7*len(overlap)/max(1,len(qt))+.3*len(search_overlap)/max(1,len(st)),3)
        accepted.append(Evidence(title,url,text,tool,score))
    return accepted,rejected

def verified_findings(proposal,evidence):
    if not isinstance(proposal,dict) or not isinstance(proposal.get('findings'),list): return []
    index={e.id:e for e in evidence}; found=[]; seen=set()
    for item in proposal['findings'][:8]:
        if not isinstance(item,dict): continue
        sid,quote=item.get('source_id'),item.get('quote')
        if not isinstance(sid,str) or not isinstance(quote,str) or sid not in index: continue
        if not 25<=len(quote)<=600 or quote not in index[sid].text or INJECTION.search(quote) or sid in seen: continue
        found.append(Finding(quote,[sid])); seen.add(sid)
    return found

def extractive(evidence):
    return [Finding(e.text[:600].rsplit(' ',1)[0] if len(e.text)>600 else e.text,[e.id]) for e in evidence[:6]]

def linked_analysis(proposal, findings, evidence):
    """Only publish verbatim evidence, never unchecked free-form claims."""
    if not isinstance(proposal,dict) or not isinstance(proposal.get('analysis'),list):
        return []
    quotes={f.source_ids[0]:f.statement for f in findings}
    result=[]
    for item in proposal['analysis'][:6]:
        if not isinstance(item,dict): continue
        statement,ids=item.get('statement'),item.get('source_ids')
        if not isinstance(statement,str) or not 25<=len(statement.strip())<=600 or INJECTION.search(statement): continue
        if not isinstance(ids,list) or len(ids)!=1 or not isinstance(ids[0],str) or ids[0] not in quotes: continue
        if statement.strip() not in quotes[ids[0]]: continue
        result.append(Finding(statement.strip(),ids))
    return result

def run(question, mode='demo', fault='none', use_model=True, adapters=None, model_select=select, model_verify=verify, include_diagnostics=False):
    if not isinstance(question,str) or not 3<=len(question.strip())<=600: raise ValueError('Question must be 3–600 characters.')
    if mode not in ('demo','live'): raise ValueError('Invalid mode')
    if fault!='none' and mode!='demo': raise ValueError('Fault injection is demo-only')
    question=question.strip(); start=time.monotonic(); trace=[]; limits=[]; calls=0; model_calls=0
    def error_category(exc):
        return exc.kind if isinstance(exc,ToolError) else 'internal_'+type(exc).__name__
    fixture=FixtureTools(fault) if mode=='demo' else None
    available={'wiki','github','web'} if mode=='demo' else {'wiki','github'}|({'web'} if os.getenv('TAVILY_API_KEY') else set())
    if adapters is not None: available=set(adapters)
    steps=plan(question,available,mode=mode)
    if not steps: raise ValueError('No research tools configured')
    trace.append({'stage':'plan','status':'ok','steps':len(steps)})
    def execute(step):
        events=[]; attempted=0
        for attempt in range(1,3):
            attempted+=1; t=time.monotonic()
            try:
                if adapters is not None: raw=adapters[step.tool](step.query,4)
                elif fixture: raw=fixture.search(step.tool,step.query,4)
                else: raw=LIVE[step.tool](step.query,4)
                accepted,rejected=normalize(raw,step.tool,question,step.query,mode)
                events.append({'stage':'retrieve','tool':step.tool,'query':step.query,'attempt':attempt,'status':'ok','raw_count':len(raw),'accepted':len(accepted),'rejected':rejected,'ms':round((time.monotonic()-t)*1000)})
                if include_diagnostics:
                    events[-1]['accepted_records']=[{'title':e.title,'host':urlsplit(e.url).hostname,'score':e.score,'chars':len(e.text)} for e in accepted]
                return accepted,events,attempted,None
            except ToolError as e:
                kind=e.kind; retry=e.retryable
            except (TypeError,KeyError,AttributeError,ValueError): kind='malformed_schema'; retry=False
            except Exception: kind='unexpected_tool_error'; retry=False
            events.append({'stage':'retrieve','tool':step.tool,'query':step.query,'attempt':attempt,'status':'error','error':kind,'ms':round((time.monotonic()-t)*1000)})
            if not retry or attempt==2: return [],events,attempted,kind
            time.sleep(.15)
        raise AssertionError('unreachable')
    def gather(batch):
        nonlocal calls
        with ThreadPoolExecutor(max_workers=3) as pool: results=list(pool.map(execute,batch))
        out=[]
        for step,(rows,events,n,error) in zip(batch,results):
            out.extend(rows); trace.extend(events); calls+=n
            if error: limits.append(f'{step.tool}: {error}; continued with remaining evidence.')
        return out
    candidates=gather(steps)
    shape,target=request_shape(question)
    requested=re.search(r'\b(?:find|list|compare|top)\s+(\d{1,2})\b',question,re.I)
    if mode=='demo': target=min(8,int(requested.group(1))) if requested else 2
    sparse=len({e.url for e in candidates})<max(2,target)
    if mode=='live' and shape in ('list','compare','tradeoffs') and 'web' in available:
        suffixes=('official websites documentation features eligibility','independent comparison practical tradeoffs limitations')
        batch=[Step('web',question[:300]+' '+s,'Complementary research: '+s) for s in suffixes]
        steps.extend(batch); trace.append({'stage':'replan','status':'triggered','reason':'Complementary evidence for requested coverage','steps':len(batch)})
        candidates+=gather(batch)
    elif sparse:
        untried=sorted(available-{s.tool for s in steps})
        reason='Recovery: broaden search after insufficient evidence'
        recovery=Step(untried[0] if untried else steps[0].tool,' '.join(sorted(terms(question)))[:180] or question[:180],reason)
        steps.append(recovery); trace.append({'stage':'replan','status':'triggered','reason':reason})
        candidates+=gather([recovery])
    unique={}
    for e in sorted(candidates,key=lambda x:-x.score):
        canonical=e.url.rstrip('/').split('#')[0].split('?')[0]
        if canonical not in unique: unique[canonical]=e
    ranked=list(unique.values())
    # Prefer diversity of evidence origins before filling remaining slots.
    first=[]; remaining=[]; hosts=set()
    for e in ranked:
        host=urlsplit(e.url).hostname
        if host not in hosts: first.append(e); hosts.add(host)
        else: remaining.append(e)
    evidence=[replace(e,id=f'S{i}') for i,e in enumerate((first+remaining)[:16 if mode=='live' else 8],1)]
    trace.append({'stage':'filter','status':'ok','candidates':len(candidates),'unique':len(unique),'retained':len(evidence)})
    if include_diagnostics:
        trace.append({'stage':'evidence_snapshot','status':'ok','records':[{'id':e.id,'title':e.title,'url':e.url,'tool':e.tool,'score':e.score,'text':e.text} for e in evidence]})
    findings=[]; analysis=[]; sections=[]; model_status='not_requested'; selected_count=0; supplemented=0
    proposed_count=0; accepted_count=0
    if evidence and use_model and mode=='live' and (os.getenv('GROQ_API_KEY') or model_select is not select):
        model_calls=1
        try:
            mt=time.monotonic()
            proposal=model_select(question,evidence,12)
            trace.append({'stage':'model_proposal','status':'ok','ms':round((time.monotonic()-mt)*1000),'meta':proposal.get('_provider_meta',{}) if isinstance(proposal,dict) else {}})
            claim_audit={}
            claims=proposed_claims(proposal,evidence,shape,claim_audit)
            trace.append({'stage':'claim_validation','status':'ok',**claim_audit,'passed':len(claims)})
            proposed_count=len(claims)
            if claims:
                model_calls+=1
                try:
                    vt=time.monotonic()
                    verdict=model_verify(question,claims,12)
                    sections=approved_sections(claims,verdict)
                    accepted_count=sum(len(s['claims']) for s in sections)
                    trace.append({'stage':'claim_review','status':'ok','proposed':proposed_count,'accepted':accepted_count,'rejected':proposed_count-accepted_count,'ms':round((time.monotonic()-vt)*1000),'meta':verdict.get('_provider_meta',{}) if isinstance(verdict,dict) else {}})
                except Exception as exc:
                    trace.append({'stage':'claim_review','status':'error','proposed':proposed_count,'accepted':0,'error':error_category(exc),'ms':round((time.monotonic()-vt)*1000)})
                    limits.append('Claim review unavailable; no paraphrased claims published.')
                if sections:
                    findings=evidence_findings(sections); selected_count=len(findings); model_status='reviewed'
                else:
                    model_status='rejected'; limits.append('No proposed claims passed review; using exact evidence only.')
            else:
                findings=verified_findings(proposal,evidence)
                selected_count=len(findings); model_status='verified' if findings else 'rejected'
                if not findings: limits.append('Model returned no verifiable spans; used extractive fallback.')
        except Exception as exc:
            trace.append({'stage':'model_proposal','status':'error','error':error_category(exc)})
            model_status='error'; limits.append('Model unavailable or malformed; used extractive fallback.')
    elif mode=='live' and use_model: model_status='no_key'; limits.append('GROQ_API_KEY absent; used extractive fallback.')
    if not findings: findings=extractive(evidence)
    covered,needed=coverage(sections,shape,target)
    used={sid for f in findings for sid in f.source_ids}; sources=[e for e in evidence if e.id in used]
    trace.append({'stage':'synthesis','status':model_status,'findings':len(findings),'model_selected':selected_count,'supplemented':supplemented,'analysis_items':len(analysis),'reviewed_claims':accepted_count,'coverage':covered,'target':needed})
    # Exact findings remain separate from source-linked model interpretations.
    confidence='low'; status='insufficient'
    if findings:
        status='partial' if len(sources)<2 or limits else 'complete'
        confidence='medium' if len(sources)>=2 and len({urlsplit(e.url).hostname for e in sources})>=2 and not limits else 'low'
    if mode=='demo': limits.append('Offline fixture corpus: authored example records, not live page content or current verification.')
    if findings: limits.append('Exact evidence matching is not semantic entailment, source accuracy, or exhaustive coverage; rankings and freshness are unverified.')
    if re.search(r'\b(top|best|latest|current|today|2026)\b',question,re.I):
        limits.append('Requested ranking or recency cannot be established from snippets alone.'); status='partial' if findings else status
    if mode=='live':
        if sections:
            limits.append('Claims passed exact-span validation and a separate Groq review; this is a model-based judgment, not independent proof of truth or entailment.')
        if covered<needed:
            limits.append(f'Question coverage incomplete: {covered} of {needed} requested sections/entities supported by reviewed claims.')
            status='partial' if findings else status; confidence='low'
        if shape=='list':
            limits.append('Distinct labels are a coverage heuristic; entity aliases and all eligibility criteria are not independently established.')
            status='partial' if findings else status
    if len(sources)<2: limits.append('Fewer than two usable sources; cannot establish a robust answer.')
    if mode=='demo' and requested and len(sources)<int(requested.group(1)):
        limits.append('Requested result count exceeds usable evidence count; coverage is incomplete.'); status='partial' if findings else status; confidence='low'
    if mode=='live' and 'web' not in available: limits.append('Broad web search disabled; configure TAVILY_API_KEY for general research.'); status='partial' if findings else status; confidence='low'
    if status=='partial' and len(sources)<2: confidence='low'
    if sections:
        short=' '.join(s['claims'][0]['statement']+' ['+s['claims'][0]['source_ids'][0]+']' for s in sections[:3])
    elif mode=='live':
        short='Insufficient reviewed evidence for a synthesized answer. See retrieved passages below.' if findings else 'Insufficient verified evidence to answer this question safely.'
    else:
        short=' '.join(f'{f.statement} [{f.source_ids[0]}]' for f in findings[:3]) if findings else 'Insufficient verified evidence to answer this question safely.'
    trace.append({'stage':'verify','status':'ok','linked_findings':len(findings),'confidence':confidence})
    return Report(question,short,findings,sources,confidence,limits,['Sources are untrusted retrieval records; confidence is a heuristic, not a calibrated probability.'],['Verify primary sources and compare evidence against the intended decision criteria.' if findings else 'Rephrase with specific entities or restore research providers, then retry.'],status,mode,steps,trace,{'tool_attempts':calls,'model_calls':model_calls,'elapsed_ms':round((time.monotonic()-start)*1000),'citation_integrity':all(s in {e.id for e in sources} for f in findings+analysis for s in f.source_ids) and all(sid in {e.id for e in sources} for sec in sections for claim in sec['claims'] for sid in claim['source_ids']),'evidence_retained':len(evidence),'model_selected':selected_count,'analysis_items':len(analysis),'distinct_candidates':sum(s['category']=='candidate' for s in sections),'coverage':covered,'coverage_target':needed,'claims_proposed':proposed_count,'claims_accepted':accepted_count,'claims_rejected':proposed_count-accepted_count},analysis=analysis,sections=sections)
