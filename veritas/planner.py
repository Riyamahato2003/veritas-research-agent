import re
from .contracts import Step, terms

def plan(question, available, mode='demo'):
    q=question.lower(); t=terms(q)
    technical=bool(t & {'database','databases','rag','framework','frameworks','architecture','memory','github','code','agent','agents','python','software','library','libraries'})
    business=bool(t & {'saas','startups','companies','market','pricing','hrtech','hr','business'}) and not bool(t & {'database','databases','rag'})
    # Search terms are compact, not full instructions; broadening is a separate bounded stage.
    if {'vector'}<=t and ('database' in t or 'databases' in t): search='vector database'
    elif 'memory' in t: search='agent memory'
    elif 'architecture' in t and ('agent' in t or 'multi' in t): search='multi agent architecture'
    elif business and ('hr' in t or 'hrtech' in t): search='Indian HR tech SaaS'
    else: search=' '.join(dict.fromkeys(w for w in re.findall(r'[\w-]+',question) if w.lower() in t))[:180] or question[:180]
    order=['web','wiki'] if business else (['github','web','wiki'] if technical else ['wiki','web'])
    reason={'wiki':'Background and conceptual context','github':'Public implementation and repository descriptions','web':'Broad discovery and official product positioning'}
    return [Step(tool,question[:400] if mode=='live' and tool=='web' else search,reason[tool]) for tool in order if tool in available][:3]
