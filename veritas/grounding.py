"""Stable source/passages, requirement-level coverage and fail-closed claim review."""
from dataclasses import dataclass, asdict
from hashlib import sha256
from urllib.parse import urlsplit, urlunsplit
from html import unescape
import ipaddress, re
from .contracts import Evidence, terms
from .synthesis import request_shape

BAD=re.compile(r'ignore.{0,45}(instructions|prompt)|reveal.{0,30}(prompt|secret|key)|system prompt|developer message|execute.{0,20}(command|shell)',re.I)
NOISE=re.compile(r'^\s*(?:cookie|privacy policy|all rights reserved|sign up|log in|recommended by linkedin|advertisement|share this|view profile)\b',re.I)
NUMBER=re.compile(r'\b\d[\d,.]*(?:\s?%)?')
def key(s): return re.sub(r'[^a-z0-9]','',s.lower())
def digest(s): return sha256(s.encode()).hexdigest()[:12]
def tokens(s): return {w[:-1] if w.endswith('s') and len(w)>4 else w for w in terms(s)}
def public_url(url):
    try:
        u=urlsplit(url)
        h=u.hostname or ''
        if u.scheme!='https' or not h or '.' not in h or u.username or u.password or u.port not in (None,443): return None
        if h.endswith(('.local','.internal','.localhost','.test','.invalid')): return None
        try:
            if not ipaddress.ip_address(h).is_global: return None
        except ValueError: pass
        return urlunsplit(('https',h,u.path or '/',u.query,''))
    except (ValueError,TypeError): return None

def clean(text):
    text=unescape(re.sub(r'<[^>]+>',' ',text))
    text=re.sub(r'!?\[([^\]\n]+)\]\([^)]+\)',r'\1',text)
    text=re.sub(r'(?m)^\s*#{1,6}\s*','',text)
    text=re.sub(r'\s+\[(?:\.\.\.|…)\]\s+','\n',text)
    return '\n'.join(' '.join(line.split()) for line in text.splitlines() if line.strip())

def fallback_intent(question):
    shape,n=request_shape(question)
    if shape=='list':
        facets=['Eligibility under the requested constraints','Positioning and relevant capabilities']
        if re.search(r'\bcompare\b',question,re.I): facets.append('Practical tradeoff or limitation')
    elif shape=='tradeoffs': facets=['Benefits','Risks and drawbacks']
    elif shape=='compare': facets=['Approach and capabilities','Practical tradeoff or limitation']
    else: facets=['Direct answer and supporting context']
    return {'shape':shape,'target':n,'facets':[{'id':'R'+str(i+1),'label':x} for i,x in enumerate(facets)],'queries':[question[:400]],'named':[]}

def intent_from(question,proposal):
    intent=fallback_intent(question)
    if not isinstance(proposal,dict): return intent
    raw=proposal.get('facets')
    if isinstance(raw,list):
        labels=[x.strip() for x in raw[:4] if isinstance(x,str) and 4<=len(x.strip())<=100 and not BAD.search(x) and 'http' not in x.lower()]
        # Keep fixed minimum criteria for explicit lists and both sides of tradeoffs.
        if intent['shape']=='list':
            extra=labels[:2]
            labels=[x['label'] for x in intent['facets']]+extra
        elif intent['shape']=='tradeoffs': labels=[x['label'] for x in intent['facets']]
        elif intent['shape']=='compare': labels=labels if len(labels)>=2 else [x['label'] for x in intent['facets']]
        else: labels=labels or [x['label'] for x in intent['facets']]
        labels=list(dict.fromkeys(labels))[:4]
        intent['facets']=[{'id':'R'+str(i+1),'label':x} for i,x in enumerate(labels)]
    queries=proposal.get('queries')
    if isinstance(queries,list):
        qt=tokens(question)
        good=[q.strip()[:400] for q in queries[:4] if isinstance(q,str) and 5<=len(q.strip())<=400 and not BAD.search(q) and not re.search(r'https?://',q) and qt & tokens(q)]
        intent['queries']=list(dict.fromkeys([question[:400]]+good))[:3]
    names=proposal.get('named')
    if isinstance(names,list):
        intent['named']=list(dict.fromkeys(n.strip() for n in names[:8] if isinstance(n,str) and 2<=len(n.strip())<=80 and key(n) and key(n) in key(question) and not BAD.search(n)))
    return intent

