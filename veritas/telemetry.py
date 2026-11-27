"""Per-run trace and privacy-minimized server log."""
import json, time, uuid
from collections import Counter
from .tools import ToolError
ENGINE='cp30-prototype'
def error_code(exc):
    return exc.kind if isinstance(exc,ToolError) else 'internal_'+type(exc).__name__
class Trace:
    def __init__(self,diagnostics=False):
        self.start=time.monotonic(); self.run_id=uuid.uuid4().hex; self.events=[]; self.diagnostics=diagnostics
        self.errors=Counter(); self.usage=Counter(); self.attempts=Counter(); self.stage_ms=Counter(); self.model_usage={}; self.rate_limits={}
    def elapsed(self): return round((time.monotonic()-self.start)*1000)
    def left(self): return max(0,48-(time.monotonic()-self.start))
    def emit(self,stage,status='ok',**data):
        e={'seq':len(self.events)+1,'offset_ms':self.elapsed(),'stage':stage,'status':status,**data}
        self.events.append(e)
        if 'error' in data: self.errors[str(data['error'])]+=1
        if isinstance(data.get('ms'),int): self.stage_ms[stage]+=data['ms']
        if stage in ('retrieve','extract','model') and status!='skipped': self.attempts[data.get('provider',stage)]+=1
        mid=data.get('model_id')
        if mid and isinstance(data.get('rate_limit'),dict) and data['rate_limit']: self.rate_limits[mid]=data['rate_limit']
        for k,v in data.get('usage',{}).items():
            if k in ('prompt_tokens','completion_tokens','total_tokens') and isinstance(v,int) and v>=0:
                self.usage[k]+=v
                if mid: self.model_usage.setdefault(mid,Counter())[k]+=v
    def summary(self):
        return {'engine_version':ENGINE,'run_id':self.run_id,'elapsed_ms':self.elapsed(),'provider_attempts':dict(self.attempts),'error_counts':dict(self.errors),'stage_ms':dict(self.stage_ms),'token_usage':dict(self.usage),'model_usage':{k:dict(v) for k,v in self.model_usage.items()},'rate_limits':self.rate_limits}
def log_report(report):
    """No question, query, evidence text, URLs, model prompts, or provider response bodies."""
    m=report.metrics
    if m.get('engine_version')!=ENGINE: return
    fields=('engine_version','run_id','elapsed_ms','provider_attempts','error_counts','stage_ms','token_usage','model_usage','rate_limits','coverage','coverage_target','claims_proposed','claims_accepted','claims_rejected','search_credits_upper_estimate','passages_indexed','recovery_triggered','failure_stage','quality')
    print('VERITAS_RUN '+json.dumps({'status':report.status,'confidence':report.confidence,**{k:m.get(k) for k in fields}},separators=(',',':')),flush=True)
