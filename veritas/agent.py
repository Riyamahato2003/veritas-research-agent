"""Bounded single-agent execution and evidence gate."""
from dataclasses import replace
from concurrent.futures import ThreadPoolExecutor
from urllib.parse import urlsplit
from html import unescape
import re, time, os
from .contracts import Evidence, Finding, Report, Step, terms
from .planner import plan
from .tools import LIVE, FixtureTools, ToolError
from .model import select
from .comparison import vector_comparison, candidate_hints, cards, card_findings

INJECTION=re.compile(r'ignore.{0,45}(instructions|prompt)|reveal.{0,30}(prompt|secret|key)|system prompt|developer message|execute.{0,20}(command|shell)',re.I)
TAG=re.compile(r'<[^>]+>')

def clean(x): return ' '.join(unescape(TAG.sub(' ',x)).split())

def normalize(rows, tool, question, search):
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

def run(question, mode='demo', fault='none', use_model=True, adapters=None, model_select=select):
    if not isinstance(question,str) or not 3<=len(question.strip())<=600: raise ValueError('Question must be 3–600 characters.')
    if mode not in ('demo','live'): raise ValueError('Invalid mode')
    if fault!='none' and mode!='demo': raise ValueError('Fault injection is demo-only')
    question=question.strip(); start=time.monotonic(); trace=[]; limits=[]; calls=0; model_calls=0
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
                accepted,rejected=normalize(raw,step.tool,question,step.query)
                events.append({'stage':'retrieve','tool':step.tool,'attempt':attempt,'status':'ok','accepted':len(accepted),'rejected':rejected,'ms':round((time.monotonic()-t)*1000)})
                return accepted,events,attempted,None
            except ToolError as e:
                kind=e.kind; retry=e.retryable
            except (TypeError,KeyError,AttributeError,ValueError): kind='malformed_schema'; retry=False
            except Exception: kind='unexpected_tool_error'; retry=False
            events.append({'stage':'retrieve','tool':step.tool,'attempt':attempt,'status':'error','error':kind,'ms':round((time.monotonic()-t)*1000)})
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
    # One conditional recovery step; no open-ended autonomous loop.
    requested = re.search(r'\b(?:find|list|compare|top)\s+(\d{1,2})\b',question,re.I)
    target = min(8,int(requested.group(1))) if requested else 2
    comparison=bool(re.search(r'\b(compare|comparison|versus|tradeoffs?|pros and cons)\b',question,re.I))
    sparse=len({e.url for e in candidates})<max(2,target)
    # A comparison needs more than a count of URLs. Spend at most one extra
    # basic web query for complementary evidence, retaining the original budget.
    comparative_followup=mode=='live' and comparison and 'web' in available
    entity_comparison=mode=='live' and vector_comparison(question)
    if entity_comparison and 'web' in available:
        # One bounded parallel follow-up phase, up to three candidate-specific queries.
        batch=[Step('web',name+' vector database official documentation deployment filtering scalability license RAG', 'Candidate-specific documentation: '+name) for name in candidate_hints(question)[:3]]
        steps.extend(batch); trace.append({'stage':'replan','status':'triggered','reason':'Candidate-specific evidence coverage','candidates':candidate_hints(question)[:3]})
        candidates+=gather(batch)
    elif sparse or comparative_followup:
        untried=sorted(available-{s.tool for s in steps})
        if comparative_followup:
            reason='Comparison-focused follow-up for feature and tradeoff evidence'
            recovery=Step('web',question[:330]+' comparison features tradeoffs practical limitations',reason)
        else:
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
    evidence=[replace(e,id=f'S{i}') for i,e in enumerate((first+remaining)[:16 if entity_comparison else 8],1)]
    trace.append({'stage':'filter','status':'ok','candidates':len(candidates),'unique':len(unique),'retained':len(evidence)})
    findings=[]; analysis=[]; comparison_rows=[]; model_status='not_requested'; selected_count=0; supplemented=0
    if evidence and use_model and mode=='live' and (os.getenv('GROQ_API_KEY') or model_select is not select):
        model_calls=1
        try:
            proposal=model_select(question,evidence,12); findings=verified_findings(proposal,evidence)
            selected_count=len(findings)
            analysis=linked_analysis(proposal,findings,evidence)
            model_status='verified' if findings else 'rejected'
            if not findings: limits.append('Model returned no verifiable spans; used extractive fallback.')
        except Exception:
            model_status='error'; limits.append('Model unavailable or malformed; used extractive fallback.')
    elif mode=='live' and use_model: model_status='no_key'; limits.append('GROQ_API_KEY absent; used extractive fallback.')
    if entity_comparison:
        comparison_rows=cards(question,evidence)
        # Candidate cards are built from all retained evidence, not the model's selection.
        if comparison_rows:
            findings=card_findings(comparison_rows)
            analysis=[]
            model_status='entity_evidence'
        else:
            findings=[]; analysis=[]
    if not findings: findings=extractive(evidence)
    elif mode=='live' and not entity_comparison:
        # A nonempty model response is not necessarily a sufficiently complete
        # response. Preserve additional usable evidence without inventing facts.
        desired=min(len(evidence),8,max(target,5 if comparison else 2))
        used_ids={sid for f in findings for sid in f.source_ids}
        extra=extractive([e for e in evidence if e.id not in used_ids])[:max(0,desired-len(findings))]
        findings.extend(extra); supplemented=len(extra)
        if supplemented: limits.append('Model selected limited evidence; additional exact passages are included. Distinct entity coverage is not guaranteed.')
    used={sid for f in findings for sid in f.source_ids}; sources=[e for e in evidence if e.id in used]
    trace.append({'stage':'synthesis','status':model_status,'findings':len(findings),'model_selected':selected_count,'supplemented':supplemented,'analysis_items':len(analysis)})
    # Exact findings remain separate from source-linked model interpretations.
    confidence='low'; status='insufficient'
    if findings:
        status='partial' if len(sources)<2 or limits else 'complete'
        confidence='medium' if len(sources)>=2 and len({urlsplit(e.url).hostname for e in sources})>=2 and not limits else 'low'
    if mode=='demo': limits.append('Offline fixture corpus: authored example records, not live page content or current verification.')
    if findings: limits.append('Exact evidence matching is not semantic entailment, source accuracy, or exhaustive coverage; rankings and freshness are unverified.')
    if re.search(r'\b(top|best|latest|current|today|2026)\b',question,re.I):
        limits.append('Requested ranking or recency cannot be established from snippets alone.'); status='partial' if findings else status
    if mode=='live' and comparison and not comparison_rows and len(analysis)<2 and findings:
        limits.append('Comparative analysis remains incomplete; exact passages alone do not establish tradeoffs.'); status='partial'; confidence='low'
    if analysis: limits.append('Analysis excerpts are verbatim subsets of checked evidence; source accuracy and entailment remain unverified.')
    if entity_comparison:
        limits.append('Candidate labels are search hints, not a verified ranking. Comparison cells are exact retrieved passages; missing criteria are not inferred.')
        if len(comparison_rows)<target or any(len(row['evidence'])<2 for row in comparison_rows):
            limits.append('Distinct candidate or criterion coverage is incomplete.'); status='partial' if findings else status; confidence='low'
    if len(sources)<2: limits.append('Fewer than two usable sources; cannot establish a robust answer.')
    if requested and len(sources)<int(requested.group(1)):
        limits.append('Requested result count exceeds usable evidence count; coverage is incomplete.'); status='partial' if findings else status; confidence='low'
    if mode=='live' and 'web' not in available: limits.append('Broad web search disabled; configure TAVILY_API_KEY for general research.'); status='partial' if findings else status; confidence='low'
    if status=='partial' and len(sources)<2: confidence='low'
    if comparison_rows:
        short='Evidence found for '+', '.join(row['entity'] for row in comparison_rows)+'. These are candidates, not a verified ranking. See the cited comparison by criterion below.'
    else:
        short=' '.join(f'{f.statement} [{f.source_ids[0]}]' for f in findings[:3]) if findings else 'Insufficient verified evidence to answer this question safely.'
    trace.append({'stage':'verify','status':'ok','linked_findings':len(findings),'confidence':confidence})
    return Report(question,short,findings,sources,confidence,limits,['Sources are untrusted retrieval records; confidence is a heuristic, not a calibrated probability.'],['Verify primary sources and compare evidence against the intended decision criteria.' if findings else 'Rephrase with specific entities or restore research providers, then retry.'],status,mode,steps,trace,{'tool_attempts':calls,'model_calls':model_calls,'elapsed_ms':round((time.monotonic()-start)*1000),'citation_integrity':all(s in {e.id for e in sources} for f in findings+analysis for s in f.source_ids),'evidence_retained':len(evidence),'model_selected':selected_count,'analysis_items':len(analysis),'distinct_candidates':len(comparison_rows)},analysis=analysis,comparison=comparison_rows)
