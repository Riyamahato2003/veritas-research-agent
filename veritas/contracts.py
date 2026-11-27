from dataclasses import dataclass, field, asdict
from typing import Literal
import re

STOP = set('a an the and or of to in for is are how what which with using use on at from by find compare top best different approaches pros cons their about can should i me please research summarize explain between startup building'.split())

def terms(s: str) -> set[str]:
    return {w for w in re.findall(r'[a-z0-9]+', s.lower()) if len(w)>1 and w not in STOP and not w.isdigit()}

@dataclass(frozen=True)
class Step:
    tool: str
    query: str
    reason: str

@dataclass(frozen=True)
class Evidence:
    title: str
    url: str
    text: str
    tool: str
    score: float = 0.0
    id: str = ''

@dataclass(frozen=True)
class Finding:
    statement: str
    source_ids: list[str]

@dataclass
class Report:
    question: str
    short_answer: str
    key_findings: list[Finding]
    sources_used: list[Evidence]
    confidence: Literal['low','medium','high']
    limitations: list[str]
    assumptions: list[str]
    suggested_next_steps: list[str]
    status: Literal['complete','partial','insufficient']
    mode: str
    plan: list[Step]
    trace: list[dict]
    metrics: dict = field(default_factory=dict)
    analysis: list[Finding] = field(default_factory=list)
    comparison: list[dict] = field(default_factory=list)
    sections: list[dict] = field(default_factory=list)
    research_intent: dict = field(default_factory=dict)
    coverage_details: dict = field(default_factory=dict)
    def to_dict(self):
        return asdict(self)
