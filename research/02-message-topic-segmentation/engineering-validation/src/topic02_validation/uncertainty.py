"""Assignment-specific uncertainty/abstention diagnostic for EV6."""
from __future__ import annotations
from dataclasses import dataclass
import random
import re
from .models import TopicDefinition
from .assignment import topic_score


@dataclass(frozen=True)
class UncertaintyExample:
    example_id: str
    family: str
    template_family: str
    text: str
    topics: tuple[TopicDefinition, ...]
    required_topics: tuple[str, ...] = ()
    ambiguous: bool = False
    irrelevant: bool = False

    @property
    def content_key(self) -> tuple:
        return (
            self.text,
            tuple((t.topic_id,t.description,t.signature_terms) for t in self.topics),
            self.required_topics,self.ambiguous,self.irrelevant,
        )


@dataclass(frozen=True)
class EvalRow:
    example: UncertaintyExample
    predicted_topics: tuple[str, ...]
    abstained: bool
    confidence: float

    @property
    def correct(self) -> bool:
        if self.example.ambiguous or self.example.irrelevant:
            return self.abstained
        return (not self.abstained) and set(self.predicted_topics)==set(self.example.required_topics)


def _topic_defs(a: str, b: str) -> tuple[TopicDefinition,...]:
    return (
        TopicDefinition("A", f"{a} work matter", tuple(a.lower().split()) + ("approval",)),
        TopicDefinition("B", f"{b} work matter", tuple(b.lower().split()) + ("approval",)),
    )


def generate_examples(*, seed: int, count_per_family: int = 30, variant: str = "calibration") -> tuple[UncertaintyExample,...]:
    rng=random.Random(seed);rows=[]
    if variant=="calibration":
        names=("Atlas budget","Beta release")
        templates={
            "unique":"Approve {a} item {n}.",
            "multi":"Security review covers {a} and {b} item {n}.",
            "amb":"Approval change {n} needs review.",
            "irrelevant":"Thanks for update {n}.",
            "near":"{a} review {n} is pending; {b} is mentioned only in background.",
        }
        prefix="cal"
    elif variant=="holdout":
        names=("North contract","South rollout")
        templates={
            "unique":"Decision for {a} case {n} is due.",
            "multi":"Shared audit affects {a} plus {b} case {n}.",
            "amb":"The approval revision {n} is pending.",
            "irrelevant":"Have a good evening {n}.",
            "near":"{a} action {n} is required; context also names {b} incidentally.",
        }
        prefix="holdout"
    else: raise KeyError(variant)
    topics=_topic_defs(*names);a=names[0];b=names[1]
    for i in range(count_per_family):
        n=rng.randint(10000,99999)
        rows.append(UncertaintyExample(f"{prefix}-unique-{i}","unique",f"{prefix}-unique-template",templates['unique'].format(a=a,b=b,n=n),topics,("A",)))
        rows.append(UncertaintyExample(f"{prefix}-multi-{i}","multi_label",f"{prefix}-multi-template",templates['multi'].format(a=a,b=b,n=n),topics,("A","B")))
        rows.append(UncertaintyExample(f"{prefix}-amb-{i}","ambiguous",f"{prefix}-amb-template",templates['amb'].format(a=a,b=b,n=n),topics,(),True,False))
        rows.append(UncertaintyExample(f"{prefix}-irrelevant-{i}","irrelevant",f"{prefix}-irrelevant-template",templates['irrelevant'].format(a=a,b=b,n=n),topics,(),False,True))
        rows.append(UncertaintyExample(f"{prefix}-near-{i}","near_collision",f"{prefix}-near-template",templates['near'].format(a=a,b=b,n=n),topics,("A",)))
    return tuple(rows)


def evaluate(example: UncertaintyExample, *, threshold: float) -> EvalRow:
    scores=sorted(((t.topic_id,topic_score(example.text,t)) for t in example.topics),key=lambda x:(-x[1],x[0]))
    eligible=[tid for tid,s in scores if s>=threshold]
    # Same ambiguity guard concept as assignment.py: multiple matters require an
    # exclusive cue for each. No eligible matter => abstain.
    if len(eligible)>1:
        words=set(re.findall(r"[A-Za-z0-9]+",example.text.lower()))
        term_sets={t.topic_id:set(t.signature_terms) for t in example.topics}
        hits=[]
        for tid in eligible:
            others=set().union(*(v for k,v in term_sets.items() if k!=tid))
            if words & (term_sets[tid]-others):hits.append(tid)
        if len(hits)==1:eligible=hits
        elif len(hits)!=len(eligible):eligible=[]
    abstain=not eligible
    confidence=max((s for _,s in scores),default=0.0)
    return EvalRow(example,tuple(sorted(eligible)),abstain,confidence)


def choose_threshold(
    calibration: tuple[UncertaintyExample,...],
    *,
    max_error: float = 0.05,
    min_coverage: float = 0.40,
) -> dict:
    candidates=(0.15,0.2,0.25,0.3,0.34,0.4,0.5,0.6,0.7,0.8)
    rows=[]
    for th in candidates:
        ev=[evaluate(x,threshold=th) for x in calibration]
        accepted=[x for x in ev if not x.abstained]
        wrong=[x for x in accepted if not x.correct]
        error=len(wrong)/len(accepted) if accepted else 0.0
        coverage=len(accepted)/len(ev) if ev else 0.0
        rows.append({'threshold':th,'accepted':len(accepted),'wrong':len(wrong),'accepted_error':error,'coverage':coverage})
    feasible=[r for r in rows if r['accepted_error']<=max_error and r['coverage']>=min_coverage]
    selected=max(feasible,key=lambda r:(r['coverage'],-r['accepted_error'],r['threshold'])) if feasible else None
    useful=[r for r in rows if r['coverage']>=min_coverage]
    fallback=min(useful,key=lambda r:(r['accepted_error'],-r['coverage'],-r['threshold'])) if useful else None
    return {
        'target_max_accepted_error':max_error,
        'target_min_coverage':min_coverage,
        'target_met':selected is not None,
        'selected_threshold':selected['threshold'] if selected else None,
        'fallback_threshold':fallback['threshold'] if fallback else None,
        'sweep':rows,
    }

