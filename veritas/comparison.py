"""Evidence-only comparison cards; known names are retrieval hints, never facts."""
import re
from urllib.parse import urlsplit
from .contracts import Finding, terms

VECTOR_HINTS = {
    'Qdrant': (r'\bqdrant\b', ('qdrant.tech','qdrant.com'), 'qdrant/qdrant'),
    'Milvus': (r'\bmilvus\b', ('milvus.io','zilliz.com'), 'milvus-io/milvus'),
    'Chroma': (r'\bchroma(?:db)?\b', ('trychroma.com','chromadb.dev'), 'chroma-core/chroma'),
    'Weaviate': (r'\bweaviate\b', ('weaviate.io',), 'weaviate/weaviate'),
    'LanceDB': (r'\blancedb\b', ('lancedb.com',), 'lancedb/lancedb'),
    'pgvector': (r'\bpgvector\b', (), 'pgvector/pgvector'),
}
FACETS = {
    'Deployment': r'\b(?:deploy\w*|self.host\w*|local|distributed|cluster\w*|docker|kubernetes|embedded|serverless)\b',
    'Retrieval and filtering': r'\b(?:filter\w*|hybrid|keyword|sparse|dense|similarity|metadata|payload|full.text)\b',
    'Scaling and performance': r'\b(?:scal\w*|throughput|latency|shard\w*|replica\w*|million|billion|performance)\b',
    'Licensing and cost': r'\b(?:open.source|license|licence|pricing|cost|free|apache|mit)\b',
}

def vector_comparison(question):
    t=terms(question)
    return 'vector' in t and bool(t & {'database','databases','store','stores'}) and bool(re.search(r'\b(compare|comparison|top|best|versus|vs|tradeoffs?)\b',question,re.I))

def candidate_hints(question):
    named=[n for n,(p,_,_) in VECTOR_HINTS.items() if re.search(p,question,re.I)]
    # An explicit comparison of named candidates is not silently broadened.
    return named[:5] if named else list(VECTOR_HINTS)[:3]

def official(e, name):
    _,domains,repo=VECTOR_HINTS[name]
    host=urlsplit(e.url).hostname or ''
    return any(host==d or host.endswith('.'+d) for d in domains) or (
        host=='github.com' and urlsplit(e.url).path.lower().strip('/').startswith(repo.lower()+'/')
        or host=='github.com' and urlsplit(e.url).path.lower().strip('/')==repo.lower()
    )

def names_in(text):
    return [n for n,(p,_,_) in VECTOR_HINTS.items() if re.search(p,text,re.I)]

def snippets(e, name):
    """A span must name only the subject, or come from its project-specific official source."""
    own=official(e,name)
    # Avoid cross-entity tables, omitted sections, and generic comparison fragments.
    for part in re.split(r'(?<=[.!?])\s+|\s+\[\.\.\.\]\s+|\s+\|\s+',e.text):
        quote=part.strip()
        if not 25<=len(quote)<=600 or '[...]' in quote or '|' in quote:
            continue
        mentions=names_in(quote)
        if any(n!=name for n in mentions) or (name not in mentions and not own):
            continue
        yield quote

def cards(question, evidence):
    result=[]
    for name in candidate_hints(question):
        choices=[]
        for e in evidence:
            for quote in snippets(e,name):
                for facet,pattern in FACETS.items():
                    if re.search(pattern,quote,re.I):
                        choices.append((not official(e,name),-e.score,facet,e.id,quote))
        chosen={}
        for _,_,facet,sid,quote in sorted(choices):
            if facet not in chosen:
                chosen[facet]={'facet':facet,'source_id':sid,'quote':quote}
        if chosen:
            result.append({'entity':name,'evidence':list(chosen.values())})
    return result

def card_findings(rows):
    """Only exact passages, deduplicated by source and span."""
    seen=set(); result=[]
    for row in rows:
        for item in row['evidence']:
            key=(item['source_id'],item['quote'])
            if key not in seen:
                seen.add(key)
                result.append(Finding(item['quote'],[item['source_id']]))
    return result
