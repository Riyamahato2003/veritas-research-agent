import argparse,json,sys
from pathlib import Path
from .agent import run

def main():
    p=argparse.ArgumentParser(description='Veritas evidence-first research agent')
    p.add_argument('question'); p.add_argument('--mode',choices=['demo','live'],default='demo'); p.add_argument('--fault',choices=['none','timeout','transient','outage','malformed','injection','noise'],default='none'); p.add_argument('--no-model',action='store_true'); p.add_argument('--json',action='store_true'); p.add_argument('--output',type=Path)
    a=p.parse_args()
    try: r=run(a.question,a.mode,a.fault,not a.no_model)
    except ValueError as e: p.error(str(e))
    raw=json.dumps(r.to_dict(),indent=2,ensure_ascii=False)
    if a.output: a.output.write_text(raw+'\n',encoding='utf-8')
    if a.json: print(raw); return
    print(f'VERITAS | {r.mode.upper()} | {r.status.upper()} | confidence: {r.confidence}\nQUESTION: {r.question}\n\nPLAN')
    for s in r.plan: print(f'  {s.tool}: {s.query} — {s.reason}')
    print('\nSHORT ANSWER\n'+r.short_answer+'\n\nKEY FINDINGS')
    for f in r.key_findings: print(f'  [{", ".join(f.source_ids)}] {f.statement}')
    if r.analysis:
        print('\nAI ANALYSIS (source-linked interpretation, not independently verified)')
        for f in r.analysis: print(f'  [{", ".join(f.source_ids)}] {f.statement}')
    print('\nSOURCES'); [print(f'  [{s.id}] {s.title}: {s.url}') for s in r.sources_used]
    print('\nLIMITATIONS / ASSUMPTIONS'); [print('  - '+x) for x in r.limitations+r.assumptions]
    print('\nNEXT STEPS'); [print('  - '+x) for x in r.suggested_next_steps]
    print('\nTRACE'); [print('  '+json.dumps(e)) for e in r.trace]
    print('\nMETRICS '+json.dumps(r.metrics))
if __name__=='__main__': main()
