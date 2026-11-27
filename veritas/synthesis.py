"""Topic-independent structured synthesis with exact-span and separate model checks."""
import re
from .contracts import Finding
BAD=re.compile(r'https?://|ignore.{0,45}(instructions|prompt)|reveal.{0,30}(prompt|secret|key)|system prompt|developer message|execute.{0,20}(command|shell)',re.I)
NOISE=re.compile(r'\[\.\.\.\]|\]\(|###|\|\s*---|Recommended by LinkedIn',re.I)

def label_key(s):
    return re.sub(r'[^a-z0-9]','',s.lower())

def request_shape(question):
    count=re.search(r'\b(?:find|list|identify|name|compare|top)\s+(?:the\s+)?(\d{1,2})\b',question,re.I)
    if count: return 'list',min(8,max(1,int(count.group(1))))
    if re.search(r'\b(?:pros and cons|advantages and disadvantages|benefits and risks)\b',question,re.I): return 'tradeoffs',2
    if re.search(r'\b(?:compare|comparison|versus|tradeoffs?|approaches|alternatives)\b',question,re.I): return 'compare',2
    return 'research',1

def candidates(proposal,evidence,shape):
    if not isinstance(proposal,dict) or not isinstance(proposal.get('sections'),list): return []
    sources={e.id:e for e in evidence}; result=[]; seen=set()
    for section in proposal['sections'][:8]:
        if not isinstance(section,dict): continue
        label=section.get('label'); category=section.get('category')
        if not isinstance(label,str) or not 2<=len(label.strip())<=90 or not label_key(label) or BAD.search(label): continue
        if category not in ('candidate','benefit','risk','topic'): continue
        if shape=='list' and category!='candidate': continue
        if shape=='tradeoffs' and category not in ('benefit','risk'): continue
        if not isinstance(section.get('claims'),list): continue
        for item in section['claims'][:3]:
            if len(result)>=16: return result
            if not isinstance(item,dict): continue
            sid,quote,statement=item.get('source_id'),item.get('quote'),item.get('statement')
            if not all(isinstance(x,str) for x in (sid,quote,statement)): continue
            if sid not in sources or not 25<=len(quote)<=600 or quote not in sources[sid].text: continue
            if not 15<=len(statement.strip())<=400 or BAD.search(statement) or BAD.search(quote) or NOISE.search(quote): continue
            if category=='candidate' and label_key(label) not in label_key(quote): continue
            key=(label_key(label),statement.strip().lower())
            if key in seen: continue
            seen.add(key)
            result.append({'id':'C'+str(len(result)+1),'label':label.strip(),'category':category,
                           'statement':statement.strip(),'source_id':sid,'quote':quote})
    return result

def approved_sections(proposals,verdict):
    if not isinstance(verdict,dict) or not isinstance(verdict.get('verdicts'),list): return []
    votes={}
    for item in verdict['verdicts']:
        if not isinstance(item,dict) or not isinstance(item.get('id'),str): continue
        cid=item['id']
        votes[cid]=False if cid in votes else item.get('supported') is True
    sections={}
    for c in proposals:
        if votes.get(c['id']) is not True: continue
        key=(label_key(c['label']),c['category'])
        if key not in sections: sections[key]={'label':c['label'],'category':c['category'],'claims':[]}
        sections[key]['claims'].append({'statement':c['statement'],'source_ids':[c['source_id']],'quote':c['quote']})
    return list(sections.values())

def coverage(sections,shape,target):
    if shape=='tradeoffs': return len({s['category'] for s in sections}&{'benefit','risk'}),2
    if shape=='list': return len({label_key(s['label']) for s in sections if s['category']=='candidate'}),target
    return len({label_key(s['label']) for s in sections}),target

def evidence_findings(sections):
    out=[]; seen=set()
    for s in sections:
        for c in s['claims']:
            key=(c['source_ids'][0],c['quote'])
            if key not in seen:
                seen.add(key); out.append(Finding(c['quote'],c['source_ids']))
    return out