@dataclass(frozen=True)
class Passage:
    id: str
    source_id: str
    text: str
    score: float
    origin: str
    def to_dict(self): return asdict(self)

def source_quality(url,title):
    """Transparent heuristic, not a proof that a source is authoritative."""
    u=urlsplit(url); host=u.hostname or ''; path=u.path.lower(); t=title.lower()
    if host.endswith(('.gov','.edu','.ac.uk','.gov.in')) or host=='arxiv.org': return .16
    if host.startswith(('docs.','learn.','developer.','developers.')) or '/docs' in path or '/documentation' in path: return .14
    if host=='github.com': return .06
    if 'linkedin.com' in host or 'dev.to'==host or 'reddit.com' in host: return -.15
    if re.search(r'\b(?:jobs|hiring|agencies|agenc(?:y|ies)|companies to work for|top \d+ companies)\b',t): return -.2
    if 'wikipedia.org' in host: return -.04
    return 0.0

class Index:
    def __init__(self,question):
        self.question=question; self.sources={}; self.passages={}; self.body_seen=set()
    def add(self,rows,tool,query,origin='snippet'):
        counts={}; accepted=[]
        def reject(reason): counts[reason]=counts.get(reason,0)+1
        if not isinstance(rows,list): raise ValueError('rows_not_list')
        qt=tokens(self.question); st=tokens(query)
        for row in rows[:10]:
            if not isinstance(row,dict) or not all(isinstance(row.get(k),str) for k in ('title','url','text')):
                reject('malformed_row'); continue
            url=public_url(row['url'])
            if not url: reject('invalid_url'); continue
            if tool=='github' and urlsplit(url).hostname!='github.com': reject('invalid_provider_host'); continue
            if tool=='wiki' and urlsplit(url).hostname!='en.wikipedia.org': reject('invalid_provider_host'); continue
            title=clean(row['title'])[:180]; body=clean(row['text'])[:11000 if origin=='extract' else 4000]
            if len(body)<25 or BAD.search(title+' '+body): reject('unsafe_or_short'); continue
            overlap=qt & tokens(title+' '+body); qo=st & tokens(title+' '+body)
            if not overlap or not qo or (len(qt)>=4 and len(overlap)<2 and origin!='extract'):
                reject('weak_relevance'); continue
            if re.search(r'\b(?:agencies|companies to work for|job openings)\b',title,re.I) and not re.search(r'\b(?:agencies|jobs|work for|careers)\b',self.question,re.I):
                reject('off_intent_title'); continue
            sid='S'+digest(url)
            bodykey=(sid,digest(body))
            if bodykey in self.body_seen: reject('duplicate_body'); continue
            self.body_seen.add(bodykey)
            quality=source_quality(url,title)
            provider=row.get('provider_score')
            provider=float(provider) if isinstance(provider,(float,int)) and not isinstance(provider,bool) and 0<=provider<=1 else .4
            score=round(.50*len(overlap)/max(1,len(qt))+.20*len(qo)/max(1,len(st))+.30*provider+quality,3)
            prev=self.sources.get(sid)
            full=(prev.text+'\n'+body) if prev else body
            if len(full)>23000: reject('source_size_budget'); continue
            self.sources[sid]=Evidence(title or (prev.title if prev else urlsplit(url).hostname),url,full,tool,max(score,prev.score if prev else score),sid)
            # Sentence-sized chunks; do not join across provider omission boundaries.
            chunks=[]
            for line in body.splitlines():
                if NOISE.search(line): continue
                # Preserve complete sentences and individual table cells where possible.
                parts=re.split(r'(?<=[.!?])\s+(?=[A-Z0-9])',line)
                for part in parts:
                    part=part.strip()
                    if not 25<=len(part)<=900 or BAD.search(part) or NOISE.search(part): continue
                    # Long sentences are accepted only if their boundaries remain intact.
                    if len(part)>600: continue
                    match=tokens(part)&(qt|st)
                    local=score+.08*len(match)/max(1,len(qt|st))
                    chunks.append((local,part))
            if not chunks and 25<=len(body)<=600 and not NOISE.search(body): chunks=[(score,body)]
            for local,part in sorted(chunks,key=lambda x:-x[0])[:18 if origin=='extract' else 8]:
                pid=sid+'-P'+digest(part)
                self.passages.setdefault(pid,Passage(pid,sid,part,round(local,3),origin))
            accepted.append({'source_id':sid,'title':title,'score':score,'provider_score':provider,'chars':len(body),'origin':origin})
        return accepted,counts
    def shortlist(self,limit=52,preferred=()):
        by_source={}
        for p in sorted(self.passages.values(),key=lambda p:(-p.score,p.id)):
            by_source.setdefault(p.source_id,[]).append(p)
        preferred=set(preferred)
        chosen=[p for p in self.passages.values() if p.id in preferred][:limit]
        seen={p.id for p in chosen}
        for i in range(8):
            for ps in by_source.values():
                if i<len(ps) and ps[i].id not in seen and len(chosen)<limit:
                    chosen.append(ps[i]); seen.add(ps[i].id)
        return chosen
    def model_records(self,passages):
        return [{'id':p.id,'text':p.text,'source_title':self.sources[p.source_id].title,'host':urlsplit(self.sources[p.source_id].url).hostname,'origin':p.origin} for p in passages]

