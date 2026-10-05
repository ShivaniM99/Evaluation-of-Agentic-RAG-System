"""Build the static evaluation report from saved eval runs (no API calls).

    python docs/build_report.py        # writes docs/index.html (+ docs/report_fragment.html for artifact hosts)

Needs the run files in evals/results/*.json and the trace database (observability/atlas.db), which are
git-ignored, so rebuild on the machine that ran the evals. docs/index.html is committed.
"""
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)
sys.path.insert(0, ROOT)
from observability import store
L=lambda n: json.load(open(f'evals/results/{n}.json'))
runs={'base':L('baseline-v1'),'v2':L('fix-v2-abstain-analyzer'),'v3':L('fix-v3-offsubject-abstain-4o-analyzer')}
M=['generation.groundedness','generation.citation_precision','generation.citation_recall','generation.citation_validity','correctness.correctness','retrieval.recall@5','retrieval.mrr','abstention.abstention_correct','abstention.false_abstain','abstention.hallucinated_answer','trajectory.iterations','trajectory.cost_usd']
out={'runs':{}}
for k,r in runs.items():
    a=r['aggregate']
    out['runs'][k]={'metrics':{m:{'mean':a['metrics'][m]['mean'],'lo':a['metrics'][m]['ci95'][0],'hi':a['metrics'][m]['ci95'][1],'n':a['metrics'][m]['n']} for m in M if m in a['metrics']},
      'n_items':a['n_items'],'pipeline_cost':a['total_cost_usd'],'judge_cost':a.get('judge_cost_usd'),'latency':a['latency_s'],'stability':a.get('stability'),'meta':r['meta'].get('generator_model')}
def trace_view(rid, item=None, full=True):
    t=store.load_trace(rid)
    d={'question':t['question'],'answer':t['answer'],'draft':t['draft_answer'],'iterations':t['iterations'],'abstained':bool(t['abstained']),
       'latency':round(t['latency_s'],1),'cost':round(t['cost_usd'],4),
       'spans':[{'node':s['node'],'latency':round(s['latency_s'],2),'cost':round(s['cost_usd'],5),'it':s['iteration']} for s in t['spans']],
       'chunks':[{'id':c['id'],'doc':c['doc'],'section':c['section'],'score':c.get('rerank_score')} for c in t['chunks']],
       'citations':[{'doc':c['doc'],'section':c['section'],'ok':c['resolved_chunk_id'] is not None} for c in t['citations']]}
    if item:
        g=item.get('generation') or {}
        d['scores']={k:g.get(k) for k in ('groundedness','citation_precision','citation_recall','citation_validity')}
        d['scores']['correctness']=(item.get('correctness') or {}).get('correctness')
        d['claims']=[{'claim':c['claim'],'supported':bool(c['supporting_chunk_ids'])} for c in (g.get('claims') or []) if c['needs_citation']][:9]
    return d
def item(run,i): return next(x for x in runs[run]['items'] if x['id']==i)
def pick(run,i,rep=0):
    it=item(run,i); rid=(it.get('request_ids') or [it['request_id']])[rep]; return trace_view(rid,it)
cases=[]
# 1 citation stripping (smoke-1): draft vs final
s1=L('smoke-1'); it=next(x for x in s1['items'] if x['id']=='seed-01'); t=store.load_trace(it['request_id'])
cases.append({'id':'cite','kind':'bug','title':'The Verifier removed every citation','question':t['question'],'before':{'label':'Draft from the synthesizer','text':t['draft_answer']},'after':{'label':'Final answer after the Verifier','text':t['answer']}})
# hallucination cases: baseline vs v3
for i,title in [('gen-078','Invented licensing answer from zero evidence'),('gen-080','Confident answer from off-subject evidence'),('gen-084','Network answer built from loosely related chunks')]:
    b=pick('base',i); v=pick('v3',i)
    cases.append({'id':i,'kind':'halluc','title':title,'question':b['question'],'before':{'label':'Baseline','trace':b},'after':{'label':'After fixes','trace':v}})
# healthy examples (v3)
for i in ['seed-01','seed-04','gen-071']:
    cases.append({'id':i,'kind':'ok','title':{'seed-01':'Single-fact lookup','seed-04':'Step-by-step procedure','gen-071':'Release-notes lookup'}[i],'question':item('v3',i)['question'],'after':{'label':'Current pipeline','trace':pick('v3',i)}})
# regression
cases.append({'id':'gen-073','kind':'miss','title':'A retrieval miss no fix touched','question':item('v3','gen-073')['question'],'before':{'label':'Baseline','trace':pick('base','gen-073')},'after':{'label':'After fixes','trace':pick('v3','gen-073')}})
out['cases']=cases


import re as _re
_docs = sorted({c["doc"] for case in cases for k in ("before", "after")
                for c in ((case.get(k) or {}).get("trace") or {}).get("chunks", [])})
_doc_alias = {d: f"doc-{i + 1:02d}" for i, d in enumerate(_docs)}


def _anon(s):
    # product-specific filenames (e.g. aiw00a12.pdf) would let a reader identify the source: relabel them
    for d in sorted(_doc_alias, key=len, reverse=True):
        stem = d[:-4] if d.endswith(".pdf") else d
        s = s.replace(stem + ".pdf", _doc_alias[d] + ".pdf").replace(stem, _doc_alias[d])
    s = _re.sub(r"(?i)ricoh", "ABC Technology", s)
    s = _re.sub(r"ABC Technology ProcessDirector", "ABC Platform", s)
    s = _re.sub(r"ProcessDirector", "Platform", s)
    return _re.sub(r"\bRPD\b", "ABC Platform", s)


data = _anon(json.dumps(out, ensure_ascii=False)).replace("</", "<\\/")
tpl = open("docs/report_template.html", encoding="utf-8").read()
fragment = tpl.replace("/*DATA*/", data)
open("docs/report_fragment.html", "w", encoding="utf-8").write(fragment)
head = ('<!doctype html><html lang="en"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width,initial-scale=1"></head><body>')
# the template starts with <title>/<link>/<style>; browsers accept them inside body, but hoist them for validity
title_end = fragment.index("</title>") + len("</title>")
open("docs/index.html", "w", encoding="utf-8").write(head + fragment + "</body></html>")
print("wrote docs/index.html", len(fragment) // 1024, "KB;", len(cases), "cases")
