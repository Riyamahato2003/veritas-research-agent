"""Compare bounded orchestration with single-tool retrieval, not a factual benchmark."""
import json
from veritas.agent import run,normalize
from veritas.tools import FixtureTools,ToolError
from evaluate import Q

def main():
    rows=[]
    for fault in ('none','timeout','outage'):
        tool=FixtureTools(fault)
        try: baseline,_=normalize(tool.search('github','vector database'),'github',Q,'vector database')
        except ToolError: baseline=[]
        agent=run(Q,fault=fault)
        rows.append({'fault':fault,'single_tool_usable_records':len(baseline),'agent_used_records':len(agent.sources_used),'single_tool_attempts':1,'agent_attempts':agent.metrics['tool_attempts'],'agent_status':agent.status})
    print(json.dumps(rows,indent=2))
if __name__=='__main__': main()