def validate(proposal,index,intent,allowed):
    audit={'raw_sections':0,'raw_claims':0,'rejections':{}}; claims=[]; labels=[]; seen=set()
    def reject(r): audit['rejections'][r]=audit['rejections'].get(r,0)+1
    if not isinstance(proposal,dict) or not isinstance(proposal.get('sections'),list):
        reject('invalid_schema'); return claims,labels,audit
    facets={x['id'] for x in intent['facets']}; allowed=set(allowed)
    audit['raw_sections']=len(proposal['sections'])
    for sec in proposal['sections'][:10]:
        if not isinstance(sec,dict): reject('section_schema'); continue
        label=sec.get('label'); cat=sec.get('category')
        if not isinstance(label,str) or not 2<=len(label.strip())<=90 or not key(label) or BAD.search(label) or 'http' in label.lower(): reject('label'); continue
        if cat not in ('candidate','benefit','risk','topic'): reject('category'); continue
        if intent['shape'] in ('list','compare') and cat!='candidate': reject('wrong_category'); continue
        if intent['shape']=='tradeoffs' and cat not in ('benefit','risk'): reject('wrong_category'); continue
        label=label.strip(); labels.append(label)
        if not isinstance(sec.get('claims'),list): reject('claims_schema'); continue
        for c in sec['claims'][:6]:
            audit['raw_claims']+=1
            if len(claims)>=24: reject('claim_budget'); continue
            if not isinstance(c,dict): reject('claim_schema'); continue
            statement,rid,pids=c.get('statement'),c.get('requirement_id'),c.get('passage_ids')
            if not isinstance(statement,str) or not 12<=len(statement.strip())<=450 or BAD.search(statement) or re.search(r'https?://',statement): reject('statement'); continue
            if not isinstance(rid,str) or rid not in facets: reject('unknown_requirement'); continue
            if not isinstance(pids,list) or not 1<=len(pids)<=3 or any(not isinstance(p,str) or p not in allowed or p not in index.passages for p in pids): reject('unknown_passage_id'); continue
            pids=list(dict.fromkeys(pids)); passages=[index.passages[p] for p in pids]
            combined=' '.join(p.text for p in passages)
            titles=' '.join(index.sources[p.source_id].title for p in passages)
            if cat=='candidate' and key(label) not in key(combined+' '+titles): reject('entity_not_in_evidence'); continue
            if intent['shape']=='tradeoffs' and ((cat=='benefit' and rid!='R1') or (cat=='risk' and rid!='R2')): reject('wrong_tradeoff_requirement'); continue
            # A numeric claim must use numbers present in evidence, even before semantic review.
            if not set(NUMBER.findall(statement))<=set(NUMBER.findall(combined)): reject('unsupported_number'); continue
            ident=(key(label),rid,key(statement))
            if ident in seen: reject('duplicate_claim'); continue
            seen.add(ident)
            claims.append({'id':'C'+digest(label+'|'+rid+'|'+statement+'|'+','.join(pids)),'label':label,'category':cat,'requirement_id':rid,'statement':statement.strip(),'passage_ids':pids})
    audit['passed']=len(claims)
    return claims,list(dict.fromkeys(labels)),audit

