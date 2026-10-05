"""LLM-as-judge primitives (OpenAI structured outputs + on-disk cache).

The judge model should differ from the generator to limit self-preference bias:
set EVAL_JUDGE_MODEL (default gpt-4o) independently of the generator models.

A model name with the prefix "anthropic:" (e.g. EVAL_JUDGE_MODEL=anthropic:claude-sonnet-5-5) is routed to the
Anthropic API (needs `pip install anthropic` and ANTHROPIC_API_KEY); structured output is forced via tool use.
"""
import hashlib
import json
import os
import threading

from dotenv import load_dotenv
from pydantic import BaseModel

load_dotenv()  # the Anthropic path never imports config.py, so load .env here

JUDGE_MODEL = os.getenv("EVAL_JUDGE_MODEL", "gpt-4o")
CACHE_PATH = os.path.join(os.path.dirname(__file__), ".judge_cache.jsonl")
_cache: dict | None = None
_cost_lock = threading.Lock()
JUDGE_COST = {"usd": 0.0, "calls": 0, "cached": 0, "input_tokens": 0, "output_tokens": 0}  # this process only


def _bill(model: str, in_tok: int, out_tok: int):
    from observability.usage import cost_usd
    with _cost_lock:
        JUDGE_COST["usd"] += cost_usd(model.split(":", 1)[-1], in_tok, out_tok)
        JUDGE_COST["calls"] += 1
        JUDGE_COST["input_tokens"] += in_tok
        JUDGE_COST["output_tokens"] += out_tok
_client = None


def _get_client():
    global _client
    if _client is None:
        from openai import OpenAI
        from config import OPENAI_API_KEY
        _client = OpenAI(api_key=OPENAI_API_KEY)
    return _client


def _load_cache() -> dict:
    global _cache
    if _cache is None:
        _cache = {}
        if os.path.exists(CACHE_PATH):
            with open(CACHE_PATH, encoding="utf-8") as f:
                for line in f:
                    try:
                        r = json.loads(line)
                        _cache[r["k"]] = r["v"]
                    except Exception:
                        pass
    return _cache


def _anthropic_parse(model: str, schema: type[BaseModel], system: str, user: str):
    """Structured output via a tool call. Some models reject a forced tool_choice, so we ask for the tool in the
    prompt (auto choice) and fall back to parsing a JSON object from the text reply."""
    import anthropic
    client = anthropic.Anthropic()  # reads ANTHROPIC_API_KEY
    sys_prompt = (system + "\n\nYou MUST respond by calling the `record` tool exactly once with your judgement. "
                  "Do not answer in prose.")
    resp = client.messages.create(
        model=model, max_tokens=4096, system=sys_prompt,
        messages=[{"role": "user", "content": user}],
        tools=[{"name": "record", "description": "Record the structured judgement.",
                "input_schema": schema.model_json_schema()}],
    )
    _bill("anthropic:" + model, resp.usage.input_tokens, resp.usage.output_tokens)
    block = next((b for b in resp.content if b.type == "tool_use"), None)
    if block is not None:
        return schema.model_validate(block.input)
    text = "".join(b.text for b in resp.content if b.type == "text")
    start, end = text.find("{"), text.rfind("}")
    if start < 0 or end <= start:
        raise ValueError(f"Anthropic judge returned no structured output: {text[:200]!r}")
    return schema.model_validate_json(text[start:end + 1])


def judge(schema: type[BaseModel], system: str, user: str, model: str | None = None, use_cache=True):
    """Run one structured judge call; deterministic (temperature 0) and cached."""
    model = model or JUDGE_MODEL
    key = hashlib.sha256(json.dumps([model, schema.__name__, system, user]).encode()).hexdigest()
    cache = _load_cache()
    if use_cache and key in cache:
        with _cost_lock:
            JUDGE_COST["cached"] += 1
        return schema.model_validate(cache[key])
    if model.startswith("anthropic:"):
        parsed = _anthropic_parse(model.split(":", 1)[1], schema, system, user)
    else:
        resp = _get_client().beta.chat.completions.parse(
            model=model,
            messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
            response_format=schema,
            temperature=0,
        )
        parsed = resp.choices[0].message.parsed
        if getattr(resp, "usage", None):
            _bill(model, resp.usage.prompt_tokens, resp.usage.completion_tokens)
    if use_cache:
        cache[key] = parsed.model_dump()
        with open(CACHE_PATH, "a", encoding="utf-8") as f:
            f.write(json.dumps({"k": key, "v": cache[key]}) + "\n")
    return parsed


def format_chunks(chunks: list[dict], max_chars: int = 3000) -> str:
    return "\n\n".join(
        f"<chunk id=\"{c['id']}\" doc=\"{c.get('doc')}\" section=\"{c.get('section')}\" page=\"{c.get('page')}\">\n"
        f"{(c.get('text') or '')[:max_chars]}\n</chunk>" for c in chunks)
