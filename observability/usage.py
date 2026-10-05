"""Per-node token / cost / latency accounting for every OpenAI call.

Instead of editing each node, we wrap the three OpenAI SDK entry points the
project uses (beta parse, chat create, embeddings create). A ContextVar names
the node that is currently running so calls inside it are attributed to it.
"""
import time
from contextvars import ContextVar
from dataclasses import dataclass, field

# USD per 1M tokens (input, output). Update when OpenAI pricing changes.
PRICING = {
    "gpt-4o":                 (2.50, 10.00),
    "gpt-4o-mini":            (0.15, 0.60),
    "text-embedding-3-small": (0.02, 0.0),
    "text-embedding-3-large": (0.13, 0.0),
    "claude-sonnet-5-5":      (2.00, 10.00),
    "claude-haiku-4-5":       (1.00, 5.00),
}


def price_for(model: str) -> tuple[float, float]:
    for name in sorted(PRICING, key=len, reverse=True):  # longest prefix wins
        if model and model.startswith(name):
            return PRICING[name]
    return (0.0, 0.0)


def cost_usd(model: str, prompt_tokens: int, completion_tokens: int) -> float:
    pin, pout = price_for(model)
    return (prompt_tokens * pin + completion_tokens * pout) / 1_000_000


@dataclass
class Usage:
    calls: int = 0
    prompt_tokens: int = 0
    completion_tokens: int = 0
    cost_usd: float = 0.0
    by_model: dict = field(default_factory=dict)

    def add(self, model, pt, ct):
        self.calls += 1
        self.prompt_tokens += pt
        self.completion_tokens += ct
        c = cost_usd(model, pt, ct)
        self.cost_usd += c
        self.by_model[model] = self.by_model.get(model, 0) + c

    def as_dict(self):
        return {
            "llm_calls": self.calls,
            "prompt_tokens": self.prompt_tokens,
            "completion_tokens": self.completion_tokens,
            "cost_usd": round(self.cost_usd, 6),
        }


_current: ContextVar = ContextVar("atlas_usage", default=None)
_in_call: ContextVar = ContextVar("atlas_in_call", default=False)


def start_collecting() -> tuple[Usage, object]:
    u = Usage()
    return u, _current.set(u)


def stop_collecting(token):
    _current.reset(token)


def _record(model, usage_obj):
    u = _current.get()
    if u is None or usage_obj is None:
        return
    pt = getattr(usage_obj, "prompt_tokens", 0) or 0
    ct = getattr(usage_obj, "completion_tokens", 0) or 0
    u.add(model, pt, ct)


def _wrap(fn):
    def inner(self, *args, **kwargs):
        if _in_call.get():  # avoid double counting nested SDK calls
            return fn(self, *args, **kwargs)
        tok = _in_call.set(True)
        try:
            resp = fn(self, *args, **kwargs)
        finally:
            _in_call.reset(tok)
        try:
            _record(kwargs.get("model", ""), getattr(resp, "usage", None))
        except Exception:
            pass  # accounting must never break the pipeline
        return resp
    inner._atlas_wrapped = True
    return inner


_installed = False


def _targets():
    """(class, method) pairs to wrap, discovered from a live client so it works across SDK versions
    (module paths differ between openai 1.x and 2.x)."""
    from openai import OpenAI
    c = OpenAI(api_key="sk-unused")
    pairs = [(type(c.chat.completions), "create"), (type(c.chat.completions), "parse"),
             (type(c.embeddings), "create")]
    beta = getattr(getattr(c, "beta", None), "chat", None)
    if beta is not None:
        pairs += [(type(beta.completions), "create"), (type(beta.completions), "parse")]
    return pairs


def install():
    """Idempotently patch the OpenAI SDK. Safe to call many times."""
    global _installed
    if _installed:
        return
    try:
        pairs = _targets()
    except Exception:
        return
    for cls, name in pairs:
        fn = getattr(cls, name, None)
        if fn is not None and not getattr(fn, "_atlas_wrapped", False):
            setattr(cls, name, _wrap(fn))
    _installed = True