def reviewer_payload(claims,index):
    return [{**c,'evidence':[{'id':pid,'text':index.passages[pid].text,'source_title':index.sources[index.passages[pid].source_id].title,'host':urlsplit(index.sources[index.passages[pid].source_id].url).hostname} for pid in c['passage_ids']]} for c in claims]

REVIEW_REASONS={'supported','irrelevant','wrong_entity','not_entailed','missing_qualification','unverified_eligibility','unsupported_number','wrong_requirement','uncertain','malformed'}
def review(claims,verdict):
    votes={}; counts={}; accepted=[]
    raw=verdict.get('verdicts') if isinstance(verdict,dict) else None
    if isinstance(raw,list):
        for v in raw[:48]:
            if not isinstance(v,dict) or not isinstance(v.get('id'),str): continue
            cid=v['id']; reason=v.get('reason')
            reason=reason if isinstance(reason,str) and reason in REVIEW_REASONS else 'uncertain'
            votes[cid]=(False,'duplicate_verdict') if cid in votes else (v.get('supported') is True and reason=='supported',reason)
    for c in claims:
        ok,reason=votes.get(c['id'],(False,'missing_verdict'))
        if ok: accepted.append(c)
        else: counts[reason]=counts.get(reason,0)+1
    return accepted,counts

def coverage(intent,claims,discovered):
    ids=[x['id'] for x in intent['facets']]
    shape=intent['shape']; target=intent['target']
    grouped={}
    for c in claims:
        k=key(c['label']); entry=grouped.setdefault(k,{'label':c['label'],'category':c['category'],'covered':set()})
        entry['covered'].add(c['requirement_id'])
    if shape in ('list','compare'):
        # Named alternatives are required, not interchangeable with other labels.
        wanted=intent.get('named') or []
        if wanted: target=max(target,len(wanted))
        for name in list(wanted)+list(discovered):
            if key(name): grouped.setdefault(key(name),{'label':name,'category':'candidate','covered':set()})
        rows=[{'label':x['label'],'covered':sorted(x['covered']),'missing':[r for r in ids if r not in x['covered']]} for x in grouped.values()]
        qualified=[r for r in rows if not r['missing'] and (not wanted or key(r['label']) in {key(n) for n in wanted})]
        covered=len(qualified)
        return {'target':target,'covered':covered,'rows':rows,'missing':[{'label':r['label'],'requirements':r['missing']} for r in rows if r['missing']][:6],
                'need_more_candidates':max(0,target-len(rows)),'complete':covered>=target}
    # For conceptual research and tradeoffs, check each requirement explicitly.
    covered_ids={c['requirement_id'] for c in claims if shape!='tradeoffs' or (c['requirement_id']=='R1' and c['category']=='benefit') or (c['requirement_id']=='R2' and c['category']=='risk')}
    missing=[r for r in ids if r not in covered_ids]
    return {'target':len(ids),'covered':len(covered_ids),'rows':[{'label':x['label'],'covered':[x['id']] if x['id'] in covered_ids else [],'missing':[x['id']] if x['id'] in missing else []} for x in intent['facets']],
            'missing':[{'label':'','requirements':missing}] if missing else [],'need_more_candidates':0,'complete':not missing}

def sections_from(claims,index,intent):
    groups={}; labels={x['id']:x['label'] for x in intent['facets']}
    for c in claims:
        k=(key(c['label']),c['category'])
        s=groups.setdefault(k,{'label':c['label'],'category':c['category'],'claims':[]})
        ps=[index.passages[p] for p in c['passage_ids']]
        s['claims'].append({'statement':c['statement'],'requirement_id':c['requirement_id'],'requirement':labels[c['requirement_id']],
                            'passage_ids':c['passage_ids'],'source_ids':list(dict.fromkeys(p.source_id for p in ps)),
                            'quote':'\n\n'.join(p.text for p in ps),
                            'passages':[p.to_dict() for p in ps]})
    return list(groups.values())
