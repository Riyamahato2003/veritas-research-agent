"""Reproducible scenario evaluation. Results measure contract behavior, not factual accuracy."""
import json
from pathlib import Path
from veritas.agent import run
Q='Compare the top 3 open-source vector databases for a startup building RAG products.'
CASES=[('vector',Q,'none','Three candidates; ranking withheld',lambda r:all(n in ' '.join(s.title.lower() for s in r.sources_used) for n in ['qdrant','milvus','weaviate']) and r.status=='partial'),('hr','Find 5 Indian B2B SaaS startups in HR tech and summarize their positioning.','none','Web first; five records',lambda r:len(r.sources_used)==5 and r.plan[0].tool=='web'),('architecture','Research the pros and cons of using a multi-agent architecture for customer support automation.','none','At least two sources',lambda r:len(r.sources_used)>=2),('memory','Compare different approaches to adding memory in an AI support agent.','none','At least two sources',lambda r:len(r.sources_used)>=2),('unknown','Explain xenoflux quorbanic tessellation.','none','Abstain; replan once',lambda r:r.status=='insufficient' and any(t['stage']=='replan' for t in r.trace)),('timeout',Q,'timeout','Retry twice; partial',lambda r:r.status=='partial' and r.confidence=='low' and sum(t.get('tool')=='github' and t['status']=='error' for t in r.trace)==2),('outage',Q,'outage','Abstain without sources',lambda r:r.status=='insufficient' and not r.sources_used),('malformed',Q,'malformed','Reject malformed payload; continue',lambda r:bool(r.key_findings) and any(t.get('error')=='malformed_schema' for t in r.trace)),('injection',Q,'injection','Reject hostile result',lambda r:any('suspected_injection' in t.get('rejected',[]) for t in r.trace)),('noise',Q,'noise','Reject unrelated result',lambda r:any('weak_relevance' in t.get('rejected',[]) for t in r.trace)),('transient',Q,'transient','Recover on second attempt',lambda r:bool(r.key_findings) and r.metrics['tool_attempts']==6)]
def main():
    output=[]; root=Path(__file__).parent
    for name,q,fault,expected,check in CASES:
        r=run(q,fault=fault); passed=bool(check(r)); row={'id':name,'question':q,'fault':fault,'expected':expected,'pass':passed,'status':r.status,'confidence':r.confidence,'source_count':len(r.sources_used),'tool_attempts':r.metrics['tool_attempts'],'elapsed_ms':r.metrics['elapsed_ms']}; output.append(row)
        print(f'{"PASS" if passed else "FAIL"} {name:13} {r.status:12} sources={len(r.sources_used)} calls={r.metrics["tool_attempts"]}')
        if name in ('vector','hr','outage'): (root/'samples'/f'{name}.json').write_text(json.dumps(r.to_dict(),indent=2,ensure_ascii=False)+'\n')
    (root/'docs'/'evaluation-results.json').write_text(json.dumps(output,indent=2)+'\n')
    print(f'{sum(x["pass"] for x in output)}/{len(output)} scenario checks passed')
    raise SystemExit(0 if all(x['pass'] for x in output) else 1)
if __name__=='__main__': main()
